"""
Simple PDF Table Extractor using pdfplumber.

Uses only pdfplumber's built-in table detection - no complex heuristics.
Focuses on tables with visible lines/borders.
"""

import logging
from typing import List, Optional
from dataclasses import dataclass

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    pdfplumber = None

logger = logging.getLogger(__name__)


@dataclass
class ExtractedTable:
    """Represents an extracted table from a PDF."""
    page_number: int  # 1-based
    table_index: int  # 0-based index on page
    headers: List[str]
    rows: List[List[str]]
    markdown: str
    confidence: float = 0.0


class PDFTableExtractor:
    """
    Simple PDF table extractor using pdfplumber's built-in detection.

    Only extracts tables that pdfplumber can detect with high confidence
    (typically tables with visible borders/lines).
    """

    def __init__(self, min_rows: int = 2, min_columns: int = 2):
        """
        Initialize the table extractor.

        Args:
            min_rows: Minimum rows for valid table
            min_columns: Minimum columns for valid table
        """
        if not PDFPLUMBER_AVAILABLE:
            raise ImportError("pdfplumber is required for table extraction")

        self.min_rows = min_rows
        self.min_columns = min_columns

    def extract_tables_from_pdf(self, pdf_path: str) -> List[ExtractedTable]:
        """
        Extract tables from a PDF file using pdfplumber's built-in detection.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            List of ExtractedTable objects
        """
        all_tables = []

        try:
            logger.info(f"[TABLE] Opening PDF: {pdf_path}")

            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    try:
                        # Use pdfplumber's find_tables() for detection
                        found_tables = page.find_tables()

                        for idx, table in enumerate(found_tables):
                            extracted = table.extract()

                            if not extracted or len(extracted) < self.min_rows:
                                continue

                            # Clean the data
                            cleaned = self._clean_table(extracted)

                            if not cleaned or len(cleaned) < self.min_rows:
                                continue

                            # Check column count
                            col_count = len(cleaned[0]) if cleaned else 0
                            if col_count < self.min_columns:
                                continue

                            # Separate headers and rows
                            headers = cleaned[0]
                            rows = cleaned[1:]

                            # Generate markdown
                            markdown = self._to_markdown(headers, rows)

                            all_tables.append(ExtractedTable(
                                page_number=page_num,
                                table_index=idx,
                                headers=headers,
                                rows=rows,
                                markdown=markdown,
                                confidence=0.9,  # High confidence for line-detected tables
                            ))

                            logger.info(
                                f"[TABLE] Page {page_num}: Found table with "
                                f"{len(headers)} columns, {len(rows)} rows"
                            )

                    except Exception as e:
                        logger.debug(f"Error on page {page_num}: {e}")
                        continue

            logger.info(f"[TABLE] Total tables extracted: {len(all_tables)}")
            return all_tables

        except Exception as e:
            logger.error(f"Error extracting tables from PDF: {e}")
            return []

    def _clean_table(self, table_data: List[List]) -> List[List[str]]:
        """
        Clean table data - convert to strings and handle None values.
        """
        cleaned = []

        for row in table_data:
            if row is None:
                continue

            cleaned_row = []
            for cell in row:
                if cell is None:
                    cleaned_row.append('')
                else:
                    # Convert to string and clean whitespace
                    text = str(cell).strip()
                    text = ' '.join(text.split())  # Normalize whitespace
                    cleaned_row.append(text)

            # Skip completely empty rows
            if any(cell for cell in cleaned_row):
                cleaned.append(cleaned_row)

        return cleaned

    def _to_markdown(self, headers: List[str], rows: List[List[str]]) -> str:
        """
        Convert table to markdown format.
        """
        if not headers:
            return ""

        lines = []
        num_cols = len(headers)

        # Header row
        header_line = "| " + " | ".join(headers) + " |"
        lines.append(header_line)

        # Separator
        separator = "| " + " | ".join(["---"] * num_cols) + " |"
        lines.append(separator)

        # Data rows
        for row in rows:
            # Ensure row has correct number of columns
            padded = (row + [''] * num_cols)[:num_cols]
            row_line = "| " + " | ".join(padded) + " |"
            lines.append(row_line)

        return "\n".join(lines)


def extract_tables_from_pdf(pdf_path: str) -> List[ExtractedTable]:
    """
    Extract tables from a PDF file.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        List of ExtractedTable objects
    """
    if not PDFPLUMBER_AVAILABLE:
        logger.warning("pdfplumber not available, table extraction disabled")
        return []

    extractor = PDFTableExtractor()
    return extractor.extract_tables_from_pdf(pdf_path)

