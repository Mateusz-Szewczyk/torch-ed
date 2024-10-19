import logging
import re

# Initialize logger
logger = logging.getLogger(__name__)

def create_chunks(text, chunk_size=8, overlap=2):
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

def nltk_chunking(text, chunk_size, overlap):
    try:
        import nltk
        from nltk.tokenize import sent_tokenize
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        logger.warning("NLTK 'punkt' resource not found. Downloading now...")
        nltk.download('punkt', quiet=True)
        nltk.download('punkt_tab')
    except ImportError:
        logger.error("NLTK is not installed. Falling back to simple chunking.")
        return simple_chunking(text, chunk_size, overlap)

    sentences = sent_tokenize(text)
    return create_chunks_from_sentences(sentences, chunk_size, overlap)

def simple_chunking(text, chunk_size, overlap):
    # Simple sentence splitting based on common sentence-ending punctuation
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return create_chunks_from_sentences(sentences, chunk_size, overlap)

def create_chunks_from_sentences(sentences, chunk_size, overlap):
    num_sentences = len(sentences)

    if num_sentences == 0:
        logger.warning("No sentences found in the input text.")
        return []

    chunks = []
    step = chunk_size - overlap
    logger.info(f"Creating chunks with chunk_size={chunk_size}, overlap={overlap}, step={step}")
    logger.debug(f"Total sentences: {num_sentences}")

    for i in range(0, num_sentences, step):
        chunk_sentences = sentences[i:i + chunk_size]
        chunk = ' '.join(chunk_sentences)
        chunks.append(chunk)
        logger.debug(f"Chunk {len(chunks)}: {chunk[:100]}...")  # Log first 100 chars of the chunk

    logger.info(f"Total chunks created: {len(chunks)}")
    return chunks