# vector_store.py

import chromadb
import logging
import uuid
from typing import List, Dict
import chromadb.utils.embedding_functions as embedding_functions
from .config import PERSIST_DIRECTORY
from langchain_openai import OpenAIEmbeddings
import numpy as np

# Initialize logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Initialize ChromaDB client
client = chromadb.PersistentClient(path=PERSIST_DIRECTORY)
collection_name = 'documents_collection'
from sklearn.decomposition import PCA


def transform_embeddings(embeddings):
    """
    Transform embeddings using PCA while maintaining proper dimensionality

    Args:
        embeddings (List[List[float]]): List of embedding vectors
    Returns:
        List[List[float]]: Transformed embeddings
    """
    embeddings = np.array(embeddings)

    # Ensure embeddings are properly shaped (n_samples, n_features)
    if len(embeddings.shape) == 1:
        embeddings = embeddings.reshape(1, -1)

    # Get the minimum dimension for PCA
    n_components = min(384, embeddings.shape[0], embeddings.shape[1])

    # Apply PCA
    pca = PCA(n_components=n_components)
    transformed_embeddings = pca.fit_transform(embeddings)

    # If we need to pad to reach 384 dimensions
    if n_components < 384:
        padding = np.zeros((transformed_embeddings.shape[0], 384 - n_components))
        transformed_embeddings = np.hstack([transformed_embeddings, padding])

    return transformed_embeddings.tolist()

def get_or_create_collection():
    try:
        # Get or create the collection with the embedding function
        return client.get_or_create_collection(
            name=collection_name
        )
    except Exception as e:
        logger.error(f"Error getting or creating collection '{collection_name}': {e}", exc_info=True)
        raise


def delete_collection():
    try:
        client.delete_collection(name=collection_name)
        logger.info(f"Deleted collection '{collection_name}'.")
    except Exception as e:
        logger.error(f"Error deleting collection '{collection_name}': {e}", exc_info=True)
        raise


def generate_unique_id(user_id: str) -> str:
    return f"{user_id}_{uuid.uuid4()}"


def generate_embeddings(chunks: List[str]) -> List[List[float]]:
    embedding_model = OpenAIEmbeddings(model="text-embedding-3-large")

    embeddings = embedding_model.embed_documents(chunks)
    embeddings = transform_embeddings(embeddings)
    return embeddings



def create_vector_store(chunks: List[str],
                        user_id: str,
                        file_description: str,
                        category: str,
                        extracted_metadatas: List[Dict]):
    if len(chunks) == 0:
        logger.warning("No chunks provided. Nothing to add to vector store.")
        return
    if len(chunks) != len(extracted_metadatas):
        logger.warning(
            f"Number of chunks ({len(chunks)}) does not match number of metadata entries ({len(extracted_metadatas)}).")
        return

    # Define the embedding function
    embedding_function = OpenAIEmbeddings(model="text-embedding-3-large")

    # Generate embeddings
    try:
        embeddings = generate_embeddings(chunks)
    except Exception as e:
        logger.error(f"Error generating embeddings: {e}", exc_info=True)
        return

    metadatas = []
    ids = []

    for i, (chunk, metadata) in enumerate(zip(chunks, extracted_metadatas)):
        if not isinstance(metadata, dict):
            logger.debug(f"Metadata for chunk {i} is not a dict. Using empty dict.")
            metadata = {}

        file_name = metadata.get('file_name', 'unknown')
        names = metadata.get('names', [])
        locations = metadata.get('locations', [])
        dates = metadata.get('dates', [])
        key_terms = metadata.get('key_terms', [])

        if not isinstance(names, list):
            names = [n.strip() for n in str(names).split(',') if n.strip()]
        if not isinstance(locations, list):
            locations = [l.strip() for l in str(locations).split(',') if l.strip()]
        if not isinstance(dates, list):
            dates = [d.strip() for d in str(dates).split(',') if d.strip()]
        if not isinstance(key_terms, list):
            key_terms = [k.strip() for k in str(key_terms).split(',') if k.strip()]

        metadata_entry = {
            'user_id': user_id,
            'category': category,
            'description': file_description,
            'file_name': file_name,
            'chunk_id': i,
            'names': ', '.join(names),
            'locations': ', '.join(locations),
            'dates': ', '.join(dates),
            'key_terms': ', '.join(key_terms)
        }
        metadatas.append(metadata_entry)

        unique_id = generate_unique_id(user_id)
        ids.append(unique_id)

    collection = get_or_create_collection()

    try:
        collection.add(
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        logger.info(f"Added {len(chunks)} documents to ChromaDB for user_id: {user_id}, file: {file_description}")
    except Exception as e:
        logger.error(f"Error adding documents to ChromaDB: {e}", exc_info=True)


def load_vector_store():
    return get_or_create_collection()


def search_vector_store(query: str, user_id: str, n_results: int = 5) -> Dict:
    if not query.strip():
        logger.warning("Empty query provided to search_vector_store.")
        return {'documents': [[]], 'embeddings': [[]], 'metadatas': [[]], 'distances': [[]]}

    # Define the embedding function
    embedding_function = OpenAIEmbeddings(model="text-embedding-3-large")
    collection = get_or_create_collection()

    try:
        query_embedding = embedding_function.embed_query(query)
        query_embedding = transform_embeddings(query_embedding)

    except Exception as e:
        logger.error(f"Error embedding query '{query}': {e}", exc_info=True)
        return {'documents': [[]], 'embeddings': [[]], 'metadatas': [[]], 'distances': [[]]}

    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where={
                "$and": [
                    {"user_id": user_id},
                    {"file_name": "Jędrzej i Tajemniczy Chłopiec z Ron.txt"}  # Replace with dynamic file_name if needed
                ]
            },
            include=["documents", "embeddings", "metadatas", "distances"]
        )
        if not results.get('documents') or not results['documents'][0]:
            logger.info(f"No documents found for query: '{query}', user_id: {user_id}.")
        else:
            logger.info(f"Found {len(results['documents'][0])} results for query: '{query}', user_id: {user_id}.")
        return results
    except Exception as e:
        logger.error(f"Error querying vector store: {e}", exc_info=True)
        return {'documents': [[]], 'embeddings': [[]], 'metadatas': [[]], 'distances': [[]]}


def delete_file_from_vector_store(user_id: str, file_name: str) -> bool:
    collection = load_vector_store()
    try:
        db_data = collection.get(
            where={
                "$and": [
                    {"user_id": user_id},
                    {"file_name": file_name}
                ]
            },
            include=["embeddings", "metadatas"]
        )

        # Extract IDs from the results
        ids_to_delete = db_data.get('ids', [])
        if not ids_to_delete:
            # If 'ids' is not returned, attempt to extract from metadatas
            metadatas = db_data.get('metadatas', [])
            ids_to_delete = [meta.get('id') for meta in metadatas if 'id' in meta]

        if ids_to_delete:
            collection.delete(ids=ids_to_delete)
            logger.info(
                f"Deleted {len(ids_to_delete)} documents from ChromaDB for user_id: {user_id}, file_name: {file_name}")
            return True
        else:
            logger.warning(f"No documents found in ChromaDB for user_id: {user_id}, file_name: {file_name}")
            return False
    except Exception as e:
        logger.error(f"Error deleting documents from ChromaDB: {e}", exc_info=True)
        return False
