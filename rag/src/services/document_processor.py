"""
Document Processor Service
Handles PDF parsing, text extraction, and section creation for Workspace.
"""
import re
import logging
from typing import List, Dict, Any, Tuple, Optional
from io import BytesIO
import uuid
from dataclasses import dataclass

logger = logging.getLogger(__name__)

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    logger.warning("PyMuPDF not available. PDF processing will be limited.")

try:
    from pdfminer.high_level import extract_text
    from pdfminer.layout import LAParams
    PDFMINER_AVAILABLE = True
except ImportError:
    PDFMINER_AVAILABLE = False


@dataclass
class TextStyle:
    """Represents a text style span."""
    start: int
    end: int
    style: str  # 'bold', 'italic', 'bold_italic'


@dataclass
class ProcessedSection:
    """Represents a processed document section."""
    index: int
    content_text: str
    base_styles: List[Dict[str, Any]]
    section_metadata: Dict[str, Any]
    char_start: int
    char_end: int


class DocumentProcessor:
    """
    Processes uploaded documents (PDF, TXT, DOCX) into sections
    suitable for lazy loading and semantic search.
    """

    # Target section size (characters) - optimize for reading experience
    SECTION_SIZE = 2000  # ~500 words per section
    SECTION_OVERLAP = 200  # Overlap for context continuity

    # Minimum section size to avoid too-small chunks
    MIN_SECTION_SIZE = 200

    def __init__(self):
        self.supported_types = ['pdf', 'txt', 'md', 'docx']

    async def process_file(
        self,
        file_content: bytes,
        filename: str,
        file_type: str
    ) -> Tuple[str, List[ProcessedSection]]:
        """
        Process uploaded file and return title + sections.

        Returns:
            Tuple of (extracted_title, list_of_sections)
        """
        file_type = file_type.lower()

        if file_type == 'pdf':
            return await self._process_pdf(file_content, filename)
        elif file_type in ['txt', 'md']:
            return await self._process_text(file_content, filename)
        elif file_type == 'docx':
            return await self._process_docx(file_content, filename)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    async def _process_pdf(
        self,
        file_content: bytes,
        filename: str
    ) -> Tuple[str, List[ProcessedSection]]:
        """
        Extract text and styles from PDF using PyMuPDF.
        Falls back to pdfminer if PyMuPDF is not available.
        """
        if PYMUPDF_AVAILABLE:
            return await self._process_pdf_pymupdf(file_content, filename)
        elif PDFMINER_AVAILABLE:
            return await self._process_pdf_pdfminer(file_content, filename)
        else:
            raise RuntimeError("No PDF processing library available. Install PyMuPDF or pdfminer.six")

    async def _process_pdf_pymupdf(
        self,
        file_content: bytes,
        filename: str
    ) -> Tuple[str, List[ProcessedSection]]:
        """
        Process PDF using PyMuPDF with style extraction.
        """
        doc = fitz.open(stream=file_content, filetype="pdf")

        # Try to extract title from metadata or first heading
        title = doc.metadata.get("title", "") or self._extract_title_from_filename(filename)

        all_text = ""
        all_styles: List[TextStyle] = []
        page_breaks: List[int] = []

        for page_num, page in enumerate(doc):
            page_start = len(all_text)

            # Extract text blocks with style info
            blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]

            for block in blocks:
                if block["type"] == 0:  # Text block
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            span_start = len(all_text)
                            text = span.get("text", "")
                            all_text += text
                            span_end = len(all_text)

                            # Detect styles from font flags
                            flags = span.get("flags", 0)
                            is_bold = bool(flags & (1 << 4))  # Bold flag
                            is_italic = bool(flags & (1 << 1))  # Italic flag

                            if is_bold and is_italic:
                                all_styles.append(TextStyle(span_start, span_end, "bold_italic"))
                            elif is_bold:
                                all_styles.append(TextStyle(span_start, span_end, "bold"))
                            elif is_italic:
                                all_styles.append(TextStyle(span_start, span_end, "italic"))

                        # Add line break
                        all_text += "\n"

                # Add paragraph break after block
                all_text += "\n"

            page_breaks.append(len(all_text))

        doc.close()

        # Create sections from text
        sections = self._create_sections(all_text, all_styles, page_breaks)

        return title, sections

    async def _process_pdf_pdfminer(
        self,
        file_content: bytes,
        filename: str
    ) -> Tuple[str, List[ProcessedSection]]:
        """
        Fallback PDF processing using pdfminer (no style extraction).
        """
        text = extract_text(BytesIO(file_content), laparams=LAParams())
        title = self._extract_title_from_filename(filename)
        sections = self._create_sections(text, [], [])
        return title, sections

    async def _process_text(
        self,
        file_content: bytes,
        filename: str
    ) -> Tuple[str, List[ProcessedSection]]:
        """
        Process plain text or markdown file.
        """
        # Try different encodings
        for encoding in ['utf-8', 'utf-16', 'latin-1', 'cp1250']:
            try:
                text = file_content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            text = file_content.decode('utf-8', errors='replace')

        title = self._extract_title_from_text(text) or self._extract_title_from_filename(filename)

        # Extract basic markdown styles
        styles = self._extract_markdown_styles(text)

        sections = self._create_sections(text, styles, [])
        return title, sections

    async def _process_docx(
        self,
        file_content: bytes,
        filename: str
    ) -> Tuple[str, List[ProcessedSection]]:
        """
        Process DOCX file.
        """
        try:
            from docx import Document
        except ImportError:
            raise RuntimeError("python-docx not installed. Run: pip install python-docx")

        doc = Document(BytesIO(file_content))

        all_text = ""
        all_styles: List[TextStyle] = []

        for para in doc.paragraphs:
            para_start = len(all_text)

            for run in para.runs:
                run_start = len(all_text)
                all_text += run.text
                run_end = len(all_text)

                # Extract styles from run
                if run.bold and run.italic:
                    all_styles.append(TextStyle(run_start, run_end, "bold_italic"))
                elif run.bold:
                    all_styles.append(TextStyle(run_start, run_end, "bold"))
                elif run.italic:
                    all_styles.append(TextStyle(run_start, run_end, "italic"))

            all_text += "\n\n"

        title = self._extract_title_from_text(all_text) or self._extract_title_from_filename(filename)
        sections = self._create_sections(all_text, all_styles, [])

        return title, sections

    def _create_sections(
        self,
        text: str,
        styles: List[TextStyle],
        page_breaks: List[int]
    ) -> List[ProcessedSection]:
        """
        Split text into sections for lazy loading.
        Uses paragraph boundaries when possible.
        """
        sections = []

        # Split by paragraphs first
        paragraphs = self._split_into_paragraphs(text)

        current_section_text = ""
        current_section_start = 0
        section_index = 0

        for para_text, para_start, para_end in paragraphs:
            # Check if adding this paragraph would exceed section size
            if len(current_section_text) + len(para_text) > self.SECTION_SIZE:
                # Save current section if it has content
                if current_section_text.strip():
                    section = self._create_section(
                        index=section_index,
                        text=current_section_text,
                        char_start=current_section_start,
                        styles=styles,
                        page_breaks=page_breaks
                    )
                    sections.append(section)
                    section_index += 1

                # Start new section
                current_section_text = para_text
                current_section_start = para_start
            else:
                current_section_text += para_text

        # Don't forget the last section
        if current_section_text.strip():
            section = self._create_section(
                index=section_index,
                text=current_section_text,
                char_start=current_section_start,
                styles=styles,
                page_breaks=page_breaks
            )
            sections.append(section)

        return sections

    def _create_section(
        self,
        index: int,
        text: str,
        char_start: int,
        styles: List[TextStyle],
        page_breaks: List[int]
    ) -> ProcessedSection:
        """
        Create a ProcessedSection with adjusted style offsets.
        """
        char_end = char_start + len(text)

        # Filter and adjust styles for this section
        section_styles = []
        for style in styles:
            # Check if style overlaps with this section
            if style.end > char_start and style.start < char_end:
                adjusted_start = max(0, style.start - char_start)
                adjusted_end = min(len(text), style.end - char_start)
                section_styles.append({
                    "start": adjusted_start,
                    "end": adjusted_end,
                    "style": style.style
                })

        # Calculate page number if we have page breaks
        page_number = None
        if page_breaks:
            for i, pb in enumerate(page_breaks):
                if char_start < pb:
                    page_number = i + 1
                    break

        metadata = {}
        if page_number:
            metadata["page"] = page_number

        return ProcessedSection(
            index=index,
            content_text=text,
            base_styles=section_styles,
            section_metadata=metadata,
            char_start=char_start,
            char_end=char_end
        )

    def _split_into_paragraphs(self, text: str) -> List[Tuple[str, int, int]]:
        """
        Split text into paragraphs, preserving positions.
        Returns list of (paragraph_text, start_pos, end_pos).
        """
        paragraphs = []

        # Split by double newlines (paragraph breaks)
        pattern = r'\n\s*\n'
        parts = re.split(pattern, text)

        pos = 0
        for part in parts:
            if part.strip():
                # Find actual position in original text
                actual_start = text.find(part, pos)
                if actual_start == -1:
                    actual_start = pos
                actual_end = actual_start + len(part)

                paragraphs.append((part + "\n\n", actual_start, actual_end))
                pos = actual_end

        return paragraphs

    def _extract_markdown_styles(self, text: str) -> List[TextStyle]:
        """
        Extract basic styles from markdown formatting.
        """
        styles = []

        # Bold: **text** or __text__
        for match in re.finditer(r'\*\*(.+?)\*\*|__(.+?)__', text):
            styles.append(TextStyle(match.start(), match.end(), "bold"))

        # Italic: *text* or _text_
        for match in re.finditer(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)|(?<!_)_(?!_)(.+?)(?<!_)_(?!_)', text):
            styles.append(TextStyle(match.start(), match.end(), "italic"))

        return styles

    def _extract_title_from_text(self, text: str) -> Optional[str]:
        """
        Try to extract title from first heading or first line.
        """
        # Check for markdown heading
        match = re.match(r'^#\s+(.+?)$', text, re.MULTILINE)
        if match:
            return match.group(1).strip()

        # Use first non-empty line
        for line in text.split('\n'):
            line = line.strip()
            if line and len(line) < 200:  # Reasonable title length
                return line

        return None

    def _extract_title_from_filename(self, filename: str) -> str:
        """
        Extract title from filename (remove extension).
        """
        # Remove extension
        name = re.sub(r'\.[^.]+$', '', filename)
        # Replace underscores and hyphens with spaces
        name = re.sub(r'[_-]+', ' ', name)
        return name.strip() or "Untitled Document"


# Singleton instance
document_processor = DocumentProcessor()

