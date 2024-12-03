# vector_store.py

import chromadb
from .config import PERSIST_DIRECTORY
import logging
import uuid
from typing import List, Dict

# Inicjalizacja loggera
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Inicjalizacja klienta ChromaDB raz na moduł
client = chromadb.PersistentClient(path=PERSIST_DIRECTORY)
collection_name = 'documents_collection'
collection = client.get_or_create_collection(name=collection_name)


def generate_unique_id(user_id: str) -> str:
    """
    Generuje unikalny identyfikator dla embeddingu, łącząc user_id z UUID.

    Args:
        user_id (str): Unikalny identyfikator użytkownika.

    Returns:
        str: Unikalny identyfikator.
    """
    return f"{user_id}_{uuid.uuid4()}"


def create_vector_store(chunks: List[str], embeddings: List[List[float]], user_id: str, file_description: str, category: str, extracted_metadatas: List[Dict]):
    """
    Tworzy vector store używając ChromaDB i przechowuje chunks z ich embeddingami i metadanymi.

    Args:
        chunks (List[str]): Lista fragmentów dokumentu.
        embeddings (List[List[float]]): Lista embeddingów odpowiadających chunks.
        user_id (str): ID użytkownika przesyłającego plik.
        file_description (str): Opis przesłanego pliku.
        category (str): Kategoria dokumentu.
        extracted_metadatas (List[dict]): Lista metadanych dla każdego chunku.
    """
    metadatas = []
    ids = []
    for i, (chunk, metadata) in enumerate(zip(chunks, extracted_metadatas)):
        metadata_entry = {
            'user_id': user_id,
            'category': category,
            'description': file_description,
            'file_name': metadata.get('file_name', 'unknown'),  # Dodanie file_name do metadanych
            'chunk_id': i,
            'names': ', '.join(metadata.get('names', [])),
            'locations': ', '.join(metadata.get('locations', [])),
            'dates': ', '.join(metadata.get('dates', [])),
            'key_terms': ', '.join(metadata.get('key_terms', []))
        }
        metadatas.append(metadata_entry)

        # Generowanie unikalnego ID przy użyciu UUID
        unique_id = generate_unique_id(user_id)
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


def load_vector_store() -> chromadb.api.models.Collection:
    """
    Ładuje vector store z trwałego magazynu.

    Returns:
        Collection: Załadowana kolekcja z ChromaDB.
    """
    return collection


def search_vector_store(query: str, model, user_id: str, n_results: int = 5) -> Dict:
    """
    Przeszukuje vector store w poszukiwaniu chunks podobnych do zapytania.

    Args:
        query (str): Zapytanie wyszukiwania.
        model: Model embeddingu używany do kodowania zapytania.
        user_id (str): ID użytkownika do filtrowania wyszukiwania.
        n_results (int): Liczba wyników do zwrócenia.

    Returns:
        dict: Wyniki wyszukiwania.
    """
    collection = load_vector_store()
    query_embedding = model.encode(query, show_progress_bar=False)  # Użycie argumentów nazwanych

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where={'user_id': user_id},
        include=['embeddings', 'documents', 'metadatas', 'distances']
    )

    return results


def delete_file_from_vector_store(user_id: str, file_name: str) -> bool:
    """
    Deletes all documents associated with a given user_id and file_name from ChromaDB.

    Args:
        user_id (str): The user's unique identifier.
        file_name (str): The name of the file to delete.

    Returns:
        bool: True if deletion was successful, False otherwise.
    """
    collection = client.get_collection(collection_name)
    try:
        # Fetch documents matching user_id and file_name
        db_data = collection.get(
            where={
                'user_id': user_id,
                'file_name': file_name
            },
            include=['ids']
        )
        ids_to_delete = db_data['ids']

        if ids_to_delete:
            collection.delete(ids=ids_to_delete)
            logger.info(f"Deleted {len(ids_to_delete)} documents from ChromaDB for user_id: {user_id}, file_name: {file_name}")
            return True
        else:
            logger.warning(f"No documents found in ChromaDB for user_id: {user_id}, file_name: {file_name}")
            return False
    except Exception as e:
        logger.error(f"Error deleting documents from ChromaDB: {e}")
        return False
