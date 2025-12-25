import logging
import re
from typing import List

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def create_chunks(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Splits the input text into semantically coherent overlapping chunks.

    Uses a hierarchical approach:
    1. First splits by structural elements (headers, paragraphs)
    2. Then applies character-based chunking with overlap

    Args:
        text (str): The input text to split into chunks.
        chunk_size (int): Maximum size of each chunk in characters (default: 1000 chars ≈ 250-300 tokens).
        overlap (int): Number of characters that overlap between chunks (default: 200).

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

    # Użyj nowej strategii: recursive semantic chunking
    try:
        return semantic_chunking(text, chunk_size, overlap)
    except Exception as e:
        logger.warning(f"Semantic chunking failed: {e}. Falling back to simple character chunking.")
        return character_chunking(text, chunk_size, overlap)


def semantic_chunking(text: str, chunk_size: int, overlap: int) -> List[str]:
    """
    Performs semantic chunking by first splitting by structural elements,
    then combining or splitting to meet chunk_size requirements.

    Hierarchical separators (from most to least significant):
    1. Headers (# markdown, numbered sections)
    2. Double newlines (paragraphs)
    3. Single newlines
    4. Sentences
    5. Character-based fallback
    """
    # Separators ordered by semantic significance
    separators = [
        r'\n#{1,6}\s+',           # Markdown headers
        r'\n\d+\.\s+',            # Numbered sections (1. 2. etc.)
        r'\n\n+',                 # Double newlines (paragraphs)
        r'\n',                    # Single newlines
        r'(?<=[.!?])\s+',         # Sentence boundaries
        r'\s+',                   # Word boundaries (last resort)
    ]

    chunks = _recursive_split(text, separators, chunk_size, overlap)

    if not chunks:
        logger.warning("Semantic chunking produced no chunks, falling back to character chunking.")
        return character_chunking(text, chunk_size, overlap)

    # Clean up chunks
    cleaned_chunks = []
    for chunk in chunks:
        chunk = chunk.strip()
        if chunk and len(chunk) > 50:  # Skip very small fragments
            cleaned_chunks.append(chunk)

    logger.info(f"Semantic chunking created {len(cleaned_chunks)} chunks")
    if cleaned_chunks:
        avg_size = sum(len(c) for c in cleaned_chunks) / len(cleaned_chunks)
        logger.info(f"Average chunk size: {avg_size:.0f} characters")

    return cleaned_chunks if cleaned_chunks else character_chunking(text, chunk_size, overlap)


def _recursive_split(text: str, separators: List[str], chunk_size: int, overlap: int) -> List[str]:
    """
    Recursively splits text using a hierarchy of separators.
    """
    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    if not separators:
        # No more separators - use character-based splitting
        return character_chunking(text, chunk_size, overlap)

    # Try splitting with current separator
    current_sep = separators[0]
    remaining_seps = separators[1:]

    # Split text
    parts = re.split(current_sep, text)

    # If split didn't help, try next separator
    if len(parts) <= 1:
        return _recursive_split(text, remaining_seps, chunk_size, overlap)

    # Merge small parts and split large ones
    chunks = []
    current_chunk = ""

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # If adding this part exceeds chunk_size
        if len(current_chunk) + len(part) + 1 > chunk_size:
            if current_chunk:
                chunks.append(current_chunk)
                # Add overlap from previous chunk
                if overlap > 0 and len(current_chunk) > overlap:
                    current_chunk = current_chunk[-overlap:]
                else:
                    current_chunk = ""

            # If the part itself is too large, recursively split it
            if len(part) > chunk_size:
                sub_chunks = _recursive_split(part, remaining_seps, chunk_size, overlap)
                if sub_chunks:
                    # Add first sub-chunk to current
                    if current_chunk:
                        current_chunk = current_chunk + " " + sub_chunks[0]
                    else:
                        current_chunk = sub_chunks[0]
                    # Add remaining sub-chunks directly
                    for sc in sub_chunks[1:]:
                        if len(current_chunk) + len(sc) + 1 <= chunk_size:
                            current_chunk = current_chunk + " " + sc if current_chunk else sc
                        else:
                            chunks.append(current_chunk)
                            current_chunk = sc
            else:
                if current_chunk:
                    current_chunk = current_chunk + " " + part
                else:
                    current_chunk = part
        else:
            if current_chunk:
                current_chunk = current_chunk + " " + part
            else:
                current_chunk = part

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def character_chunking(text: str, chunk_size: int, overlap: int) -> List[str]:
    """
    Simple character-based chunking with overlap.
    Used as a fallback when semantic chunking fails.
    """
    if not text.strip():
        return []

    chunks = []
    start = 0
    text_len = len(text)
    step = chunk_size - overlap

    logger.info(f"Character chunking with size={chunk_size}, overlap={overlap}, step={step}")

    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk = text[start:end].strip()

        if chunk:
            # Try to end at a sentence boundary if possible
            if end < text_len:
                # Look for sentence-ending punctuation near the end
                for i in range(min(100, len(chunk))):
                    pos = len(chunk) - 1 - i
                    if pos > 0 and chunk[pos] in '.!?':
                        chunk = chunk[:pos+1]
                        break

            chunks.append(chunk)

        start += step

    logger.info(f"Character chunking created {len(chunks)} chunks")
    if chunks:
        avg_size = sum(len(c) for c in chunks) / len(chunks)
        logger.info(f"Average chunk size: {avg_size:.0f} characters")

    return chunks


# Legacy functions kept for backward compatibility
def nltk_chunking(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Legacy NLTK-based sentence chunking. Now redirects to semantic chunking."""
    return semantic_chunking(text, chunk_size, overlap)


def simple_chunking(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Legacy simple chunking. Now redirects to character chunking."""
    return character_chunking(text, chunk_size, overlap)


def create_chunks_from_sentences(sentences: List[str], chunk_size: int, overlap: int) -> List[str]:
    """Legacy function - kept for backward compatibility."""
    # Convert to text and use new method
    text = ' '.join(sentences)
    return semantic_chunking(text, chunk_size, overlap)

