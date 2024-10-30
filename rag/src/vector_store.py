# vector_store.py

import chromadb
from .config import PERSIST_DIRECTORY
import logging

logger = logging.getLogger(__name__)


def create_vector_store(chunks, embeddings, user_id, file_description, category, extracted_metadatas):
    """
    Creates a vector store using ChromaDB and stores the chunks with their embeddings and metadata.
    """
    client = chromadb.PersistentClient(path=PERSIST_DIRECTORY)
    collection_name = 'documents_collection'
    collection = client.get_or_create_collection(name=collection_name)

    metadatas = []
    ids = []
    for i, (chunk, metadata) in enumerate(zip(chunks, extracted_metadatas)):
        metadata_entry = {
            'user_id': user_id,
            'category': category,
            'description': file_description,
            'chunk_id': i,
            'names': ', '.join(metadata.get('names', [])),
            'locations': ', '.join(metadata.get('locations', [])),
            'dates': ', '.join(metadata.get('dates', [])),
            'key_terms': ', '.join(metadata.get('key_terms', []))
        }
        metadatas.append(metadata_entry)

        # Generate a unique ID by combining user_id with chunk index
        unique_id = f"{user_id}_{i}"
        ids.append(unique_id)

    try:
        collection.add(
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        logger.info(f"Added {len(chunks)} documents to ChromaDB for user_id: {user_id}")
    except Exception as e:
        logger.error(f"Error adding documents to ChromaDB: {e}")


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
        where={'user_id': user_id},
        include=['embeddings', 'documents', 'metadatas', 'distances']

    )

    return results
