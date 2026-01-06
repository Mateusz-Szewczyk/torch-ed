"""
Workspace Router - Document Reader & AI Assistant
Endpoints for document upload, lazy loading, highlights, and context-aware chat.
"""
import logging
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from ..dependencies import get_db
from ..auth import get_current_user
from ..models import (
    User,
    WorkspaceDocument,
    DocumentSection,
    UserHighlight,
)
from ..services.document_processor import document_processor
from ..services.workspace_chat import WorkspaceChatService, HIGHLIGHT_COLORS

logger = logging.getLogger(__name__)

router = APIRouter(tags=["workspace"])


# =============================================================================
# SCHEMAS
# =============================================================================

class DocumentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)


class DocumentResponse(BaseModel):
    id: UUID
    title: str
    original_filename: Optional[str]
    file_type: Optional[str]
    total_length: int
    total_sections: int
    created_at: str

    class Config:
        from_attributes = True


class SectionStyleSchema(BaseModel):
    start: int
    end: int
    style: str


class SectionResponse(BaseModel):
    id: UUID
    section_index: int
    content_text: str
    base_styles: List[dict]
    section_metadata: dict
    char_start: int
    char_end: int


class HighlightCreate(BaseModel):
    document_id: UUID
    section_id: UUID
    start_offset: int = Field(..., ge=0)
    end_offset: int = Field(..., ge=0)
    color_code: str = Field(..., pattern="^(red|orange|yellow|green|blue|purple)$")
    annotation_text: Optional[str] = None


class HighlightUpdate(BaseModel):
    color_code: Optional[str] = Field(None, pattern="^(red|orange|yellow|green|blue|purple)$")
    annotation_text: Optional[str] = None


class HighlightResponse(BaseModel):
    id: UUID
    document_id: UUID
    section_id: UUID
    start_offset: int
    end_offset: int
    color_code: str
    annotation_text: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


class SectionsWithHighlights(BaseModel):
    sections: List[SectionResponse]
    highlights: List[HighlightResponse]
    total_sections: int
    has_more: bool


class ChatRequest(BaseModel):
    #TODO: Add information about workspace id, because we want to retrieve documents from specific workspace
    #TODO: Update the endpoints to handle workspace id and update flutter frontend accordingly
    query: str = Field(..., min_length=1, max_length=10000)
    document_id: Optional[UUID] = None
    filter_colors: Optional[List[str]] = Field(default=None, description="Colors to filter highlights by")


class ChatContextResponse(BaseModel):
    context_text: str
    context_source: str  # 'highlights' or 'rag'
    highlights_used: List[dict]
    documents_searched: List[str]
    colors_filtered: Optional[List[str]] = None
    total_highlights: Optional[int] = None
    message: Optional[str] = None


# =============================================================================
# DOCUMENT ENDPOINTS
# =============================================================================

@router.post("/documents/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a document (PDF, TXT, DOCX, MD).

    The document will be:
    1. Parsed and split into sections (for lazy loading in Reader)
    2. Indexed in ChromaDB (for RAG semantic search)
    """
    # Validate file type
    filename = file.filename or "document"
    file_ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'txt'

    allowed_types = ['pdf', 'txt', 'md', 'docx']
    if file_ext not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. Allowed: {allowed_types}"
        )

    # Read file content
    content = await file.read()
    if len(content) > 50 * 1024 * 1024:  # 50MB limit
        raise HTTPException(status_code=400, detail="File too large. Maximum size: 50MB")

    try:
        # Process document
        title, sections = await document_processor.process_file(
            file_content=content,
            filename=filename,
            file_type=file_ext
        )

        # Calculate total length
        total_length = sum(len(s.content_text) for s in sections)

        # Create document record
        document = WorkspaceDocument(
            user_id=current_user.id_,
            title=title,
            original_filename=filename,
            file_type=file_ext,
            total_length=total_length,
            total_sections=len(sections)
        )
        db.add(document)
        db.flush()  # Get document ID

        # Create section records
        for section in sections:
            db_section = DocumentSection(
                document_id=document.id,
                section_index=section.index,
                content_text=section.content_text,
                base_styles=section.base_styles,
                section_metadata=section.section_metadata,
                char_start=section.char_start,
                char_end=section.char_end
            )
            db.add(db_section)

        db.commit()
        db.refresh(document)

        # Index in ChromaDB for RAG (async, non-blocking)
        try:
            await _index_document_for_rag(document.id, sections, current_user.id_)
        except Exception as e:
            logger.warning(f"Failed to index document in ChromaDB: {e}")
            # Don't fail the upload, just log warning

        logger.info(f"Document uploaded: {document.id} with {len(sections)} sections")

        return DocumentResponse(
            id=document.id,
            title=document.title,
            original_filename=document.original_filename,
            file_type=document.file_type,
            total_length=document.total_length,
            total_sections=document.total_sections,
            created_at=document.created_at.isoformat()
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Document upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")


@router.get("/documents", response_model=List[DocumentResponse])
async def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List user's documents."""
    query = select(WorkspaceDocument).where(
        WorkspaceDocument.user_id == current_user.id_
    ).order_by(
        WorkspaceDocument.updated_at.desc()
    ).offset(skip).limit(limit)

    documents = db.execute(query).scalars().all()

    return [
        DocumentResponse(
            id=doc.id,
            title=doc.title,
            original_filename=doc.original_filename,
            file_type=doc.file_type,
            total_length=doc.total_length,
            total_sections=doc.total_sections,
            created_at=doc.created_at.isoformat()
        )
        for doc in documents
    ]


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get document metadata."""
    document = db.query(WorkspaceDocument).filter(
        and_(
            WorkspaceDocument.id == document_id,
            WorkspaceDocument.user_id == current_user.id_
        )
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentResponse(
        id=document.id,
        title=document.title,
        original_filename=document.original_filename,
        file_type=document.file_type,
        total_length=document.total_length,
        total_sections=document.total_sections,
        created_at=document.created_at.isoformat()
    )


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a document and all its sections/highlights."""
    document = db.query(WorkspaceDocument).filter(
        and_(
            WorkspaceDocument.id == document_id,
            WorkspaceDocument.user_id == current_user.id_
        )
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete from ChromaDB
    try:
        await _remove_document_from_rag(document_id, current_user.id_)
    except Exception as e:
        logger.warning(f"Failed to remove document from ChromaDB: {e}")

    db.delete(document)
    db.commit()

    return {"message": "Document deleted successfully"}


# =============================================================================
# LAZY LOADING - SECTIONS ENDPOINT
# =============================================================================

@router.get("/documents/{document_id}/sections", response_model=SectionsWithHighlights)
async def get_sections(
    document_id: UUID,
    start_section: int = Query(0, ge=0, description="Starting section index"),
    end_section: int = Query(10, ge=1, description="Ending section index (exclusive)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get document sections for lazy loading.

    Returns sections in range [start_section, end_section) along with
    all highlights for those sections.

    Frontend uses this for infinite scroll - fetches sections as user scrolls.
    """
    # Verify document ownership
    document = db.query(WorkspaceDocument).filter(
        and_(
            WorkspaceDocument.id == document_id,
            WorkspaceDocument.user_id == current_user.id_
        )
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Get sections in range
    sections_query = select(DocumentSection).where(
        and_(
            DocumentSection.document_id == document_id,
            DocumentSection.section_index >= start_section,
            DocumentSection.section_index < end_section
        )
    ).order_by(DocumentSection.section_index)

    sections = db.execute(sections_query).scalars().all()

    # Get highlights for these sections
    section_ids = [s.id for s in sections]

    highlights = []
    if section_ids:
        highlights_query = select(UserHighlight).where(
            UserHighlight.section_id.in_(section_ids)
        ).order_by(UserHighlight.start_offset)

        highlights = db.execute(highlights_query).scalars().all()

    # Check if there are more sections
    has_more = end_section < document.total_sections

    return SectionsWithHighlights(
        sections=[
            SectionResponse(
                id=s.id,
                section_index=s.section_index,
                content_text=s.content_text,
                base_styles=s.base_styles or [],
                section_metadata=s.section_metadata or {},
                char_start=s.char_start,
                char_end=s.char_end
            )
            for s in sections
        ],
        highlights=[
            HighlightResponse(
                id=h.id,
                document_id=h.document_id,
                section_id=h.section_id,
                start_offset=h.start_offset,
                end_offset=h.end_offset,
                color_code=h.color_code,
                annotation_text=h.annotation_text,
                created_at=h.created_at.isoformat()
            )
            for h in highlights
        ],
        total_sections=document.total_sections,
        has_more=has_more
    )


# =============================================================================
# HIGHLIGHTS ENDPOINTS
# =============================================================================

@router.post("/highlights", response_model=HighlightResponse)
async def create_highlight(
    highlight: HighlightCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new highlight.

    Frontend calls this when user selects text and picks a color.
    Debouncing recommended (3s delay) to batch rapid selections.
    """
    # Verify document ownership
    document = db.query(WorkspaceDocument).filter(
        and_(
            WorkspaceDocument.id == highlight.document_id,
            WorkspaceDocument.user_id == current_user.id_
        )
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Verify section belongs to document
    section = db.query(DocumentSection).filter(
        and_(
            DocumentSection.id == highlight.section_id,
            DocumentSection.document_id == highlight.document_id
        )
    ).first()

    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    # Validate offsets
    if highlight.end_offset <= highlight.start_offset:
        raise HTTPException(status_code=400, detail="end_offset must be greater than start_offset")

    if highlight.end_offset > len(section.content_text):
        raise HTTPException(status_code=400, detail="Offset exceeds section length")

    # Create highlight
    db_highlight = UserHighlight(
        document_id=highlight.document_id,
        section_id=highlight.section_id,
        start_offset=highlight.start_offset,
        end_offset=highlight.end_offset,
        color_code=highlight.color_code,
        annotation_text=highlight.annotation_text
    )

    db.add(db_highlight)
    db.commit()
    db.refresh(db_highlight)

    return HighlightResponse(
        id=db_highlight.id,
        document_id=db_highlight.document_id,
        section_id=db_highlight.section_id,
        start_offset=db_highlight.start_offset,
        end_offset=db_highlight.end_offset,
        color_code=db_highlight.color_code,
        annotation_text=db_highlight.annotation_text,
        created_at=db_highlight.created_at.isoformat()
    )


@router.put("/highlights/{highlight_id}", response_model=HighlightResponse)
async def update_highlight(
    highlight_id: UUID,
    update: HighlightUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update highlight color or annotation."""
    highlight = db.query(UserHighlight).join(
        WorkspaceDocument,
        UserHighlight.document_id == WorkspaceDocument.id
    ).filter(
        and_(
            UserHighlight.id == highlight_id,
            WorkspaceDocument.user_id == current_user.id_
        )
    ).first()

    if not highlight:
        raise HTTPException(status_code=404, detail="Highlight not found")

    if update.color_code is not None:
        highlight.color_code = update.color_code

    if update.annotation_text is not None:
        highlight.annotation_text = update.annotation_text

    db.commit()
    db.refresh(highlight)

    return HighlightResponse(
        id=highlight.id,
        document_id=highlight.document_id,
        section_id=highlight.section_id,
        start_offset=highlight.start_offset,
        end_offset=highlight.end_offset,
        color_code=highlight.color_code,
        annotation_text=highlight.annotation_text,
        created_at=highlight.created_at.isoformat()
    )


@router.delete("/highlights/{highlight_id}")
async def delete_highlight(
    highlight_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a highlight."""
    highlight = db.query(UserHighlight).join(
        WorkspaceDocument,
        UserHighlight.document_id == WorkspaceDocument.id
    ).filter(
        and_(
            UserHighlight.id == highlight_id,
            WorkspaceDocument.user_id == current_user.id_
        )
    ).first()

    if not highlight:
        raise HTTPException(status_code=404, detail="Highlight not found")

    db.delete(highlight)
    db.commit()

    return {"message": "Highlight deleted"}


# =============================================================================
# SEARCH & PAGE NAVIGATION ENDPOINTS
# =============================================================================

@router.get("/documents/{document_id}/search")
async def search_document_text(
    document_id: UUID,
    query: str = Query(..., min_length=1, max_length=500, description="Text to search for"),
    context_sections: int = Query(1, ge=0, le=5, description="Number of sections to include before/after match"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Search for text within a document.

    Returns matching sections with context sections before and after.
    Useful for "jump to text" functionality in the reader.

    Args:
        document_id: UUID of the document to search
        query: Text string to search for (case-insensitive)
        context_sections: How many sections to include before/after the matching section

    Returns:
        List of search results with section info and match positions
    """
    # Verify document ownership
    document = db.query(WorkspaceDocument).filter(
        and_(
            WorkspaceDocument.id == document_id,
            WorkspaceDocument.user_id == current_user.id_
        )
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Get all sections
    sections = db.query(DocumentSection).filter(
        DocumentSection.document_id == document_id
    ).order_by(DocumentSection.section_index).all()

    if not sections:
        return {"results": [], "total_matches": 0}

    # Search through sections (case-insensitive)
    query_lower = query.lower()
    results = []

    for section in sections:
        content_lower = section.content_text.lower()

        # Find all occurrences in this section
        start_pos = 0
        matches_in_section = []

        while True:
            pos = content_lower.find(query_lower, start_pos)
            if pos == -1:
                break
            matches_in_section.append({
                "start_offset": pos,
                "end_offset": pos + len(query),
                "match_text": section.content_text[pos:pos + len(query)]
            })
            start_pos = pos + 1

        if matches_in_section:
            # Get context sections
            section_idx = section.section_index
            start_idx = max(0, section_idx - context_sections)
            end_idx = min(len(sections), section_idx + context_sections + 1)

            context_section_indices = list(range(start_idx, end_idx))

            # Get page number from metadata
            page_number = (section.section_metadata or {}).get("page_number", 1)

            results.append({
                "section_id": str(section.id),
                "section_index": section.section_index,
                "page_number": page_number,
                "matches": matches_in_section,
                "match_count": len(matches_in_section),
                "context_section_indices": context_section_indices,
                "preview": section.content_text[:200] + "..." if len(section.content_text) > 200 else section.content_text
            })

    return {
        "results": results,
        "total_matches": sum(r["match_count"] for r in results),
        "sections_with_matches": len(results)
    }


@router.get("/documents/{document_id}/pages")
async def get_document_pages(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get list of unique pages in a document with their section ranges.

    Used for page selector/navigation in document reader.

    Returns:
        List of pages with their section index ranges
    """
    # Verify document ownership
    document = db.query(WorkspaceDocument).filter(
        and_(
            WorkspaceDocument.id == document_id,
            WorkspaceDocument.user_id == current_user.id_
        )
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Get all sections with their page numbers
    sections = db.query(DocumentSection).filter(
        DocumentSection.document_id == document_id
    ).order_by(DocumentSection.section_index).all()

    if not sections:
        return {"pages": [], "total_pages": 0}

    # Build page mapping
    pages_dict = {}  # page_number -> {start_section_index, end_section_index, section_count}

    for section in sections:
        page_num = (section.section_metadata or {}).get("page_number", 1)

        if page_num not in pages_dict:
            pages_dict[page_num] = {
                "page_number": page_num,
                "start_section_index": section.section_index,
                "end_section_index": section.section_index,
                "section_count": 1,
                "section_ids": [str(section.id)]
            }
        else:
            pages_dict[page_num]["end_section_index"] = section.section_index
            pages_dict[page_num]["section_count"] += 1
            pages_dict[page_num]["section_ids"].append(str(section.id))

    # Sort by page number and return
    pages = sorted(pages_dict.values(), key=lambda p: p["page_number"])
    total_pages = (sections[0].section_metadata or {}).get("total_pages", len(pages)) if sections else 0

    return {
        "pages": pages,
        "total_pages": total_pages,
        "total_sections": document.total_sections
    }


@router.get("/documents/{document_id}/sections/by-page/{page_number}")
async def get_sections_by_page(
    document_id: UUID,
    page_number: int,
    context_sections: int = 3,  # Number of sections before/after to include
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all sections for a specific page with context sections.

    Args:
        document_id: UUID of the document
        page_number: Page number (1-based)
        context_sections: Number of sections to include before/after the page (default 3)

    Returns:
        Sections belonging to that page with highlights, plus context sections
        and the index of the first section that starts this page.
    """
    # Verify document ownership
    document = db.query(WorkspaceDocument).filter(
        and_(
            WorkspaceDocument.id == document_id,
            WorkspaceDocument.user_id == current_user.id_
        )
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Get sections for this page using JSONB query
    page_sections = db.query(DocumentSection).filter(
        and_(
            DocumentSection.document_id == document_id,
            DocumentSection.section_metadata["page_number"].as_integer() == page_number
        )
    ).order_by(DocumentSection.section_index).all()

    if not page_sections:
        return {
            "page_number": page_number,
            "sections": [],
            "highlights": [],
            "section_count": 0,
            "page_start_section_index": None,
            "context_loaded": False
        }

    # Find the section index of the first section for this page (is_page_start=True)
    page_start_section_index = None
    for section in page_sections:
        meta = section.section_metadata or {}
        if meta.get("is_page_start", False):
            page_start_section_index = section.section_index
            break

    # If no is_page_start found, use the first section of the page
    if page_start_section_index is None:
        page_start_section_index = page_sections[0].section_index

    # Get context sections before and after
    min_section_index = max(0, page_sections[0].section_index - context_sections)
    max_section_index = page_sections[-1].section_index + context_sections

    # Fetch all sections in the range
    all_sections = db.query(DocumentSection).filter(
        and_(
            DocumentSection.document_id == document_id,
            DocumentSection.section_index >= min_section_index,
            DocumentSection.section_index <= max_section_index
        )
    ).order_by(DocumentSection.section_index).all()

    # Get highlights for all sections
    section_ids = [s.id for s in all_sections]
    highlights = []

    if section_ids:
        highlights_query = select(UserHighlight).where(
            UserHighlight.section_id.in_(section_ids)
        ).order_by(UserHighlight.start_offset)
        highlights = db.execute(highlights_query).scalars().all()

    return {
        "page_number": page_number,
        "sections": [
            SectionResponse(
                id=s.id,
                section_index=s.section_index,
                content_text=s.content_text,
                base_styles=s.base_styles or [],
                section_metadata=s.section_metadata or {},
                char_start=s.char_start,
                char_end=s.char_end
            )
            for s in all_sections
        ],
        "highlights": [
            HighlightResponse(
                id=h.id,
                document_id=h.document_id,
                section_id=h.section_id,
                start_offset=h.start_offset,
                end_offset=h.end_offset,
                color_code=h.color_code,
                annotation_text=h.annotation_text,
                created_at=h.created_at.isoformat()
            )
            for h in highlights
        ],
        "section_count": len(all_sections),
        "page_start_section_index": page_start_section_index,
        "context_loaded": context_sections > 0
    }


@router.post("/highlights/batch", response_model=List[HighlightResponse])
async def create_highlights_batch(
    highlights: List[HighlightCreate],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create multiple highlights in one request.
    Use this for debounced batch saves from frontend.
    """
    if len(highlights) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 highlights per batch")

    created = []

    for h in highlights:
        # Verify document ownership
        document = db.query(WorkspaceDocument).filter(
            and_(
                WorkspaceDocument.id == h.document_id,
                WorkspaceDocument.user_id == current_user.id_
            )
        ).first()

        if not document:
            continue

        db_highlight = UserHighlight(
            document_id=h.document_id,
            section_id=h.section_id,
            start_offset=h.start_offset,
            end_offset=h.end_offset,
            color_code=h.color_code,
            annotation_text=h.annotation_text
        )
        db.add(db_highlight)
        created.append(db_highlight)

    db.commit()

    return [
        HighlightResponse(
            id=h.id,
            document_id=h.document_id,
            section_id=h.section_id,
            start_offset=h.start_offset,
            end_offset=h.end_offset,
            color_code=h.color_code,
            annotation_text=h.annotation_text,
            created_at=h.created_at.isoformat()
        )
        for h in created
    ]


# =============================================================================
# CHAT HELPER ENDPOINTS
# =============================================================================

# NOTE: Main chat context logic has been moved to /api/query/ endpoint
# which handles both normal and workspace chat types.
# Use chat_type="workspace" and workspace_metadata with filter_colors to get
# highlight-filtered context.

@router.get("/chat/colors")
async def get_highlight_colors():
    """
    Get available highlight colors with their meanings.
    Use this to populate the color picker and filter chips in UI.
    """
    return HIGHLIGHT_COLORS


@router.get("/documents/{document_id}/highlight-summary")
async def get_document_highlight_summary(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get summary of highlights by color for a document.
    Shows which colors have been used and how many highlights each has.
    """
    service = WorkspaceChatService(db=db, user_id=current_user.id_)
    return await service.get_document_highlight_summary(document_id)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def _index_document_for_rag(document_id: UUID, sections, user_id: int):
    """
    Index document sections in ChromaDB for RAG search.
    """
    try:
        from ..vector_store import add_user_document

        documents = []
        metadatas = []
        ids = []

        for section in sections:
            documents.append(section.content_text)
            metadatas.append({
                'document_id': str(document_id),
                'section_index': section.index,
                'user_id': str(user_id),
                'type': 'workspace_document'
            })
            ids.append(f"workspace_{document_id}_{section.index}")

        if documents:
            # Use existing vector store function
            for doc, meta, doc_id in zip(documents, metadatas, ids):
                add_user_document(
                    user_id=user_id,
                    document=doc,
                    metadata=meta,
                    doc_id=doc_id
                )

        logger.info(f"Indexed {len(documents)} sections for document {document_id}")
    except Exception as e:
        logger.warning(f"Failed to index document: {e}")


async def _remove_document_from_rag(document_id: UUID, user_id: int):
    """
    Remove document from ChromaDB.
    """
    try:
        from ..vector_store import delete_user_documents

        delete_user_documents(
            user_id=user_id,
            where={'document_id': str(document_id)}
        )
        logger.info(f"Removed document {document_id} from ChromaDB")
    except Exception as e:
        logger.warning(f"Error removing from ChromaDB: {e}")

