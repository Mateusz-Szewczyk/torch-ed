import chromadb
from .config import PERSIST_DIRECTORY

def create_vector_store(chunks, embeddings, user_id, file_description, category, extracted_metadatas):
    """
    Creates a vector store using ChromaDB and stores the chunks with their embeddings and metadata.

    Args:
        chunks (List[str]): The list of text chunks.
        embeddings (List): The list of embeddings corresponding to the chunks.
        user_id (str): The user ID associated with the data.
        file_description (str): A description of the file.
        category (str): The category of the text.
        extracted_metadatas (List[dict]): The list of metadata dictionaries extracted from each chunk.

    Returns:
        None
    """
    # Use the new PersistentClient initialization
    client = chromadb.PersistentClient(path=PERSIST_DIRECTORY)

    collection_name = 'documents_collection'
    collection = client.get_or_create_collection(name=collection_name)

    metadatas = []
    for i in range(len(chunks)):
        metadata = {
            'user_id': user_id,
            'category': category,
            'description': file_description,
            'chunk_id': i
        }

        metadata['names'] = ', '.join(extracted_metadatas[i].get('names', []))
        metadata['locations'] = ', '.join(extracted_metadatas[i].get('locations', []))
        metadata['dates'] = ', '.join(extracted_metadatas[i].get('dates', []))
        metadata['key_terms'] = ', '.join(extracted_metadatas[i].get('key_terms', []))

        metadatas.append(metadata)

    collection.add(
        documents=chunks,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=[str(i) for i in range(len(chunks))]
    )


def load_vector_store():
    """
    Loads the vector store from persistent storage.

    Returns:
        Collection: The loaded collection from ChromaDB.
    """
    client = chromadb.PersistentClient(path=PERSIST_DIRECTORY)
    collection_name = 'documents_collection'
    collection = client.get_or_create_collection(name=collection_name)
    return collection


def search_vector_store(query, model, user_id, n_results=5):
    """
    Searches the vector store for chunks similar to the query.

    Args:
        query (str): The search query.
        model: The embedding model used to encode the query.
        user_id (str): The user ID to filter the search.
        n_results (int): The number of results to return.

    Returns:
        dict: The search results.
    """
    collection = load_vector_store()
    query_embedding = model.encode(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where={'user_id': user_id}
    )

    return results
