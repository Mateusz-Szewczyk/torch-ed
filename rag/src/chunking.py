import logging
import re
from typing import List

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def create_chunks(text: str, chunk_size: int = 8, overlap: int = 2) -> List[str]:
    """
    Splits the input text into overlapping chunks of sentences.

    Args:
        text (str): The input text to split into chunks.
        chunk_size (int): The number of sentences in each chunk.
        overlap (int): The number of sentences that overlap between chunks.

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

    try:
        return nltk_chunking(text, chunk_size, overlap)
    except Exception as e:
        logger.warning(f"NLTK chunking failed: {e}. Falling back to simple chunking.")
        return simple_chunking(text, chunk_size, overlap)


def nltk_chunking(text: str, chunk_size: int, overlap: int) -> List[str]:
    try:
        import nltk
        from nltk.tokenize import sent_tokenize
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            logger.warning("NLTK 'punkt' resource not found. Downloading now...")
            nltk.download('punkt', quiet=True)
    except ImportError:
        logger.error("NLTK is not installed. Falling back to simple chunking.")
        return simple_chunking(text, chunk_size, overlap)

    sentences = sent_tokenize(text)
    return create_chunks_from_sentences(sentences, chunk_size, overlap)


def simple_chunking(text: str, chunk_size: int, overlap: int) -> List[str]:
    # Simple sentence splitting based on common sentence-ending punctuation
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return create_chunks_from_sentences(sentences, chunk_size, overlap)


def create_chunks_from_sentences(sentences: List[str], chunk_size: int, overlap: int) -> List[str]:
    num_sentences = len(sentences)

    if num_sentences == 0:
        logger.warning("No sentences found in the input text.")
        return []

    chunks = []
    step = chunk_size - overlap
    logger.info(f"Creating chunks with chunk_size={chunk_size} sentences, overlap={overlap} sentences, step={step}")
    logger.debug(f"Total sentences: {num_sentences}")

    for i in range(0, num_sentences, step):
        chunk_sentences = sentences[i:i + chunk_size]
        chunk = ' '.join(chunk_sentences)
        chunks.append(chunk)
        logger.debug(f"Chunk {len(chunks)}: {len(chunk)} chars from {len(chunk_sentences)} sentences")

    logger.info(f"Total chunks created: {len(chunks)}")
    logger.info(f"Average chunk size: {sum(len(c) for c in chunks) / len(chunks):.0f} characters")

    return chunks
