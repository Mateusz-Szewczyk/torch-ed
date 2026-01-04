# pdf_processor.py
import fitz
import PyPDF2
import logging
import os
import re
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass

# Import the new table extractor
try:
    from .table_extractor import PDFTableExtractor, ExtractedTable, PDFPLUMBER_AVAILABLE
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    PDFTableExtractor = None
    ExtractedTable = None

logger = logging.getLogger(__name__)


@dataclass
class ImageInfo:
    """Represents an extracted image from a PDF page."""
    page_number: int  # 1-based page number
    image_index: int  # Index on the page (0-based)
    image_data: bytes  # Raw image bytes
    image_type: str  # 'png', 'jpeg', etc.
    width: int
    height: int
    x_position: float  # Position on page (0-1 range)
    y_position: float  # Position on page (0-1 range)


@dataclass
class TableInfo:
    """Represents an extracted table from a PDF page."""
    page_number: int  # 1-based page number
    table_index: int  # Index on the page (0-based)
    headers: List[str]  # Column headers
    rows: List[List[str]]  # Table rows
    markdown: str  # Pre-formatted markdown representation
    bbox: Optional[Tuple[float, float, float, float]] = None  # Bounding box (x0, y0, x1, y1)


class PageContent:
    """Represents content from a single PDF page."""
    def __init__(self, page_number: int, text: str):
        self.page_number = page_number  # 1-based page number
        self.text = text


class PDFProcessor:
    def __init__(self, language='pol', device='cpu'):
        """
        Initializes the PDFProcessor with specified configurations.

        Args:
            language (str, optional): Language code for OCR. Defaults to 'pol' (Polish).
            device (str, optional): Device to run OCR on (e.g., 'cuda' for GPU, 'cpu').
                Defaults to 'cpu'.
        """
        self.language = language
        # Usunięto inicjalizację pix2text, ponieważ jest ona wyłączona

    def process_pdf(self, pdf_file, start_page=0, end_page=None):
        """
           Processes a PDF file and extracts its content into a single text file.

           The method determines the type of PDF (text-based, image-based, or mixed) and
           applies the appropriate extraction strategy. The extracted text is returned as a string.

           Args:
               pdf_file (str): Path to the PDF file to be processed.
               start_page (int, optional): Starting page number (0-based index) for extraction.
                   Defaults to 0.
               end_page (int, optional): Ending page number (exclusive) for extraction.
                   Defaults to None, which processes up to the last page.

           Returns:
               str or None: Extracted text upon successful extraction,
                   or None if extraction fails.
        """
        # Ensure start_page is an integer
        if start_page is None:
            start_page = 0
        if end_page is not None and not isinstance(end_page, int):
            end_page = None

        pdf_type = self._determine_pdf_type(pdf_file)

        try:
            if pdf_type == "text_based":
                text = self._pdf_to_text(pdf_file, start_page, end_page)
            elif pdf_type == "image_based":
                print("PDF is image-based. Skipping processing as per user request.")
                return None
            elif pdf_type == "mixed_content":
                # Process only the text content, skip images
                text = self._extract_text_directly_from_range(pdf_file, start_page, end_page)
            else:
                print("Cannot process PDF content. Unsupported or empty PDF.")
                return None

            if text:
                return text
            else:
                print("No text extracted from the PDF.")
                return None
        except Exception as e:
            print(f"Error processing PDF file {pdf_file}: {e}")
            return None

    def process_pdf_with_pages(self, pdf_file, start_page=0, end_page=None) -> List[PageContent]:
        """
        Processes a PDF file and extracts content PER PAGE.

        This method preserves page boundaries so that sections can track
        which page they came from.

        Args:
            pdf_file (str): Path to the PDF file to be processed.
            start_page (int, optional): Starting page number (0-based index) for extraction.
                Defaults to 0.
            end_page (int, optional): Ending page number (exclusive) for extraction.
                Defaults to None, which processes up to the last page.

        Returns:
            List[PageContent]: List of PageContent objects with page numbers and text.
        """
        if start_page is None:
            start_page = 0
        if end_page is not None and not isinstance(end_page, int):
            end_page = None

        pdf_type = self._determine_pdf_type(pdf_file)
        pages: List[PageContent] = []

        try:
            if pdf_type == "text_based":
                pages = self._pdf_to_pages(pdf_file, start_page, end_page)
            elif pdf_type == "image_based":
                logger.warning("PDF is image-based. Skipping processing.")
                return []
            elif pdf_type == "mixed_content":
                pages = self._extract_pages_directly(pdf_file, start_page, end_page)
            else:
                logger.warning("Cannot process PDF content. Unsupported or empty PDF.")
                return []

            return pages
        except Exception as e:
            logger.error(f"Error processing PDF file {pdf_file}: {e}")
            return []

    def _pdf_to_pages(self, pdf_path, start_page=0, end_page=None) -> List[PageContent]:
        """
        Extract text from a text-based PDF, preserving page boundaries.

        Returns:
            List[PageContent]: List of page contents with page numbers.
        """
        pages = []
        try:
            with open(pdf_path, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                total_pages = len(pdf_reader.pages)

                start_page = max(0, min(start_page, total_pages - 1))
                end_page = min(end_page if end_page is not None else total_pages, total_pages)

                logger.info(f"Extracting text from pages {start_page + 1} to {end_page} out of {total_pages}")

                for page_num in range(start_page, end_page):
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        pages.append(PageContent(
                            page_number=page_num + 1,  # 1-based page number
                            text=page_text.strip()
                        ))
                    else:
                        logger.debug(f"No text found on page {page_num + 1}")

            return pages
        except Exception as e:
            logger.error(f"Error extracting pages from PDF: {e}")
            return []

    def _extract_pages_directly(self, pdf_file, start_page=0, end_page=None) -> List[PageContent]:
        """
        Extract text directly from each page, preserving page boundaries.
        Uses fitz (PyMuPDF) for better extraction.

        Returns:
            List[PageContent]: List of page contents with page numbers.
        """
        pages = []
        try:
            with fitz.open(pdf_file) as doc:
                num_pages = doc.page_count
                start = max(0, start_page)
                end = min(end_page if end_page is not None else num_pages, num_pages)

                logger.info(f"Extracting pages from {start + 1} to {end} out of {num_pages}")

                for i in range(start, end):
                    try:
                        page = doc.load_page(i)
                        # Use text extraction with better line break preservation
                        text = self._extract_text_with_structure(page)
                        if text and text.strip():
                            pages.append(PageContent(
                                page_number=i + 1,  # 1-based page number
                                text=text.strip()
                            ))
                        else:
                            logger.debug(f"No text found on page {i + 1}")
                    except Exception as e:
                        logger.error(f"Error extracting text from page {i + 1}: {e}")

            return pages
        except Exception as e:
            logger.error(f"Error opening PDF file {pdf_file}: {e}")
            return []

    def _extract_text_with_structure(self, page) -> str:
        """
        Extract text from a PDF page while preserving structure (especially for algorithms).

        Uses block-aware extraction to better preserve line breaks and structure.
        """
        try:
            # Try to get text blocks which preserves structure better
            blocks = page.get_text("dict")["blocks"]
            lines_text = []

            for block in blocks:
                if "lines" in block:  # Text block
                    for line in block["lines"]:
                        line_text = ""
                        for span in line["spans"]:
                            line_text += span["text"]
                        if line_text.strip():
                            lines_text.append(line_text.strip())
                    # Add paragraph break after block if it has multiple lines
                    if len(block["lines"]) > 0:
                        lines_text.append("")  # Empty line for paragraph break

            # Clean up excessive empty lines
            result_lines = []
            prev_empty = False
            for line in lines_text:
                if line == "":
                    if not prev_empty:
                        result_lines.append("")
                        prev_empty = True
                else:
                    result_lines.append(line)
                    prev_empty = False

            return "\n".join(result_lines)
        except Exception as e:
            logger.warning(f"Block-based extraction failed, falling back to simple: {e}")
            return page.get_text()

    def extract_images(
        self,
        pdf_file: str,
        start_page: int = 0,
        end_page: Optional[int] = None,
        min_width: int = 100,
        min_height: int = 100
    ) -> List[ImageInfo]:
        """
        Extract images from PDF pages.

        Args:
            pdf_file: Path to the PDF file
            start_page: Starting page (0-based)
            end_page: Ending page (exclusive), None for all
            min_width: Minimum image width to extract (filters small icons)
            min_height: Minimum image height to extract

        Returns:
            List of ImageInfo objects with extracted images
        """
        images = []

        try:
            with fitz.open(pdf_file) as doc:
                num_pages = doc.page_count
                start = max(0, start_page)
                end = min(end_page if end_page is not None else num_pages, num_pages)

                logger.info(f"Extracting images from pages {start + 1} to {end}")

                for page_idx in range(start, end):
                    try:
                        page = doc.load_page(page_idx)
                        page_rect = page.rect
                        page_width = page_rect.width
                        page_height = page_rect.height

                        image_list = page.get_images(full=True)

                        for img_idx, img_info in enumerate(image_list):
                            try:
                                xref = img_info[0]  # Image xref
                                base_image = doc.extract_image(xref)

                                if not base_image:
                                    continue

                                image_bytes = base_image.get("image")
                                image_ext = base_image.get("ext", "png")
                                width = base_image.get("width", 0)
                                height = base_image.get("height", 0)

                                # Filter out small images (icons, bullets, etc.)
                                if width < min_width or height < min_height:
                                    logger.debug(f"Skipping small image on page {page_idx + 1}: {width}x{height}")
                                    continue

                                # Try to get image position on page
                                x_pos, y_pos = 0.5, 0.5  # Default to center

                                # Find image rectangle on page
                                for img_rect in page.get_image_rects(xref):
                                    if img_rect:
                                        # Normalize position to 0-1 range
                                        x_pos = (img_rect.x0 + img_rect.x1) / 2 / page_width if page_width else 0.5
                                        y_pos = (img_rect.y0 + img_rect.y1) / 2 / page_height if page_height else 0.5
                                        break

                                images.append(ImageInfo(
                                    page_number=page_idx + 1,  # 1-based
                                    image_index=img_idx,
                                    image_data=image_bytes,
                                    image_type=image_ext.lower(),
                                    width=width,
                                    height=height,
                                    x_position=x_pos,
                                    y_position=y_pos
                                ))

                                logger.debug(f"Extracted image from page {page_idx + 1}: {width}x{height} ({image_ext})")

                            except Exception as e:
                                logger.warning(f"Failed to extract image {img_idx} from page {page_idx + 1}: {e}")
                                continue

                    except Exception as e:
                        logger.error(f"Error processing page {page_idx + 1} for images: {e}")
                        continue

                logger.info(f"Extracted {len(images)} images from PDF")
                return images

        except Exception as e:
            logger.error(f"Error opening PDF for image extraction: {e}")
            return []

    def extract_tables(
        self,
        pdf_file: str,
        start_page: int = 0,
        end_page: Optional[int] = None,
    ) -> List[TableInfo]:
        """
        Extract tables from PDF pages.

        Uses only pdfplumber's built-in table detection for reliable results.
        Only extracts tables with visible borders/lines.

        Args:
            pdf_file: Path to the PDF file
            start_page: Starting page (0-based)
            end_page: Ending page (exclusive), None for all

        Returns:
            List of TableInfo objects with extracted tables
        """
        tables = []

        # Use pdfplumber's simple table detection
        if PDFPLUMBER_AVAILABLE and PDFTableExtractor is not None:
            try:
                extractor = PDFTableExtractor(min_rows=2, min_columns=2)
                pdfplumber_tables = extractor.extract_tables_from_pdf(pdf_file)

                for pt in pdfplumber_tables:
                    # Filter by page range
                    if start_page <= pt.page_number - 1 < (end_page if end_page else float('inf')):
                        tables.append(TableInfo(
                            page_number=pt.page_number,
                            table_index=pt.table_index,
                            headers=pt.headers,
                            rows=pt.rows,
                            markdown=pt.markdown,
                            bbox=None
                        ))
                        logger.info(
                            f"[TABLE] Found table on page {pt.page_number}: "
                            f"{len(pt.headers)} cols, {len(pt.rows)} rows"
                        )

                logger.info(f"[TABLE] Total tables extracted: {len(tables)}")
                return tables

            except Exception as e:
                logger.warning(f"[TABLE] Table extraction failed: {e}")
                return []

        logger.info("[TABLE] pdfplumber not available, skipping table extraction")
        return []


    def _convert_to_markdown_table(self, headers: List[str], rows: List[List[str]]) -> str:
        """
        Convert extracted table data to a pipe-separated markdown table.

        Args:
            headers: List of column headers
            rows: List of rows, each row is a list of cell values

        Returns:
            str: Markdown-formatted table as a string
        """
        if not headers:
            return ""

        # Normalize column count
        max_cols = max(len(headers), max((len(row) for row in rows), default=0))

        while len(headers) < max_cols:
            headers.append('')

        normalized_rows = []
        for row in rows:
            normalized_row = list(row)
            while len(normalized_row) < max_cols:
                normalized_row.append('')
            normalized_rows.append(normalized_row[:max_cols])

        # Calculate column widths for alignment
        col_widths = []
        for i in range(max_cols):
            col_values = [headers[i]] + [row[i] for row in normalized_rows]
            col_widths.append(max(len(str(v)) for v in col_values))

        # Format header
        header_row = "| " + " | ".join(
            str(h).ljust(w) for h, w in zip(headers, col_widths)
        ) + " |"

        # Format separator (required for markdown tables)
        separator_row = "|" + "|".join(
            "-" * (w + 2) for w in col_widths
        ) + "|"

        # Format data rows
        data_rows = [
            "| " + " | ".join(
                str(cell).ljust(w) for cell, w in zip(row, col_widths)
            ) + " |"
            for row in normalized_rows
        ]

        return "\n".join([header_row, separator_row] + data_rows)

    def get_total_pages(self, pdf_file) -> int:
        """Get total number of pages in a PDF file."""
        try:
            with open(pdf_file, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                return len(pdf_reader.pages)
        except Exception as e:
            logger.error(f"Error getting page count: {e}")
            return 0

    def _pdf_to_text(self, pdf_path, start_page=0, end_page=None):
        """
        Extract text directly from a text-based PDF.

        :param pdf_path: Path to the PDF file
        :param start_page: Starting page number (0-based index)
        :param end_page: Ending page number (exclusive)
        :return: Extracted text as a string
        """
        try:
            with open(pdf_path, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                total_pages = len(pdf_reader.pages)

                # Set default values for start_page and end_page if not provided
                start_page = max(0, min(start_page, total_pages - 1))
                end_page = min(end_page if end_page is not None else total_pages, total_pages)

                print(f"Extracting text from pages {start_page + 1} to {end_page} out of {total_pages}")

                text = ''
                for page_num in range(start_page, end_page):
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text()
                    if page_text:
                        # Don't add page markers - just clean text with paragraph separation
                        text += page_text.strip() + '\n\n'
                    else:
                        print(f"No text found on page {page_num + 1}")
                return text
        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
            return None

    def _extract_text_directly_from_range(self, pdf_file, start_page=0, end_page=None):
        """
        Extract text directly from a range of pages in a PDF, skipping images.

        :param pdf_file: Path to the PDF file
        :param start_page: Starting page number (0-based index)
        :param end_page: Ending page number (exclusive)
        :return: Extracted text as a string
        """
        all_text = []
        try:
            with fitz.open(pdf_file) as doc:
                num_pages = doc.page_count
                start = max(0, start_page)
                end = min(end_page if end_page is not None else num_pages, num_pages)

                print(f"Extracting text from pages {start + 1} to {end} out of {num_pages}")

                for i in range(start, end):
                    try:
                        page = doc.load_page(i)
                        text = page.get_text()
                        if text and text.strip():
                            # Don't add page markers - just clean text with paragraph separation
                            all_text.append(text.strip() + '\n\n')
                        else:
                            print(f"No text found on page {i + 1}")
                    except Exception as e:
                        logger.error(f"Error extracting text from page {i + 1}: {e}", exc_info=True)

            return ''.join(all_text)
        except Exception as e:
            logger.error(f"Error opening PDF file {pdf_file}: {e}", exc_info=True)
            return None

    def _analyze_pdf_content(self, pdf_path, sample_size=5):
        """
        Analyzes a PDF to determine if it contains extractable text or if it's primarily image-based.

        :param pdf_path: Path to the PDF file
        :param sample_size: Number of pages to sample (default is 5)
        :return: A tuple (has_text, has_images, total_pages)
        """
        has_text = False
        has_images = False

        try:
            with open(pdf_path, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                total_pages = len(pdf_reader.pages)
                # Determine how many pages to check
                pages_to_check = min(sample_size, total_pages)

                for i in range(pages_to_check):
                    page = pdf_reader.pages[i]

                    # Check for text
                    if not has_text:
                        text = page.extract_text()
                        if text and text.strip():
                            has_text = True

                    # Check for images
                    if not has_images and '/XObject' in page['/Resources']:
                        x_object = page['/Resources']['/XObject'].get_object()
                        if x_object:
                            for obj in x_object:
                                if x_object[obj]['/Subtype'] == '/Image':
                                    has_images = True
                                    break

                    # If we've found both text and images, we can stop checking
                    if has_text and has_images:
                        break
        except Exception as e:
            print(f"Error analyzing PDF content: {e}")
            return False, False, 0

        return has_text, has_images, total_pages

    def _determine_pdf_type(self, pdf_path):
        """
        Determines the type of PDF based on its content.

        :param pdf_path: Path to the PDF file
        :return: A string describing the PDF type
        """
        print(pdf_path)
        has_text, has_images, total_pages = self._analyze_pdf_content(pdf_path)

        if has_text and not has_images:
            return "text_based"
        elif has_images and not has_text:
            return "image_based"
        elif has_text and has_images:
            return "mixed_content"
        else:
            return False

    def process_pdf_with_tables(
        self,
        pdf_file: str,
        start_page: int = 0,
        end_page: Optional[int] = None
    ) -> List[PageContent]:
        """
        Process PDF and extract text with tables properly formatted.

        Uses pdfplumber for reliable table detection (tables with visible borders).

        Args:
            pdf_file: Path to the PDF file
            start_page: Starting page (0-based)
            end_page: Ending page (exclusive)

        Returns:
            List of PageContent objects with tables formatted as markdown
        """
        pages = []
        total_tables_found = 0

        # Pre-extract tables using pdfplumber
        pdfplumber_tables_by_page: Dict[int, List[str]] = {}

        if PDFPLUMBER_AVAILABLE and PDFTableExtractor is not None:
            try:
                extractor = PDFTableExtractor(min_rows=2, min_columns=2)
                extracted_tables = extractor.extract_tables_from_pdf(pdf_file)

                for table in extracted_tables:
                    page_num = table.page_number - 1  # Convert to 0-based
                    if page_num not in pdfplumber_tables_by_page:
                        pdfplumber_tables_by_page[page_num] = []
                    pdfplumber_tables_by_page[page_num].append(table.markdown)
                    total_tables_found += 1
                    logger.info(
                        f"[TABLE] pdfplumber: Page {table.page_number}: "
                        f"{len(table.headers)} cols, {len(table.rows)} rows"
                    )

                if pdfplumber_tables_by_page:
                    logger.info(f"[TABLE] pdfplumber pre-extracted {total_tables_found} table(s)")
            except Exception as e:
                logger.warning(f"[TABLE] pdfplumber pre-extraction failed: {e}")

        try:
            with fitz.open(pdf_file) as doc:
                num_pages = doc.page_count
                start = max(0, start_page)
                end = min(end_page if end_page is not None else num_pages, num_pages)

                logger.info(f"Processing PDF with tables from pages {start + 1} to {end}")

                for page_idx in range(start, end):
                    try:
                        page = doc.load_page(page_idx)
                        # Use structured extraction for better line preservation
                        page_text = self._extract_text_with_structure(page)

                        # Check if we have pdfplumber tables for this page
                        page_tables = []

                        if page_idx in pdfplumber_tables_by_page:
                            for markdown in pdfplumber_tables_by_page[page_idx]:
                                page_tables.append({
                                    'markdown': markdown,
                                    'bbox': None
                                })

                        # If no pdfplumber tables, try PyMuPDF's find_tables()
                        if not page_tables:
                            try:
                                table_finder = page.find_tables()

                                # Handle different PyMuPDF versions
                                tables_list = []
                                if hasattr(table_finder, 'tables'):
                                    tables_list = table_finder.tables
                                elif hasattr(table_finder, '__iter__'):
                                    tables_list = list(table_finder)
                                else:
                                    try:
                                        for t in table_finder:
                                            tables_list.append(t)
                                    except TypeError:
                                        pass

                                tables_on_page = len(tables_list)

                                if tables_on_page > 0:
                                    logger.info(f"[TABLE] Page {page_idx + 1}: PyMuPDF found {tables_on_page} potential table(s)")

                                for table_idx, table in enumerate(tables_list):
                                    try:
                                        extracted = table.extract()
                                        if extracted and len(extracted) >= 2:
                                            headers = [str(c).strip() if c else '' for c in extracted[0]]
                                            rows = [
                                                [str(c).strip() if c else '' for c in row]
                                                for row in extracted[1:]
                                            ]

                                            if headers and any(h for h in headers):
                                                markdown = self._convert_to_markdown_table(headers, rows)
                                                if markdown:
                                                    page_tables.append({
                                                        'markdown': markdown,
                                                        'bbox': table.bbox if hasattr(table, 'bbox') else None
                                                    })
                                                    total_tables_found += 1
                                                    logger.info(f"[TABLE] Page {page_idx + 1}, Table {table_idx + 1}: {len(headers)} cols, {len(rows)} rows - extracted successfully")
                                    except Exception as te:
                                        logger.warning(f"[TABLE] Failed to extract table {table_idx} on page {page_idx + 1}: {te}")
                            except AttributeError as ae:
                                # find_tables() not available
                                logger.debug(f"[TABLE] find_tables() not available: {ae}")
                            except Exception as table_err:
                                logger.warning(f"[TABLE] Error during table extraction on page {page_idx + 1}: {table_err}")


                        # If tables were found, insert them into the text content
                        if page_tables:
                            # For simplicity, append tables at the end of page text
                            # with clear markers
                            for table_data in page_tables:
                                page_text += f"\n\n{table_data['markdown']}\n\n"

                        if page_text and page_text.strip():
                            pages.append(PageContent(
                                page_number=page_idx + 1,
                                text=page_text.strip()
                            ))

                    except Exception as e:
                        logger.error(f"Error processing page {page_idx + 1}: {e}")
                        # Try fallback text extraction
                        try:
                            page = doc.load_page(page_idx)
                            text = page.get_text()
                            if text and text.strip():
                                pages.append(PageContent(
                                    page_number=page_idx + 1,
                                    text=text.strip()
                                ))
                        except:
                            pass

                logger.info(f"[TABLE] Total tables extracted from PDF: {total_tables_found}")
                logger.info(f"Processed {len(pages)} pages with table integration")
                return pages

        except Exception as e:
            logger.error(f"Error processing PDF with tables: {e}")
            # Fallback to standard processing
            return self.process_pdf_with_pages(pdf_file, start_page, end_page)

# Example usage
if __name__ == "__main__":
    pdf_path = '../matematyks.pdf'
    processor = PDFProcessor()

    desired_start_page = 74  # 0-based index (i.e., page 75)
    desired_end_page = 79    # Exclusive (i.e., up to page 79)

    result = processor.process_pdf(pdf_path, start_page=desired_start_page, end_page=desired_end_page)

    if result:
        print("PDF preprocessing and text extraction completed successfully.")
        print(result)  # Print the extracted text
    else:
        print("An error occurred during PDF preprocessing.")
