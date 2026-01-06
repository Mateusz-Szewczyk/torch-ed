# routers/files.py

from fastapi import APIRouter, HTTPException, Depends, Form, File, UploadFile, Request, Query
from fastapi_cache.decorator import cache
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from ..models import ORMFile, User, WorkspaceDocument, FileCategory, DocumentSection, DocumentImage
from ..schemas import (
    UploadResponse,
    UploadedFileRead,
    DeleteKnowledgeRequest,
    DeleteKnowledgeResponse,
)
from ..dependencies import get_db
from ..auth import get_current_user, get_current_user_optional, verify_jwt_token
from ..vector_store import delete_file_from_vector_store, create_vector_store
from ..file_processor.pdf_processor import PDFProcessor
from ..file_processor.documents_processor import DocumentProcessor
from ..file_processor.math_extractor import MathExtractor, extract_math_from_text, check_math_content
from ..chunking import create_chunks
from ..services.subscription import SubscriptionService
from ..services.storage_service import get_storage_service

import os
from pathlib import Path
import aiofiles
import asyncio
import logging
import re
import uuid as uuid_lib
from difflib import SequenceMatcher

router = APIRouter()
logger = logging.getLogger(__name__)

# Inicjalizacja procesorów plików
pdf_processor = PDFProcessor()
document_processor = DocumentProcessor()

# Inicjalizacja modelu embedującego
from langchain_openai import OpenAIEmbeddings

try:
    embedding_model = OpenAIEmbeddings(model="text-embedding-3-large")
except Exception as e:
    raise


# --- FUNKCJE POMOCNICZE DO USUWANIA NAGŁÓWKÓW/STOPEK ---

def _is_similar(s1: str, s2: str, threshold: float = 0.85) -> bool:
    """Check if two strings are similar (useful for detecting headers/footers with page numbers)."""
    if not s1 or not s2:
        return False
    # Normalize strings for comparison (remove numbers that might be page numbers)
    s1_normalized = re.sub(r'\d+', '#', s1.strip().lower())
    s2_normalized = re.sub(r'\d+', '#', s2.strip().lower())
    return SequenceMatcher(None, s1_normalized, s2_normalized).ratio() >= threshold


def _extract_lines_from_page(page_text: str, num_lines: int = 3, from_start: bool = True) -> list:
    """Extract first or last N lines from a page."""
    lines = [l.strip() for l in page_text.split('\n') if l.strip()]
    if from_start:
        return lines[:num_lines]
    else:
        return lines[-num_lines:]


def _find_recurring_patterns(pages_text: list, threshold_ratio: float = 0.5) -> tuple:
    """
    Analyze pages to find recurring header/footer patterns.

    Args:
        pages_text: List of tuples (page_num, text)
        threshold_ratio: Minimum ratio of pages where pattern must appear (0.5 = 50%)

    Returns:
        Tuple of (header_patterns, footer_patterns) - lists of strings to remove
    """
    if len(pages_text) < 3:
        # Need at least 3 pages to detect patterns
        return [], []

    min_occurrences = max(2, int(len(pages_text) * threshold_ratio))

    # Extract first/last lines from each page
    headers = []  # List of lists (first 3 lines per page)
    footers = []  # List of lists (last 3 lines per page)

    for _, page_text in pages_text:
        headers.append(_extract_lines_from_page(page_text, num_lines=3, from_start=True))
        footers.append(_extract_lines_from_page(page_text, num_lines=3, from_start=False))

    # Find recurring header patterns
    header_patterns = []
    for line_idx in range(3):  # Check first 3 lines
        line_candidates = [h[line_idx] if len(h) > line_idx else None for h in headers]
        line_candidates = [l for l in line_candidates if l and len(l) < 150]  # Skip long lines

        if not line_candidates:
            continue

        # Group similar lines
        groups = []
        for candidate in line_candidates:
            found_group = False
            for group in groups:
                if _is_similar(candidate, group[0]):
                    group.append(candidate)
                    found_group = True
                    break
            if not found_group:
                groups.append([candidate])

        # Find groups that appear frequently enough
        for group in groups:
            if len(group) >= min_occurrences:
                # Use the most common normalized form
                normalized = re.sub(r'\d+', '#', group[0].strip())
                if len(normalized) > 3:  # Ignore very short patterns
                    header_patterns.append(normalized)

    # Find recurring footer patterns
    footer_patterns = []
    for line_idx in range(3):  # Check last 3 lines
        line_candidates = [f[-(line_idx + 1)] if len(f) > line_idx else None for f in footers]
        line_candidates = [l for l in line_candidates if l and len(l) < 150]

        if not line_candidates:
            continue

        groups = []
        for candidate in line_candidates:
            found_group = False
            for group in groups:
                if _is_similar(candidate, group[0]):
                    group.append(candidate)
                    found_group = True
                    break
            if not found_group:
                groups.append([candidate])

        for group in groups:
            if len(group) >= min_occurrences:
                normalized = re.sub(r'\d+', '#', group[0].strip())
                if len(normalized) > 3:
                    footer_patterns.append(normalized)

    logger.info(f"Detected {len(header_patterns)} header patterns and {len(footer_patterns)} footer patterns")
    return header_patterns, footer_patterns


def _is_page_number_line(line: str) -> bool:
    """
    Check if a line is just a page number.

    Detects patterns like:
    - "1", "12", "123"
    - "- 1 -", "- 12 -"
    - "Page 1", "page 12"
    - "1 of 10", "12/100"
    """
    line = line.strip()
    if not line:
        return False

    # Pure number
    if re.fullmatch(r'\d{1,4}', line):
        return True

    # "- N -" or "— N —" pattern
    if re.fullmatch(r'[-–—]\s*\d{1,4}\s*[-–—]', line):
        return True

    # "Page N" or "Strona N" patterns
    if re.fullmatch(r'(?:page|strona|str\.?|p\.?)\s*\d{1,4}', line, re.IGNORECASE):
        return True

    # "N of M" or "N / M" patterns
    if re.fullmatch(r'\d{1,4}\s*(?:of|/|z)\s*\d{1,4}', line, re.IGNORECASE):
        return True

    # Roman numerals (i, ii, iii, iv, v, vi, vii, viii, ix, x, etc.)
    if re.fullmatch(r'[ivxlcdm]+', line, re.IGNORECASE) and len(line) <= 10:
        return True

    return False


def _remove_standalone_page_numbers(lines: list) -> list:
    """
    Remove standalone page numbers from the beginning or end of a page.

    Checks first 3 and last 3 lines for page number patterns.
    """
    if not lines:
        return lines

    result = lines.copy()

    # Check and remove from the end (last 3 lines, reversed)
    lines_to_check_end = min(3, len(result))
    while lines_to_check_end > 0 and result:
        last_line = result[-1].strip()
        if not last_line:
            result.pop()
            continue
        if _is_page_number_line(last_line):
            logger.debug(f"Removing page number from end: '{last_line}'")
            result.pop()
            lines_to_check_end -= 1
        else:
            break

    # Check and remove from the start (first 3 lines)
    lines_removed = 0
    while lines_removed < 3 and result:
        first_line = result[0].strip()
        if not first_line:
            result.pop(0)
            continue
        if _is_page_number_line(first_line):
            logger.debug(f"Removing page number from start: '{first_line}'")
            result.pop(0)
            lines_removed += 1
        else:
            break

    return result


def remove_headers_footers(pages_text: list) -> list:
    """
    Remove detected headers, footers, and standalone page numbers from page texts.

    Args:
        pages_text: List of tuples (page_num, text)

    Returns:
        List of tuples (page_num, cleaned_text) with headers/footers/page numbers removed
    """
    if not pages_text:
        return pages_text

    header_patterns, footer_patterns = _find_recurring_patterns(pages_text)

    cleaned_pages = []
    for page_num, page_text in pages_text:
        lines = page_text.split('\n')

        # Remove header lines
        if header_patterns:
            new_lines = []
            for i, line in enumerate(lines):
                line_stripped = line.strip()
                if not line_stripped:
                    new_lines.append(line)
                    continue

                # Only check first 5 lines for headers
                if i < 5:
                    line_normalized = re.sub(r'\d+', '#', line_stripped.lower())
                    is_header = any(
                        SequenceMatcher(None, line_normalized, pattern.lower()).ratio() >= 0.85
                        for pattern in header_patterns
                    )
                    if is_header:
                        logger.debug(f"Removing header from page {page_num}: '{line_stripped[:50]}...'")
                        continue

                new_lines.append(line)
            lines = new_lines

        # Remove footer lines
        if footer_patterns:
            new_lines = []
            total_lines = len(lines)
            for i, line in enumerate(lines):
                line_stripped = line.strip()
                if not line_stripped:
                    new_lines.append(line)
                    continue

                # Only check last 5 lines for footers
                if i >= total_lines - 5:
                    line_normalized = re.sub(r'\d+', '#', line_stripped.lower())
                    is_footer = any(
                        SequenceMatcher(None, line_normalized, pattern.lower()).ratio() >= 0.85
                        for pattern in footer_patterns
                    )
                    if is_footer:
                        logger.debug(f"Removing footer from page {page_num}: '{line_stripped[:50]}...'")
                        continue

                new_lines.append(line)
            lines = new_lines

        # Also remove standalone page numbers (even if no patterns detected)
        lines = _remove_standalone_page_numbers(lines)

        cleaned_text = '\n'.join(lines)
        cleaned_pages.append((page_num, cleaned_text))

    return cleaned_pages


# --- FUNKCJA POMOCNICZA DO CZYSZCZENIA TEKSTU ---
def clean_text(text: str) -> str:
    """
    Czyści tekst z niepożądanych znaków i normalizuje formatowanie.
    - Usuwa znaki NUL (0x00), których PostgreSQL nie akceptuje
    - Usuwa markery stron (Page X:)
    - Normalizuje znaki nowej linii - usuwa pojedyncze łamanie linii w środku zdań
    - Zachowuje podział akapitów (podwójne nowe linie)
    - PRESERVES markdown tables (pipe-separated format)
    """
    if not text:
        return ""

    # 1. Usuń znaki NUL
    text = text.replace("\x00", "")

    # 2. Normalizuj różne typy końca linii do \n
    text = text.replace('\r\n', '\n')
    text = text.replace('\r', '\n')

    # 3. Usuń markery stron (np. "Page 1:", "Page 12:\n")
    text = re.sub(r'Page\s+\d+:\s*\n?', '', text, flags=re.IGNORECASE)

    # 3.5 DETECT AND PRESERVE MARKDOWN TABLES
    # Find markdown tables and temporarily replace with placeholders
    table_pattern = re.compile(
        r'(\|[^\n]+\|\n\|[-:| ]+\|\n(?:\|[^\n]+\|\n?)+)',
        re.MULTILINE
    )
    tables_found = table_pattern.findall(text)
    table_placeholders = {}

    for i, table in enumerate(tables_found):
        placeholder = f'<TABLE_PLACEHOLDER_{i}>'
        table_placeholders[placeholder] = table
        text = text.replace(table, placeholder, 1)

    if tables_found:
        logger.debug(f"[clean_text] Preserved {len(tables_found)} markdown table(s)")

    # 4. Zachowaj podział akapitów - zamień 2+ nowych linii na specjalny marker
    text = re.sub(r'\n{2,}', '\n\n<PARAGRAPH_BREAK>\n\n', text)

    # 5. Zamień pojedyncze nowe linie na spację (to łamanie tekstu w środku zdania)
    # ALE zachowaj nowe linie po znakach kończących zdanie lub przed nagłówkami
    lines = text.split('\n')
    processed_lines = []

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        # Sprawdź czy to jest marker akapitu
        if '<PARAGRAPH_BREAK>' in line:
            processed_lines.append('\n\n')
            continue

        # Sprawdź czy to placeholder tabeli - nie modyfikuj
        if '<TABLE_PLACEHOLDER_' in line:
            processed_lines.append(line)
            continue

        # Sprawdź czy poprzednia linia kończy się na znak kończący zdanie
        # lub czy bieżąca linia zaczyna się od wielkiej litery/cyfry (potencjalny nagłówek)
        if processed_lines:
            last = processed_lines[-1].strip()

            # Skip processing if last was a table placeholder
            if last and '<TABLE_PLACEHOLDER_' in last:
                processed_lines.append('\n\n')
                processed_lines.append(line)
                continue

            # Jeśli poprzednia linia kończy się na . ! ? : - to zachowaj jako osobne
            if last and last[-1] in '.!?:':
                processed_lines.append(' ')  # Dodaj spację między zdaniami
            # Jeśli bieżąca linia wygląda na nagłówek (krótka, zaczyna się od wielkiej litery)
            elif len(line) < 80 and line[0].isupper() and (not last or last[-1] not in '.,;'):
                processed_lines.append('\n\n')  # Nowy akapit dla nagłówków
            # Jeśli bieżąca linia zaczyna się od cyfry (punkt listy)
            elif line and line[0].isdigit() and '.' in line[:5]:
                processed_lines.append('\n')  # Nowa linia dla punktów listy
            else:
                # Łączenie linii w środku zdania - dodaj spację
                if last and not last.endswith(' '):
                    processed_lines.append(' ')

        processed_lines.append(line)

    text = ''.join(processed_lines)

    # 6. Usuń wielokrotne spacje
    text = re.sub(r' {2,}', ' ', text)

    # 7. Usuń spacje przed znakami interpunkcyjnymi
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)

    # 8. Normalizuj wielokrotne nowe linie do maksymalnie 2
    text = re.sub(r'\n{3,}', '\n\n', text)

    # 9. RESTORE MARKDOWN TABLES from placeholders
    for placeholder, table in table_placeholders.items():
        # Add newlines around tables for proper formatting
        text = text.replace(placeholder, f'\n\n{table}\n\n')

    return text.strip()


# ------------------------------------------------


@router.post("/upload/", response_model=UploadResponse)
async def upload_file(
        file_description: str = Form(None, description="Description of the uploaded file."),
        category_id: str = Form(..., description="Category ID (UUID) of the document."),
        start_page: int = Form(None, description="Starting page number for PDF processing."),
        end_page: int = Form(None, description="Ending page number for PDF processing."),
        file: UploadFile = File(..., description="The file to be uploaded and processed."),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    user_id = str(current_user.id_)
    logger.info(f"Received upload request from user_id: {user_id} for file: {file.filename}")

    # Check subscription limits
    subscription_service = SubscriptionService(db, current_user)
    # Check file count first
    subscription_service.check_file_upload_limit(0)

    # Validate category exists
    try:
        category_uuid = UUID(category_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid category_id format. Must be a valid UUID.")

    category = db.query(FileCategory).filter(
        FileCategory.id == category_uuid,
        (FileCategory.user_id == current_user.id_) | (FileCategory.user_id == None)
    ).first()

    if not category:
        raise HTTPException(status_code=404, detail="Category not found or you don't have access to it.")

    if start_page is None:
        start_page = 0
    if end_page is not None and end_page < 0:
        logger.error("end_page must be a non-negative integer.")
        raise HTTPException(status_code=400, detail="end_page must be a non-negative integer.")

    upload_dir = "uploads"
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
        logger.info(f"Created upload directory at '{upload_dir}'.")

    safe_filename = Path(file.filename).name

    # Check if document already exists (by title and user_id)
    existing_doc = db.query(WorkspaceDocument).filter(
        WorkspaceDocument.user_id == current_user.id_,
        WorkspaceDocument.original_filename == safe_filename
    ).first()

    if existing_doc:
        # Sprawdzamy, czy dokument jest poprawny (czy ma sekcje)
        count_sections = db.query(DocumentSection).filter(DocumentSection.document_id == existing_doc.id).count()

        if count_sections == 0:
            logger.warning(
                f"Found orphaned document {existing_doc.id} (filename: {safe_filename}) with 0 sections. Deleting it to allow re-upload.")
            try:
                # Delete images from storage
                storage_service = get_storage_service()
                await storage_service.delete_document_images(str(existing_doc.id))

                # First delete any highlights (if any) to avoid FK errors
                from ..models import UserHighlight
                db.query(UserHighlight).filter(
                    UserHighlight.document_id == existing_doc.id
                ).delete(synchronize_session=False)

                # Then delete the document itself (sections will cascade)
                db.delete(existing_doc)
                db.commit()
                logger.info(f"Deleted orphaned document {existing_doc.id}")
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to delete orphaned document: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to clean up incomplete upload: {str(e)}")
        else:
            logger.error(f"Document with filename '{safe_filename}' already exists for user_id: {user_id}.")
            raise HTTPException(status_code=400, detail="Document with this filename already exists.")

    file_path = os.path.join(upload_dir, safe_filename)

    try:
        content = await file.read()
        subscription_service.check_file_upload_limit(len(content))

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)
        logger.info(f"Saved uploaded file: {safe_filename} to {file_path}")

        file_extension = os.path.splitext(safe_filename)[1].lower()
        logger.info(f"Determined file type: {file_extension} for file: {safe_filename}")

        # Track page information for PDFs
        page_info_list = []  # List of (page_number, text) tuples
        total_pages = 0

        if file_extension == '.txt':
            async with aiofiles.open(file_path, "r", encoding='utf-8') as f:
                text_content = await f.read()
            # For text files, treat the whole file as page 1
            page_info_list = [(1, text_content)]
            total_pages = 1
        elif file_extension == '.pdf':
            # Use new page-aware method WITH table extraction
            pages = await asyncio.to_thread(
                pdf_processor.process_pdf_with_tables,
                file_path,
                start_page=start_page,
                end_page=end_page
            )
            if pages:
                page_info_list = [(p.page_number, p.text) for p in pages]
                total_pages = await asyncio.to_thread(pdf_processor.get_total_pages, file_path)
                text_content = '\n\n'.join([p.text for p in pages])
            else:
                # Fallback to standard method if table-aware method fails
                pages = await asyncio.to_thread(
                    pdf_processor.process_pdf_with_pages,
                    file_path,
                    start_page=start_page,
                    end_page=end_page
                )
                if pages:
                    page_info_list = [(p.page_number, p.text) for p in pages]
                    total_pages = await asyncio.to_thread(pdf_processor.get_total_pages, file_path)
                    text_content = '\n\n'.join([p.text for p in pages])
                else:
                    # Last fallback to old method
                    text_content = await asyncio.to_thread(
                        pdf_processor.process_pdf, file_path, start_page=start_page, end_page=end_page
                    )
                    if text_content:
                        page_info_list = [(1, text_content)]
                        total_pages = 1
        elif file_extension in ['.docx', '.odt', '.rtf']:
            text_content = await asyncio.to_thread(document_processor.process_document, file_path)
            page_info_list = [(1, text_content)] if text_content else []
            total_pages = 1
        else:
            logger.error(f"Unsupported file type: {file_extension}")
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_extension}")

        if not text_content:
            logger.error("Failed to extract text from the document.")
            raise HTTPException(status_code=400, detail="Failed to extract text from the document.")

        # --- FIRST: Remove recurring headers, footers, and page numbers ---
        # This must happen before individual page cleaning to properly detect patterns
        if len(page_info_list) > 1:  # Only for multi-page documents
            page_info_list = remove_headers_footers(page_info_list)
            logger.info(f"Cleaned headers/footers from {len(page_info_list)} pages")

        # --- BUILD CLEANED TEXT AND PAGE MAPPING TOGETHER ---
        # IMPORTANT: We must clean each page individually AND track offsets consistently
        # This ensures page_char_mapping matches the final text_content exactly

        cleaned_pages = []
        page_char_mapping = []  # List of (start_char, end_char, page_number)
        char_offset = 0

        for page_num, page_text in page_info_list:
            cleaned_page_text = clean_text(page_text)
            if cleaned_page_text:  # Only include non-empty pages
                start_char = char_offset
                end_char = char_offset + len(cleaned_page_text)
                page_char_mapping.append((start_char, end_char, page_num))
                cleaned_pages.append(cleaned_page_text)
                char_offset = end_char + 2  # +2 for '\n\n' separator between pages

        # Rebuild text_content from cleaned pages (consistent with mapping)
        text_content = '\n\n'.join(cleaned_pages)

        # Intelligent chunking with optimized parameters:
        # - chunk_size=1200: ~300-350 tokens, good balance for context window
        # - overlap=150: preserves sentence continuity without excessive duplication
        chunks = await asyncio.to_thread(
            create_chunks,
            text_content,
            chunk_size=1200,
            overlap=150
        )
        if not chunks:
            logger.error("Failed to create text chunks from the document.")
            raise HTTPException(status_code=500, detail="Failed to create text chunks from the document.")

        await asyncio.to_thread(
            create_vector_store,
            chunks=chunks,
            user_id=user_id,
            file_name=safe_filename,
            file_description=file_description,
            category=category.name,
        )
        logger.info(f"Vector store updated for user_id: {user_id}")

        # Create WorkspaceDocument
        new_document = WorkspaceDocument(
            user_id=current_user.id_,
            category_id=category_uuid,
            title=safe_filename,
            original_filename=safe_filename,
            file_type=file_extension[1:] if file_extension else None,
            total_length=len(text_content),
            total_sections=len(chunks)
        )

        db.add(new_document)
        db.commit()
        db.refresh(new_document)

        logger.info(
            f"Created WorkspaceDocument with id={new_document.id}, category_id={new_document.category_id}, user_id={new_document.user_id}")

        # Helper function to determine page number for a chunk based on character position
        def get_page_for_chunk(chunk_start_char: int, chunk_end_char: int) -> int:
            """Find which page a chunk belongs to based on character offset.

            Uses the midpoint of the chunk to determine page, which handles
            chunks that span multiple pages better.
            """
            chunk_midpoint = (chunk_start_char + chunk_end_char) // 2

            # First try: find page by midpoint
            for start_c, end_c, page_num in page_char_mapping:
                if start_c <= chunk_midpoint < end_c:
                    return page_num

            # Fallback: find page by start position
            for start_c, end_c, page_num in page_char_mapping:
                if start_c <= chunk_start_char < end_c:
                    return page_num

            # Last fallback: return the last page if chunk is beyond all pages
            if page_char_mapping and chunk_start_char >= page_char_mapping[-1][1]:
                return page_char_mapping[-1][2]

            return 1  # Default to page 1 if no match found

        try:
            sections_to_add = []
            search_start = 0  # Track where to start searching for next chunk

            # Track which page numbers we've seen to determine is_page_start
            seen_pages = set()

            for idx, chunk in enumerate(chunks):
                # Note: chunks from create_chunks should already be from cleaned text_content
                # so we don't need to clean them again (would cause misalignment)

                # Find chunk position in text_content starting from last position
                chunk_sample = chunk[:min(100, len(chunk))]
                chunk_start = text_content.find(chunk_sample, search_start)

                if chunk_start == -1:
                    # Try from beginning as fallback
                    chunk_start = text_content.find(chunk_sample)

                if chunk_start == -1:
                    # If still not found, estimate position based on previous chunks
                    chunk_start = search_start
                    logger.warning(f"Could not find exact position for chunk {idx}, estimating at {chunk_start}")

                chunk_end = chunk_start + len(chunk)

                # Determine page number for this chunk
                page_number = get_page_for_chunk(chunk_start, chunk_end)

                # Determine if this is the first section for this page
                is_page_start = page_number not in seen_pages
                seen_pages.add(page_number)

                # Check if this chunk contains a table (pipe-separated format)
                is_table_chunk = chunk.strip().startswith('|') and '\n|' in chunk

                # Check for mathematical content
                math_result = extract_math_from_text(chunk)
                has_math = math_result.get('has_math', False)
                math_blocks = math_result.get('math_blocks', [])

                if has_math and math_blocks:
                    logger.info(f"[MATH] Chunk {idx} has {len(math_blocks)} math blocks: {[b.get('latex', '')[:30] for b in math_blocks]}")

                section = DocumentSection(
                    document_id=new_document.id,
                    section_index=idx,
                    content_text=chunk,  # Use original chunk (already cleaned via text_content)
                    base_styles=[],
                    section_metadata={
                        "page_number": page_number,
                        "total_pages": total_pages,
                        "chunk_index": idx,
                        "is_table": is_table_chunk,
                        "has_math": has_math,
                        "math_blocks": math_blocks if has_math else [],
                        "is_page_start": is_page_start  # Mark first section of each page
                    },
                    char_start=chunk_start,
                    char_end=chunk_end
                )
                sections_to_add.append(section)

                # Update search position for next chunk (account for overlap)
                search_start = max(search_start, chunk_start + 1)

            if sections_to_add:
                db.add_all(sections_to_add)
                db.commit()
                logger.info(f"Added {len(sections_to_add)} sections for document {new_document.id}")

        except Exception as inner_e:
            db.rollback()
            logger.error(f"Failed to add sections. Cleaning up document {new_document.id}. Error: {inner_e}")
            try:
                db.query(WorkspaceDocument).filter(WorkspaceDocument.id == new_document.id).delete()
                db.commit()
                logger.info(f"Cleanup successful: Deleted orphaned document {new_document.id}")
            except Exception as cleanup_error:
                db.rollback()
                logger.error(f"Failed to cleanup document {new_document.id}: {cleanup_error}")
            raise inner_e

        # --- EXTRACT AND SAVE IMAGES FROM PDF ---
        if file_extension == '.pdf':
            try:
                extracted_images = await asyncio.to_thread(
                    pdf_processor.extract_images,
                    file_path,
                    start_page=start_page,
                    end_page=end_page,
                    min_width=100,  # Filter out small icons
                    min_height=100
                )

                if extracted_images:
                    # Get storage service
                    storage_service = get_storage_service()
                    document_id_str = str(new_document.id)

                    images_to_add = []

                    for img_info in extracted_images:
                        try:
                            # Generate unique filename
                            image_filename = f"p{img_info.page_number}_i{img_info.image_index}_{uuid_lib.uuid4().hex[:8]}.{img_info.image_type}"

                            # Determine content type
                            content_type = f"image/{img_info.image_type}"
                            if img_info.image_type == 'jpg':
                                content_type = 'image/jpeg'

                            # Save image using storage service (supports both local and R2)
                            storage_path = await storage_service.save_image(
                                document_id=document_id_str,
                                image_data=img_info.image_data,
                                filename=image_filename,
                                content_type=content_type
                            )

                            # Create database record
                            doc_image = DocumentImage(
                                document_id=new_document.id,
                                page_number=img_info.page_number,
                                image_index=img_info.image_index,
                                image_path=storage_path,  # Storage path/key
                                image_type=img_info.image_type,
                                file_size=len(img_info.image_data),
                                width=img_info.width,
                                height=img_info.height,
                                x_position=img_info.x_position,
                                y_position=img_info.y_position
                            )
                            images_to_add.append(doc_image)

                        except Exception as img_save_error:
                            logger.warning(f"Failed to save image: {img_save_error}")
                            continue

                    if images_to_add:
                        db.add_all(images_to_add)
                        db.commit()
                        logger.info(f"Saved {len(images_to_add)} images for document {new_document.id}")

            except Exception as img_extract_error:
                # Image extraction failure should not fail the entire upload
                logger.warning(f"Image extraction failed, continuing without images: {img_extract_error}")

        uploaded_files = [
            UploadedFileRead(
                id=str(new_document.id),
                name=new_document.title,
                description=file_description or "",
                category=category.name,
                created_at=new_document.created_at.isoformat()
            )
        ]

        # Naprawiony return z category.name zamiast całego obiektu
        return UploadResponse(
            message="File processed successfully.",
            user_id=user_id,
            file_name=safe_filename,
            file_description=file_description,
            category=category.name,
            uploaded_files=uploaded_files
        )

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error during file upload and processing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
    finally:
        if os.path.exists(file_path):
            try:
                await asyncio.to_thread(os.remove, file_path)
                logger.info(f"Deleted uploaded file: {safe_filename} from {file_path}")
            except Exception as e:
                logger.error(f"Failed to delete uploaded file: {safe_filename}. Error: {e}")


@cache(expire=300)
@router.get("/list/", response_model=List[UploadedFileRead])
async def list_uploaded_files(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    user_id = str(current_user.id_)
    logger.info(f"Fetching uploaded files for user_id: {user_id}")
    try:
        documents = db.query(WorkspaceDocument, FileCategory).join(
            FileCategory,
            WorkspaceDocument.category_id == FileCategory.id,
            isouter=True
        ).filter(
            WorkspaceDocument.user_id == current_user.id_
        ).all()

        uploaded_files = [
            UploadedFileRead(
                id=str(doc.id),
                name=doc.title,
                description="",
                category=cat.name if cat else "Uncategorized",
                created_at=doc.created_at.isoformat(),
            )
            for doc, cat in documents
        ]
        return uploaded_files
    except Exception as e:
        logger.error(f"Error fetching uploaded files: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching uploaded files: {str(e)}")


@router.delete("/delete-file/", response_model=DeleteKnowledgeResponse)
async def delete_knowledge(
        request: DeleteKnowledgeRequest,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    user_id = str(current_user.id_)
    file_name = request.file_name

    deleted_from_vector_store = delete_file_from_vector_store(user_id, file_name)
    if not deleted_from_vector_store:
        logger.warning(f"Could not delete vectors for file: {file_name} from vector store.")

    try:
        document = db.query(WorkspaceDocument).filter(
            WorkspaceDocument.user_id == current_user.id_,
            WorkspaceDocument.original_filename == file_name
        ).first()
        if document:
            # Delete images from storage before deleting database record
            storage_service = get_storage_service()
            await storage_service.delete_document_images(str(document.id))
            logger.info(f"Deleted images from storage for document: {document.id}")

            db.delete(document)
            db.commit()
            logger.info(f"Deleted document record from database: {document}")
        else:
            logger.warning(f"No document record found in database for user_id: {user_id}, file_name: {file_name}")
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting file record from database: {e}")
        raise HTTPException(status_code=500, detail="Error deleting file record from database.")

    return DeleteKnowledgeResponse(
        message="Deletion process completed.",
        deleted_from_vector_store=deleted_from_vector_store
    )


# =============================================================================
# DOCUMENT IMAGES ENDPOINTS
# =============================================================================

from fastapi.responses import FileResponse
from pydantic import BaseModel
import mimetypes


class DocumentImageRead(BaseModel):
    """Schema for document image response."""
    id: str
    page_number: int
    image_index: int
    image_url: str  # URL to fetch the image
    image_type: str
    width: Optional[int] = None
    height: Optional[int] = None
    x_position: Optional[float] = None
    y_position: Optional[float] = None
    alt_text: Optional[str] = None


@router.get("/documents/{document_id}/images", response_model=List[DocumentImageRead])
async def get_document_images(
    document_id: str,
    page_number: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get list of images for a document.
    Optionally filter by page number.
    """
    try:
        doc_uuid = UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document_id format")

    # Verify document ownership
    document = db.query(WorkspaceDocument).filter(
        WorkspaceDocument.id == doc_uuid,
        WorkspaceDocument.user_id == current_user.id_
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Query images
    query = db.query(DocumentImage).filter(DocumentImage.document_id == doc_uuid)

    if page_number is not None:
        query = query.filter(DocumentImage.page_number == page_number)

    images = query.order_by(DocumentImage.page_number, DocumentImage.image_index).all()

    # Build response with URLs
    result = []
    for img in images:
        result.append(DocumentImageRead(
            id=str(img.id),
            page_number=img.page_number,
            image_index=img.image_index,
            image_url=f"/api/files/images/{img.id}",
            image_type=img.image_type,
            width=img.width,
            height=img.height,
            x_position=img.x_position,
            y_position=img.y_position,
            alt_text=img.alt_text
        ))

    return result


@router.get("/images/{image_id}")
async def get_image_file(
    request: Request,
    image_id: str,
    token: Optional[str] = Query(None, description="JWT token for authentication"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Serve an image file by its ID.
    Supports both cookie-based auth and token query param for img src loading.
    For R2 storage: redirects to presigned URL.
    For local storage: serves file directly.
    """
    from fastapi.responses import RedirectResponse, Response

    try:
        img_uuid = UUID(image_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid image_id format")

    # Try to get user from token query param if not authenticated via cookie
    user_id = None
    if current_user:
        user_id = current_user.id_
    elif token:
        # Fix potential URL encoding issues - spaces might have been decoded from + signs
        sanitized_token = token.replace(' ', '+')
        try:
            payload = verify_jwt_token(sanitized_token)
            if payload:
                user_id = payload.get("aud")
                if user_id is not None:
                    user_id = int(user_id)
        except Exception:
            pass

    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Get image with document join to verify ownership
    image = db.query(DocumentImage).join(
        WorkspaceDocument,
        DocumentImage.document_id == WorkspaceDocument.id
    ).filter(
        DocumentImage.id == img_uuid,
        WorkspaceDocument.user_id == user_id
    ).first()

    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    # Get storage service
    storage_service = get_storage_service()

    if storage_service.is_r2_enabled():
        # For R2: redirect to presigned URL
        presigned_url = storage_service.generate_presigned_url(
            image.image_path,
            expiration=3600  # 1 hour
        )
        return RedirectResponse(url=presigned_url, status_code=307)
    else:
        # For local storage: serve file directly
        if not os.path.exists(image.image_path):
            logger.error(f"Image file not found at path: {image.image_path}")
            raise HTTPException(status_code=404, detail="Image file not found")

        # Determine MIME type
        mime_type, _ = mimetypes.guess_type(image.image_path)
        if not mime_type:
            mime_type = f"image/{image.image_type}"

        return FileResponse(
            path=image.image_path,
            media_type=mime_type,
        filename=os.path.basename(image.image_path)
    )


@router.get("/documents/{document_id}/images/by-page/{page_number}", response_model=List[DocumentImageRead])
async def get_images_by_page(
    document_id: str,
    page_number: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get images for a specific page of a document.
    Optimized for lazy loading in document reader.
    """
    try:
        doc_uuid = UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document_id format")

    # Verify document ownership
    document = db.query(WorkspaceDocument).filter(
        WorkspaceDocument.id == doc_uuid,
        WorkspaceDocument.user_id == current_user.id_
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Query images for specific page
    images = db.query(DocumentImage).filter(
        DocumentImage.document_id == doc_uuid,
        DocumentImage.page_number == page_number
    ).order_by(DocumentImage.image_index).all()

    result = []
    for img in images:
        result.append(DocumentImageRead(
            id=str(img.id),
            page_number=img.page_number,
            image_index=img.image_index,
            image_url=f"/api/files/images/{img.id}",
            image_type=img.image_type,
            width=img.width,
            height=img.height,
            x_position=img.x_position,
            y_position=img.y_position,
            alt_text=img.alt_text
        ))

    return result


# =============================================================================
# STORAGE DIAGNOSTICS ENDPOINT (for admin/debug)
# =============================================================================

@router.get("/storage/info")
async def get_storage_info(
    current_user: User = Depends(get_current_user),
):
    """
    Get information about the current storage configuration.
    Useful for debugging and monitoring.
    """
    storage_service = get_storage_service()
    return storage_service.get_storage_info()

