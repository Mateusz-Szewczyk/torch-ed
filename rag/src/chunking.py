import logging
import re
from typing import List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# Common abbreviations that shouldn't be treated as sentence endings
ABBREVIATIONS = {
    # Polish
    'dr', 'mgr', 'inż', 'prof', 'doc', 'hab', 'np', 'tzn', 'tj', 'itd', 'itp',
    'etc', 'al', 'ul', 'pl', 'os', 'nr', 'tel', 'fax', 'godz', 'min', 'sek',
    'tys', 'mln', 'mld', 'zł', 'gr', 'kg', 'mg', 'ml', 'cm', 'mm', 'km',
    'ok', 'ca', 'por', 'zob', 'przyp', 'red', 'wyd', 'rozdz', 'tab', 'rys',
    'fig', 'str', 'ss', 'vol', 'art', 'ust', 'pkt', 'lit', 'par', 'dz',
    # English
    'dr', 'mr', 'mrs', 'ms', 'prof', 'sr', 'jr', 'vs', 'etc', 'al', 'eg',
    'ie', 'cf', 'inc', 'ltd', 'co', 'corp', 'no', 'vol', 'pp', 'fig',
    'st', 'ave', 'blvd', 'rd', 'dept', 'est', 'approx', 'min', 'max',
}

# Patterns that indicate structural breaks in documents
STRUCTURAL_PATTERNS = [
    r'^#{1,6}\s+.+$',                    # Markdown headers
    r'^\d+\.\s+[A-ZĄĆĘŁŃÓŚŹŻ]',          # Numbered sections (1. Introduction)
    r'^[A-Z][A-ZĄĆĘŁŃÓŚŹŻ]+:$',          # ALL CAPS headers with colon
    r'^(?:CHAPTER|SECTION|PART|ROZDZIAŁ|SEKCJA|CZĘŚĆ)\s+\d+',  # Chapter/Section headers
    r'^(?:Abstract|Streszczenie|Summary|Podsumowanie|Introduction|Wstęp|Conclusion|Wnioski):?\s*$',
    r'^\*{3,}$|^-{3,}$|^_{3,}$',         # Horizontal rules
    r'^(?:Table|Tabela|Figure|Rysunek|Fig\.?)\s+\d+',  # Table/Figure captions
]


# ============================================================================
# TABLE DETECTION AND FORMATTING
# ============================================================================

def detect_table_in_text(text: str) -> Optional[Tuple[int, int, str]]:
    """
    Detect if text contains a table and return its boundaries.

    Returns:
        Tuple of (start_pos, end_pos, formatted_table) or None if no table found
    """
    lines = text.split('\n')

    # Look for table-like patterns
    table_start = None
    table_end = None
    consecutive_table_lines = 0

    for i, line in enumerate(lines):
        if _is_table_like_line(line):
            if table_start is None:
                table_start = i
            consecutive_table_lines += 1
            table_end = i
        else:
            if consecutive_table_lines >= 2:
                # Found a valid table region
                break
            table_start = None
            consecutive_table_lines = 0

    if table_start is not None and table_end is not None and table_end - table_start >= 1:
        table_lines = lines[table_start:table_end + 1]
        formatted = _format_table_lines(table_lines)
        if formatted:
            # Calculate character positions
            start_pos = sum(len(lines[j]) + 1 for j in range(table_start))
            end_pos = sum(len(lines[j]) + 1 for j in range(table_end + 1))
            return (start_pos, end_pos, formatted)

    return None


def _is_table_like_line(line: str) -> bool:
    """Check if a line appears to be part of a table."""
    line = line.strip()
    if not line or len(line) < 5:
        return False

    # Pipe-separated (Markdown table)
    if '|' in line and line.count('|') >= 2:
        return True

    # Tab-separated
    if '\t' in line and line.count('\t') >= 1:
        return True

    # Multiple columns separated by 2+ spaces
    parts = re.split(r'\s{2,}', line)
    if len(parts) >= 2:  # Changed from 3 to 2 for better detection
        # Check for numeric data or short values typical of tables
        numeric_count = sum(1 for p in parts if re.match(r'^[\d.,\-+%()]+$', p.strip()))
        if numeric_count >= 1:
            return True

        # Check if parts look like table cells (short, uniform-ish lengths)
        lengths = [len(p.strip()) for p in parts if p.strip()]
        if lengths and max(lengths) <= 30:
            # If all parts are relatively short, likely a table row
            return True

        # Short column headers/values
        short_count = sum(1 for p in parts if 0 < len(p.strip()) <= 20)
        if short_count >= len(parts) * 0.5:
            return True

    return False


def _format_table_lines(lines: List[str]) -> Optional[str]:
    """
    Convert detected table lines to pipe-separated markdown format.

    Args:
        lines: List of table lines

    Returns:
        Formatted markdown table string or None if formatting fails
    """
    if not lines or len(lines) < 2:
        return None

    # Parse all rows
    all_rows = []
    separator_type = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Detect separator type
        if separator_type is None:
            if '|' in line:
                separator_type = 'pipe'
            elif '\t' in line:
                separator_type = 'tab'
            else:
                separator_type = 'space'

        # Parse cells based on separator
        if separator_type == 'pipe':
            cells = [c.strip() for c in line.split('|') if c.strip()]
        elif separator_type == 'tab':
            cells = [c.strip() for c in line.split('\t')]
        else:
            cells = [c.strip() for c in re.split(r'\s{2,}', line)]

        # Skip separator rows (like "---" or "===")
        if all(re.match(r'^[-=|:]+$', c) or not c for c in cells):
            continue

        if cells and len(cells) >= 2:
            all_rows.append(cells)

    if len(all_rows) < 2:
        return None

    # Normalize column count
    max_cols = max(len(row) for row in all_rows)
    if max_cols > 15:  # Too many columns, probably not a table
        return None

    normalized_rows = []
    for row in all_rows:
        while len(row) < max_cols:
            row.append('')
        normalized_rows.append(row[:max_cols])

    # Build markdown table
    headers = normalized_rows[0]
    data_rows = normalized_rows[1:]

    # Calculate column widths
    col_widths = []
    for i in range(max_cols):
        col_values = [headers[i]] + [row[i] for row in data_rows]
        col_widths.append(max(len(str(v)) for v in col_values))

    # Format header
    header_row = "| " + " | ".join(
        str(h).ljust(w) for h, w in zip(headers, col_widths)
    ) + " |"

    # Format separator
    separator_row = "|" + "|".join(
        "-" * (w + 2) for w in col_widths
    ) + "|"

    # Format data rows
    formatted_rows = [
        "| " + " | ".join(
            str(cell).ljust(w) for cell, w in zip(row, col_widths)
        ) + " |"
        for row in data_rows
    ]

    return "\n".join([header_row, separator_row] + formatted_rows)


def preserve_tables_in_text(text: str) -> str:
    """
    Scan text for tables and ensure they are properly marked for preservation.
    Handles both:
    1. Already-formatted markdown tables (from PDF extraction)
    2. Raw tabular data that needs formatting
    """
    # First, find and protect already-formatted markdown tables
    # Pattern: header row | separator row (---) | data rows
    markdown_table_pattern = re.compile(
        r'(\|[^\n]+\|\n\|[-:| ]+\|\n(?:\|[^\n]+\|\n?)+)',
        re.MULTILINE
    )

    protected_markdown_tables = []

    def protect_markdown_table(match):
        idx = len(protected_markdown_tables)
        table_text = match.group(0).strip()
        # Wrap with markers if not already wrapped
        if '<!-- TABLE_START -->' not in table_text:
            table_text = f"<!-- TABLE_START -->\n{table_text}\n<!-- TABLE_END -->"
        protected_markdown_tables.append(table_text)
        return f'<MARKDOWN_TABLE_{idx}>'

    text = markdown_table_pattern.sub(protect_markdown_table, text)

    if protected_markdown_tables:
        logger.debug(f"[preserve_tables] Found {len(protected_markdown_tables)} pre-formatted markdown table(s)")

    # Now process remaining text for raw tables
    lines = text.split('\n')
    result_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check for markdown table placeholder - pass through
        if '<MARKDOWN_TABLE_' in line:
            result_lines.append(line)
            i += 1
            continue

        # Check if this line starts a table
        if _is_table_like_line(line):
            # Collect all consecutive table-like lines
            table_lines = []
            while i < len(lines) and (_is_table_like_line(lines[i]) or not lines[i].strip()):
                if lines[i].strip():  # Skip empty lines but don't break
                    table_lines.append(lines[i])
                i += 1

            if len(table_lines) >= 2:
                # Format the table
                formatted = _format_table_lines(table_lines)
                if formatted:
                    # Add table marker for chunking to recognize
                    result_lines.append("")  # Empty line before table
                    result_lines.append("<!-- TABLE_START -->")
                    result_lines.append(formatted)
                    result_lines.append("<!-- TABLE_END -->")
                    result_lines.append("")  # Empty line after table
                    logger.debug(f"[preserve_tables] Formatted raw table with {len(table_lines)} lines")
                else:
                    # Couldn't format, keep original
                    result_lines.extend(table_lines)
            else:
                # Not enough lines for a table
                result_lines.extend(table_lines)
        else:
            result_lines.append(line)
            i += 1

    text = '\n'.join(result_lines)

    # Restore protected markdown tables
    for idx, table_content in enumerate(protected_markdown_tables):
        text = text.replace(f'<MARKDOWN_TABLE_{idx}>', table_content)

    return text


@dataclass
class ChunkMetadata:
    """Metadata for a text chunk."""
    start_char: int
    end_char: int
    has_header: bool = False
    section_name: Optional[str] = None
    is_table: bool = False


def create_chunks(text: str, chunk_size: int = 1200, overlap: int = 150) -> List[str]:
    """
    Splits the input text into semantically coherent overlapping chunks.

    Uses an intelligent multi-pass approach:
    1. Identifies structural elements (headers, sections)
    2. Preserves tables as atomic units
    3. Splits text into sentences while respecting abbreviations
    3. Groups sentences into semantic chunks respecting paragraph boundaries
    4. Applies smart overlap that preserves sentence integrity

    Args:
        text (str): The input text to split into chunks.
        chunk_size (int): Target size of each chunk in characters (default: 1200 chars ≈ 300-350 tokens).
        overlap (int): Target overlap between chunks in characters (default: 150).

    Returns:
        List[str]: A list of text chunks.

    Raises:
        ValueError: If chunk_size is not greater than overlap.
        TypeError: If text is not a string.
    """
    if not isinstance(text, str):
        logger.error("Input text must be a string.")
        raise TypeError("Input text must be a string.")

    if chunk_size <= overlap:
        logger.error("Chunk size must be greater than overlap.")
        raise ValueError("Chunk size must be greater than overlap")

    # Check for tables in input
    has_markdown_table = bool(re.search(r'\|[^\n]+\|\n\|[-:| ]+\|', text))
    if has_markdown_table:
        logger.info("[chunking] Input contains markdown table(s)")

    # Clean and normalize text
    text = _normalize_text(text)

    # Check if tables survived normalization
    has_table_after_norm = '<!-- TABLE_START -->' in text or bool(re.search(r'\|[^\n]+\|\n\|[-:| ]+\|', text))
    if has_markdown_table and has_table_after_norm:
        logger.info("[chunking] Tables preserved after normalization")
    elif has_markdown_table and not has_table_after_norm:
        logger.warning("[chunking] Tables may have been lost during normalization!")

    if not text.strip():
        return []

    # Use intelligent semantic chunking
    try:
        chunks = _intelligent_semantic_chunking(text, chunk_size, overlap)

        if not chunks:
            logger.warning("Intelligent chunking produced no chunks, falling back to sentence-based.")
            chunks = _sentence_based_chunking(text, chunk_size, overlap)

        # Final cleanup and validation
        chunks = _cleanup_chunks(chunks, min_size=100)

        # Check how many chunks contain tables
        table_chunks = sum(1 for c in chunks if '|' in c and re.search(r'\|[-:]+\|', c))
        if table_chunks > 0:
            logger.info(f"[chunking] {table_chunks} chunk(s) contain table data")

        logger.info(f"Created {len(chunks)} chunks")
        if chunks:
            avg_size = sum(len(c) for c in chunks) / len(chunks)
            logger.info(f"Average chunk size: {avg_size:.0f} characters")

        return chunks

    except Exception as e:
        logger.warning(f"Chunking failed with error: {e}. Using fallback.")
        return _fallback_chunking(text, chunk_size, overlap)


def _detect_and_protect_algorithms(text: str) -> Tuple[str, List[str]]:
    """
    Detect and protect algorithm/pseudocode blocks from being scrambled.

    Detects patterns like:
    - "Algorithm 1 ..." blocks
    - Pseudocode with line numbers (1:, 2:, etc.)
    - Code blocks with keywords (Require:, Input:, Output:, if, for, while, return)

    Returns:
        Tuple of (text with placeholders, list of protected algorithm blocks)
    """
    protected_algorithms = []

    # First, pre-process to fix common PDF extraction issues in algorithm text
    text = _preprocess_algorithm_text(text)

    # Pattern 1: Algorithm blocks (Algorithm 1, Algorithm 2, etc.)
    # Match from "Algorithm X" until we hit a section break or new section
    # This pattern looks for "Algorithm N" followed by content until a major section break
    algorithm_pattern = re.compile(
        r'(Algorithm\s+\d+[^\n]*(?:\n(?!(?:\d+\.\s+[A-Z]|^(?:Abstract|Introduction|Conclusion|References|Section|Table|Figure)\s))[^\n]*)*)',
        re.MULTILINE | re.IGNORECASE
    )

    def protect_algorithm(match):
        idx = len(protected_algorithms)
        block = match.group(0).strip()
        # Format the algorithm block properly
        formatted = _format_algorithm_block(block)
        protected_algorithms.append(formatted)
        return f'\n\n<ALGORITHM_PLACEHOLDER_{idx}>\n\n'

    text = algorithm_pattern.sub(protect_algorithm, text)

    # Pattern 2: Numbered pseudocode lines (1:, 2:, etc.) - common in academic papers
    # Look for sequences of lines starting with numbers
    lines = text.split('\n')
    result_lines = []
    current_algo_block = []
    in_algo = False

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Check if this looks like an algorithm line
        is_algo_line = (
            # Numbered lines: "1:", "2:", etc.
            re.match(r'^\d+:\s*', stripped) or
            # Require/Input/Output keywords
            re.match(r'^(Require|Input|Output|Ensure)\s*:', stripped, re.IGNORECASE) or
            # Control flow keywords with structure
            (in_algo and re.match(r'^(if|else|for|while|return|end\s*(if|for|while))\b', stripped, re.IGNORECASE))
        )

        if is_algo_line:
            if not in_algo:
                in_algo = True
            current_algo_block.append(line)
        else:
            if in_algo and current_algo_block:
                # Check if we have enough lines to be an algorithm block
                if len(current_algo_block) >= 3:
                    idx = len(protected_algorithms)
                    formatted = _format_algorithm_block('\n'.join(current_algo_block))
                    protected_algorithms.append(formatted)
                    result_lines.append(f'\n\n<ALGORITHM_PLACEHOLDER_{idx}>\n\n')
                else:
                    # Too short, keep original lines
                    result_lines.extend(current_algo_block)
                current_algo_block = []
                in_algo = False
            result_lines.append(line)

    # Don't forget any remaining algorithm block
    if current_algo_block and len(current_algo_block) >= 3:
        idx = len(protected_algorithms)
        formatted = _format_algorithm_block('\n'.join(current_algo_block))
        protected_algorithms.append(formatted)
        result_lines.append(f'\n\n<ALGORITHM_PLACEHOLDER_{idx}>\n\n')
    elif current_algo_block:
        result_lines.extend(current_algo_block)

    text = '\n'.join(result_lines)

    if protected_algorithms:
        logger.info(f"[normalize] Protected {len(protected_algorithms)} algorithm/pseudocode block(s)")

    return text, protected_algorithms


def _preprocess_algorithm_text(text: str) -> str:
    """
    Pre-process text to fix common PDF extraction issues in algorithm/pseudocode.

    Handles:
    - Corrupted Unicode arrows and symbols
    - Broken subscripts/superscripts
    - Line fragments that should be joined
    """
    # Fix common corrupted Unicode symbols from PDF extraction
    symbol_replacements = [
        # Arrows
        (r'←|<-|<−|⇐', ' ← '),
        (r'→|->|−>|⇒', ' → '),
        # Mathematical operators
        (r'⊕|\+\+', ' ⊕ '),
        (r'∈|\\in\b', ' ∈ '),
        (r'∀|\\forall\b', ' ∀ '),
        (r'∃|\\exists\b', ' ∃ '),
        (r'≤|<=|⩽', ' ≤ '),
        (r'≥|>=|⩾', ' ≥ '),
        (r'≠|!=|<>', ' ≠ '),
        # Subscript patterns often broken by PDF - normalize them
        (r'(\w)_(\{[^}]+\}|\w)', r'\1_\2'),  # Preserve subscripts
        (r'(\w)\^(\{[^}]+\}|\w)', r'\1^\2'),  # Preserve superscripts
    ]

    for pattern, replacement in symbol_replacements:
        text = re.sub(pattern, replacement, text)

    # Fix common pattern: "erate" should be "generate" (corrupted by special chars)
    text = re.sub(r'\berate\b', 'generate', text, flags=re.IGNORECASE)

    # Fix "internternal" -> "internal" (common OCR/extraction error)
    text = re.sub(r'\binternternal\b', 'internal', text, flags=re.IGNORECASE)

    # Normalize spacing around mathematical notation
    text = re.sub(r'\s*([←→⊕∈∀∃≤≥≠])\s*', r' \1 ', text)

    # Clean up multiple spaces
    text = re.sub(r' {2,}', ' ', text)

    # IMPORTANT: Reconstruct line breaks for algorithms that were extracted as single lines
    text = _reconstruct_algorithm_lines(text)

    return text


def _reconstruct_algorithm_lines(text: str) -> str:
    """
    Reconstruct proper line breaks in algorithm text that was extracted as a single line.

    This handles the common case where PDF extraction produces:
    "Algorithm 1 ... 1: step one 2: step two 3: step three"

    And converts it to proper multi-line format.
    """
    # Check if this text contains an algorithm pattern
    if not re.search(r'\bAlgorithm\s+\d+\b', text, re.IGNORECASE):
        return text

    # Check if it's already multi-line with proper structure
    lines = text.split('\n')
    numbered_line_count = sum(1 for line in lines if re.match(r'^\s*\d+:\s*', line.strip()))
    if numbered_line_count >= 3:
        # Already has good line structure
        return text

    # Need to reconstruct line breaks
    result_parts = []

    # Find the algorithm header and extract it
    algorithm_match = re.match(r'^(Algorithm\s+\d+[^0-9]*?)(?=\d+:|Require:|Input:|Output:|$)', text, re.IGNORECASE)
    if algorithm_match:
        header = algorithm_match.group(1).strip()
        result_parts.append(header)
        text = text[len(algorithm_match.group(0)):].strip()

    # Insert line breaks before Require:, Input:, Output:, Ensure:
    for keyword in ['Require:', 'Input:', 'Output:', 'Ensure:']:
        text = re.sub(rf'(?<!\n)\s*({keyword})', r'\n\1', text, flags=re.IGNORECASE)

    # Insert line breaks before numbered steps (N:)
    # Pattern: digit followed by colon, not part of a ratio or time
    # Look for patterns like " 1:" or " 12:" that indicate algorithm steps
    text = re.sub(r'(?<=\s)(\d{1,2}:)\s*(?=[A-Za-z])', r'\n\1 ', text)

    # Also handle cases like "⊲Section..." which should start new line (comments)
    text = re.sub(r'\s*(⊲[^\n]*?)(?=\s*\d+:|$)', r'  \1\n', text)

    # Handle control flow keywords that should be on their own lines
    # Insert line break before "if", "else", "for", "while", "end if", "end for", "end while", "return"
    for keyword in ['if ', 'else', 'for ', 'while ', 'end if', 'end for', 'end while', 'return ']:
        # Only insert break if not already at start of line
        text = re.sub(rf'(?<=[^\n\d])(\s*)({keyword})', r'\n\2', text, flags=re.IGNORECASE)

    result_parts.append(text.strip())

    result = '\n'.join(result_parts)

    # Clean up any double newlines or leading/trailing whitespace on lines
    result = re.sub(r'\n{3,}', '\n\n', result)
    result = '\n'.join(line.rstrip() for line in result.split('\n'))

    logger.debug(f"[algorithm] Reconstructed line breaks in algorithm text")
    return result


def _format_algorithm_block(block: str) -> str:
    """
    Format an algorithm/pseudocode block for clean display.

    Preserves:
    - Line structure
    - Mathematical symbols
    - Indentation hierarchy
    - Line numbers
    """
    lines = block.split('\n')
    formatted_lines = []

    # Check if this is a titled algorithm (starts with "Algorithm X")
    has_title = bool(re.match(r'^Algorithm\s+\d+', lines[0].strip(), re.IGNORECASE))

    # Track indentation level for proper formatting
    indent_level = 0
    base_indent = "  "

    for i, line in enumerate(lines):
        line = line.rstrip()
        if not line:
            continue

        # Clean up common PDF extraction issues in algorithm text
        # Fix common symbol corruptions
        line = line.replace('←', ' ← ')  # Assignment arrow
        line = line.replace('→', ' → ')  # Right arrow
        line = line.replace('⊕', ' ⊕ ')  # XOR/concatenation
        line = line.replace('∈', ' ∈ ')  # Element of
        line = line.replace('∀', ' ∀ ')  # For all
        line = line.replace('∃', ' ∃ ')  # Exists
        line = line.replace('≤', ' ≤ ')  # Less than or equal
        line = line.replace('≥', ' ≥ ')  # Greater than or equal
        line = line.replace('≠', ' ≠ ')  # Not equal

        # Fix common PDF extraction errors
        line = re.sub(r'\berate\b', 'generate', line)
        line = re.sub(r'\binternternal\b', 'internal', line)
        line = re.sub(r'\b([Cc])ombine\s+internternal', r'\1ombine internal', line)

        # Fix broken words (common pattern: "Adap tively" -> "Adaptively")
        line = re.sub(r'(\w)\s+([a-z]{2,})\b', lambda m: m.group(1) + m.group(2) if len(m.group(1)) <= 2 else m.group(0), line)

        # Normalize multiple spaces (but preserve leading indentation)
        leading_spaces = len(line) - len(line.lstrip())
        line_content = re.sub(r'\s{2,}', ' ', line.strip())

        # Detect indentation changes based on keywords
        stripped = line_content.lower()

        # Decrease indent for end/else
        if re.match(r'^(end\s*(if|for|while)|else)\b', stripped, re.IGNORECASE):
            indent_level = max(0, indent_level - 1)

        # Format line number if present
        match = re.match(r'^(\d+):\s*(.*)$', line_content)
        if match:
            num, content = match.groups()
            # Format as "  N: content" with consistent spacing
            formatted_line = f"{base_indent * indent_level}{num}: {content}"
        elif i == 0 and has_title:
            # Title line - no extra indent
            formatted_line = line_content
        elif re.match(r'^(Require|Input|Output|Ensure)\s*:', line_content, re.IGNORECASE):
            # Require/Input/Output - no indent
            formatted_line = line_content
        else:
            formatted_line = base_indent * indent_level + line_content

        formatted_lines.append(formatted_line)

        # Increase indent for if/for/while (after adding the line)
        if re.match(r'^(\d+:\s*)?(if|for|while)\b', stripped, re.IGNORECASE) and not 'end' in stripped:
            indent_level += 1

    # Wrap in a code block for clear formatting
    result = "```algorithm\n" + '\n'.join(formatted_lines) + "\n```"

    return result


def _normalize_text(text: str) -> str:
    """
    Normalize text by cleaning up whitespace, special characters and fixing line breaks.

    This function intelligently handles:
    - Removal of null characters
    - Normalization of line endings
    - Detecting and formatting tables
    - Protecting algorithm/pseudocode blocks
    - Joining lines that were broken in the middle of sentences
    - Preserving paragraph structure
    - Removing page markers
    """
    # Remove null characters
    text = text.replace('\x00', '')

    # Normalize different types of line endings
    text = re.sub(r'\r\n', '\n', text)
    text = re.sub(r'\r', '\n', text)

    # Remove page markers that might interfere
    text = re.sub(r'^Page \d+:\s*\n?', '', text, flags=re.MULTILINE | re.IGNORECASE)

    # IMPORTANT: Detect and protect algorithm blocks BEFORE other normalization
    text, protected_algorithms = _detect_and_protect_algorithms(text)

    # IMPORTANT: Detect and format tables BEFORE other normalization
    # This preserves table structure that would otherwise be lost
    text = preserve_tables_in_text(text)

    # Mark paragraph breaks (2+ newlines) with a special marker
    # But protect tables from this
    protected_tables = []
    table_pattern = re.compile(r'<!-- TABLE_START -->\n(.*?)\n<!-- TABLE_END -->', re.DOTALL)

    def protect_table(match):
        idx = len(protected_tables)
        protected_tables.append(match.group(0))
        return f'<TABLE_PLACEHOLDER_{idx}>'

    text = table_pattern.sub(protect_table, text)

    text = re.sub(r'\n{2,}', '\n\n<PARA>\n\n', text)

    # Process single newlines - join lines that are broken mid-sentence
    lines = text.split('\n')
    result_parts = []

    for i, line in enumerate(lines):
        line = line.strip()

        if not line:
            continue

        # Handle paragraph marker
        if '<PARA>' in line:
            result_parts.append('\n\n')
            continue

        # Handle table placeholder - keep as is
        if '<TABLE_PLACEHOLDER_' in line:
            result_parts.append('\n\n')
            result_parts.append(line)
            result_parts.append('\n\n')
            continue

        # Handle algorithm placeholder - keep as is
        if '<ALGORITHM_PLACEHOLDER_' in line:
            result_parts.append('\n\n')
            result_parts.append(line)
            result_parts.append('\n\n')
            continue

        # Check if we need to join with previous content
        if result_parts:
            last_part = result_parts[-1].rstrip()

            # Determine if this line should start a new block or continue previous
            starts_new_block = False

            # Check for structural elements (headers, list items, etc.)
            if _is_structural_element(line):
                starts_new_block = True
            # Check if line starts with a number followed by period (list item)
            elif re.match(r'^\d+\.\s', line):
                starts_new_block = True
            # Check if line is a bullet point
            elif line.startswith(('- ', '• ', '* ', '– ')):
                starts_new_block = True
            # Check if previous line ends with sentence-ending punctuation
            elif last_part and last_part[-1] in '.!?:':
                # If current line starts with lowercase, it's likely a continuation
                if line and line[0].islower():
                    starts_new_block = False
                else:
                    starts_new_block = True
            # If current line looks like a short header (short, starts with capital)
            elif len(line) < 60 and line[0].isupper() and (not last_part or last_part[-1] not in '.,;'):
                starts_new_block = True

            if starts_new_block:
                result_parts.append('\n\n')
            elif last_part and not last_part.endswith(' '):
                # Join with space for mid-sentence line breaks
                result_parts.append(' ')

        result_parts.append(line)

    text = ''.join(result_parts)

    # Clean up multiple spaces
    text = re.sub(r' {2,}', ' ', text)

    # Remove spaces before punctuation
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)

    # Remove excessive blank lines (more than 2 consecutive)
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Restore protected tables
    for idx, table_content in enumerate(protected_tables):
        text = text.replace(f'<TABLE_PLACEHOLDER_{idx}>', table_content)

    # Restore protected algorithms
    for idx, algo_content in enumerate(protected_algorithms):
        text = text.replace(f'<ALGORITHM_PLACEHOLDER_{idx}>', algo_content)

    return text.strip()


def _intelligent_semantic_chunking(text: str, chunk_size: int, overlap: int) -> List[str]:
    """
    Intelligent chunking that respects document structure.

    Strategy:
    1. Split into paragraphs
    2. Identify structural elements (headers, lists)
    3. Preserve tables as atomic units
    4. Group paragraphs into chunks, keeping related content together
    5. Apply sentence-aware overlap
    """
    # Split into paragraphs (double newline or significant indentation)
    paragraphs = _split_into_paragraphs(text)

    if not paragraphs:
        return []

    chunks = []
    current_chunk_parts = []
    current_size = 0

    for i, para in enumerate(paragraphs):
        para = para.strip()
        if not para:
            continue

        # Check if this paragraph is a table (marked with TABLE_START/TABLE_END)
        is_table = '<!-- TABLE_START -->' in para or para.startswith('|')

        # Check if this paragraph is an algorithm block
        is_algorithm = '```algorithm' in para or para.startswith('```algorithm')

        # Tables and algorithms are atomic - don't split them
        if is_table:
            # Save current chunk first
            if current_chunk_parts:
                chunks.append('\n\n'.join(current_chunk_parts))
                current_chunk_parts = []
                current_size = 0

            # Clean up table markers for final output
            table_content = para.replace('<!-- TABLE_START -->', '').replace('<!-- TABLE_END -->', '').strip()

            # Add table as its own chunk (tables are atomic)
            chunks.append(table_content)
            continue

        if is_algorithm:
            # Save current chunk first
            if current_chunk_parts:
                chunks.append('\n\n'.join(current_chunk_parts))
                current_chunk_parts = []
                current_size = 0

            # Add algorithm as its own chunk (algorithms are atomic)
            chunks.append(para)
            continue

        para_size = len(para)
        is_header = _is_structural_element(para)

        # If paragraph itself is too large, split it into sentences
        if para_size > chunk_size:
            # Save current chunk first
            if current_chunk_parts:
                chunks.append('\n\n'.join(current_chunk_parts))
                current_chunk_parts = []
                current_size = 0

            # Split large paragraph
            sub_chunks = _split_large_paragraph(para, chunk_size, overlap)
            chunks.extend(sub_chunks)
            continue

        # Check if adding this paragraph would exceed chunk_size
        potential_size = current_size + para_size + (2 if current_chunk_parts else 0)  # +2 for \n\n

        if potential_size > chunk_size and current_chunk_parts:
            # Save current chunk
            chunks.append('\n\n'.join(current_chunk_parts))

            # Calculate overlap - take last sentences from current chunk
            overlap_text = _get_sentence_overlap(current_chunk_parts[-1], overlap)

            if overlap_text and len(overlap_text) > 50:
                current_chunk_parts = [overlap_text]
                current_size = len(overlap_text)
            else:
                current_chunk_parts = []
                current_size = 0

        # Headers start new chunks (but only if we have content)
        if is_header and current_chunk_parts and current_size > chunk_size * 0.3:
            chunks.append('\n\n'.join(current_chunk_parts))
            current_chunk_parts = []
            current_size = 0

        current_chunk_parts.append(para)
        current_size += para_size + (2 if len(current_chunk_parts) > 1 else 0)

    # Don't forget the last chunk
    if current_chunk_parts:
        chunks.append('\n\n'.join(current_chunk_parts))

    return chunks


def _split_into_paragraphs(text: str) -> List[str]:
    """Split text into paragraphs based on multiple newlines or indentation."""
    # Split on double (or more) newlines
    paragraphs = re.split(r'\n\s*\n', text)

    result = []
    for para in paragraphs:
        para = para.strip()
        if para:
            result.append(para)

    return result


def _is_structural_element(text: str) -> bool:
    """Check if text is a structural element like header."""
    first_line = text.split('\n')[0].strip()

    for pattern in STRUCTURAL_PATTERNS:
        if re.match(pattern, first_line, re.IGNORECASE):
            return True

    # Short lines that are likely headers (< 100 chars, no period at end)
    if len(first_line) < 100 and not first_line.endswith('.'):
        # Check if it looks like a title (capitalized words)
        words = first_line.split()
        if words and all(w[0].isupper() for w in words if w and w[0].isalpha()):
            return True

    return False


def _split_large_paragraph(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Split a large paragraph into chunks while preserving sentence boundaries."""
    sentences = _split_into_sentences(text)

    if not sentences:
        return _fallback_chunking(text, chunk_size, overlap)

    chunks = []
    current_sentences = []
    current_size = 0

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        sentence_size = len(sentence)

        # If single sentence is too large, split it by clauses
        if sentence_size > chunk_size:
            if current_sentences:
                chunks.append(' '.join(current_sentences))
                current_sentences = []
                current_size = 0

            # Split long sentence by clauses
            clause_chunks = _split_long_sentence(sentence, chunk_size, overlap)
            chunks.extend(clause_chunks)
            continue

        potential_size = current_size + sentence_size + (1 if current_sentences else 0)

        if potential_size > chunk_size and current_sentences:
            chunks.append(' '.join(current_sentences))

            # Smart overlap: include last 1-2 sentences
            overlap_sentences = []
            overlap_size = 0
            for s in reversed(current_sentences):
                if overlap_size + len(s) <= overlap:
                    overlap_sentences.insert(0, s)
                    overlap_size += len(s) + 1
                else:
                    break

            current_sentences = overlap_sentences
            current_size = sum(len(s) for s in current_sentences) + len(current_sentences) - 1 if current_sentences else 0

        current_sentences.append(sentence)
        current_size += sentence_size + (1 if len(current_sentences) > 1 else 0)

    if current_sentences:
        chunks.append(' '.join(current_sentences))

    return chunks


def _split_into_sentences(text: str) -> List[str]:
    """
    Split text into sentences while handling abbreviations properly.

    This is a critical function that ensures sentences aren't broken at abbreviations.
    """
    # First, protect abbreviations by replacing their periods temporarily
    protected_text = text

    # Create a pattern for known abbreviations
    abbrev_pattern = r'\b(' + '|'.join(re.escape(abbr) for abbr in ABBREVIATIONS) + r')\.'

    # Replace abbreviation periods with a placeholder
    placeholder = '\x01'  # Using a control character as placeholder
    protected_text = re.sub(abbrev_pattern, r'\1' + placeholder, protected_text, flags=re.IGNORECASE)

    # Also protect common patterns like "1.", "a)", decimal numbers "3.14"
    protected_text = re.sub(r'(\d+)\.(\d+)', r'\1' + placeholder + r'\2', protected_text)  # Decimal numbers
    protected_text = re.sub(r'^(\d+)\.\s', r'\1' + placeholder + ' ', protected_text, flags=re.MULTILINE)  # List numbers

    # Split on sentence-ending punctuation
    # Pattern: period/exclamation/question followed by space and capital letter (or end of string)
    sentence_pattern = r'(?<=[.!?])\s+(?=[A-ZĄĆĘŁŃÓŚŹŻ"])'
    sentences = re.split(sentence_pattern, protected_text)

    # Restore the periods in abbreviations
    sentences = [s.replace(placeholder, '.') for s in sentences]

    # Clean up sentences
    result = []
    for s in sentences:
        s = s.strip()
        if s:
            result.append(s)

    return result


def _split_long_sentence(sentence: str, chunk_size: int, overlap: int) -> List[str]:
    """Split a very long sentence by clauses (semicolons, colons, conjunctions)."""
    # Split by natural clause boundaries
    clause_separators = [
        r';\s*',                          # Semicolons
        r':\s+(?=[A-Z])',                 # Colons followed by capital
        r',\s*(?:and|or|but|oraz|i|lub|ale|jednak)\s+',  # Conjunctions
        r'\s*-\s*',                        # Dashes
    ]

    chunks = [sentence]

    for sep in clause_separators:
        new_chunks = []
        for chunk in chunks:
            if len(chunk) > chunk_size:
                parts = re.split(sep, chunk)
                new_chunks.extend(parts)
            else:
                new_chunks.append(chunk)
        chunks = new_chunks

    # If still too large, fall back to word-based splitting
    final_chunks = []
    for chunk in chunks:
        if len(chunk) > chunk_size:
            # Word-based splitting as last resort
            words = chunk.split()
            current = []
            current_size = 0
            for word in words:
                if current_size + len(word) + 1 > chunk_size and current:
                    final_chunks.append(' '.join(current))
                    current = []
                    current_size = 0
                current.append(word)
                current_size += len(word) + 1
            if current:
                final_chunks.append(' '.join(current))
        else:
            final_chunks.append(chunk)

    return [c.strip() for c in final_chunks if c.strip()]


def _get_sentence_overlap(text: str, target_overlap: int) -> str:
    """Get the last complete sentence(s) for overlap, up to target_overlap characters."""
    sentences = _split_into_sentences(text)

    if not sentences:
        # Fallback: just take the last N characters
        return text[-target_overlap:] if len(text) > target_overlap else text

    overlap_sentences = []
    overlap_size = 0

    for sentence in reversed(sentences):
        if overlap_size + len(sentence) + 1 <= target_overlap:
            overlap_sentences.insert(0, sentence)
            overlap_size += len(sentence) + 1
        else:
            break

    return ' '.join(overlap_sentences)


def _cleanup_chunks(chunks: List[str], min_size: int = 100) -> List[str]:
    """Clean up chunks - remove too small ones, merge orphans."""
    if not chunks:
        return []

    cleaned = []
    pending_small = ""

    for chunk in chunks:
        chunk = chunk.strip()

        if not chunk:
            continue

        # If chunk is too small, try to merge with next
        if len(chunk) < min_size:
            pending_small = (pending_small + "\n\n" + chunk).strip() if pending_small else chunk
            continue

        # If we have pending small content, prepend it
        if pending_small:
            chunk = pending_small + "\n\n" + chunk
            pending_small = ""

        cleaned.append(chunk)

    # Handle any remaining small content
    if pending_small:
        if cleaned:
            cleaned[-1] = cleaned[-1] + "\n\n" + pending_small
        else:
            cleaned.append(pending_small)

    return cleaned


def _fallback_chunking(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Fallback character-based chunking with smart boundary detection."""
    if not text.strip():
        return []

    chunks = []
    start = 0
    text_len = len(text)
    step = chunk_size - overlap

    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk = text[start:end]

        # Try to end at a sentence boundary
        if end < text_len:
            # Look for sentence endings near the end (within last 20%)
            search_start = int(len(chunk) * 0.8)
            best_break = -1

            for i in range(len(chunk) - 1, search_start, -1):
                if chunk[i] in '.!?' and (i + 1 >= len(chunk) or chunk[i + 1] in ' \n'):
                    best_break = i + 1
                    break

            if best_break > 0:
                chunk = chunk[:best_break]

        chunk = chunk.strip()
        if chunk:
            chunks.append(chunk)

        # Move start position
        actual_chunk_len = len(chunk) if chunk else chunk_size
        start += max(actual_chunk_len - overlap, step // 2)

    return chunks


def _sentence_based_chunking(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Pure sentence-based chunking as a middle-ground fallback."""
    sentences = _split_into_sentences(text)

    if not sentences:
        return _fallback_chunking(text, chunk_size, overlap)

    chunks = []
    current = []
    current_size = 0

    for sentence in sentences:
        sentence_size = len(sentence)

        if current_size + sentence_size + 1 > chunk_size and current:
            chunks.append(' '.join(current))

            # Overlap: keep last sentence(s)
            overlap_sentences = []
            overlap_size = 0
            for s in reversed(current):
                if overlap_size + len(s) <= overlap:
                    overlap_sentences.insert(0, s)
                    overlap_size += len(s) + 1
                else:
                    break

            current = overlap_sentences
            current_size = overlap_size

        current.append(sentence)
        current_size += sentence_size + 1

    if current:
        chunks.append(' '.join(current))

    return chunks


# ============================================================================
# SEMANTIC CHUNKING WITH EMBEDDINGS (Optional advanced feature)
# ============================================================================

def semantic_chunking(text: str, chunk_size: int, overlap: int) -> List[str]:
    """
    Performs semantic chunking by first splitting by structural elements,
    then combining or splitting to meet chunk_size requirements.

    This is the main entry point that redirects to intelligent chunking.
    """
    return _intelligent_semantic_chunking(text, chunk_size, overlap)


def character_chunking(text: str, chunk_size: int, overlap: int) -> List[str]:
    """
    Simple character-based chunking with overlap.
    Used as a fallback when semantic chunking fails.
    """
    return _fallback_chunking(text, chunk_size, overlap)


# ============================================================================
# LEGACY FUNCTIONS (kept for backward compatibility)
# ============================================================================

def nltk_chunking(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Legacy NLTK-based sentence chunking. Now redirects to semantic chunking."""
    return _intelligent_semantic_chunking(text, chunk_size, overlap)


def simple_chunking(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Legacy simple chunking. Now redirects to fallback chunking."""
    return _fallback_chunking(text, chunk_size, overlap)


def create_chunks_from_sentences(sentences: List[str], chunk_size: int, overlap: int) -> List[str]:
    """Legacy function - kept for backward compatibility."""
    text = ' '.join(sentences)
    return _intelligent_semantic_chunking(text, chunk_size, overlap)
