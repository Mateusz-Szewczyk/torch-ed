import nltk
from nltk.tokenize import sent_tokenize

nltk.download('punkt')


def create_chunks(text, chunk_size=8, overlap=2):
    """
    Splits the input text into overlapping chunks of sentences.

    Args:
        text (str): The input text to split into chunks.
        chunk_size (int): The number of sentences in each chunk.
        overlap (int): The number of sentences that overlap between chunks.

    Returns:
        List[str]: A list of text chunks.
    """
    sentences = sent_tokenize(text)
    if chunk_size <= overlap:
        raise ValueError("Chunk size must be greater than overlap")

    chunks = []
    step = chunk_size - overlap
    for i in range(0, len(sentences), step):
        chunk_sentences = sentences[i:i + chunk_size]
        chunk = ' '.join(chunk_sentences)
        chunks.append(chunk)

    return chunks
