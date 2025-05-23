# vector_store.py

import logging
import uuid
from typing import List, Dict, Any

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from .config import PERSIST_DIRECTORY

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Inicjalizacja embeddings i Chroma
embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
collection_name = 'torched-rag'
client = Chroma(
    collection_name=collection_name,
    embedding_function=embeddings,
    persist_directory=PERSIST_DIRECTORY
)


def delete_collection() -> None:
    """Usuwa całą kolekcję z Chroma."""
    try:
        client.delete_collection()
        logger.info(f"Deleted collection '{collection_name}'.")
    except Exception as e:
        logger.error(f"Error deleting collection '{collection_name}': {e}", exc_info=True)
        raise


def generate_unique_id(user_id: str) -> str:
    """Generuje unikalne ID dokumentu."""
    return f"{user_id}_{uuid.uuid4()}"


# POPRAWKA: Zmieniona sygnatura funkcji, aby przyjmowała `file_name`
def create_vector_store(chunks: List[str],
                        user_id: str,
                        file_name: str,
                        file_description: str,
                        category: str) -> None:
    """
    Dodaje listę tekstów (chunków) do ChromaDB wraz z metadanymi,
    w tym z nazwą pliku.
    """
    if not chunks:
        logger.warning("No chunks provided. Nothing to add to vector store.")
        return

    try:
        metadatas = []
        ids = []
        for i, chunk in enumerate(chunks):
            doc_id = generate_unique_id(user_id)
            meta = {
                "user_id": user_id,
                # WAŻNE: Dodajemy nazwę pliku do metadanych każdego wektora
                "file_name": file_name,
                "file_description": file_description,
                "category": category,
                "chunk_index": i,
                "doc_id": doc_id
            }
            metadatas.append(meta)
            ids.append(doc_id)

        client.add_texts(
            texts=chunks,
            metadatas=metadatas,
            ids=ids
        )
        logger.info(f"Added {len(chunks)} documents to ChromaDB for user_id: {user_id}, file: {file_name}")
    except Exception as e:
        logger.error(f"Error adding documents to ChromaDB: {e}", exc_info=True)


def search_vector_store(query: str, user_id: str, n_results: int = 5) -> List[Dict[str, Any]]:
    """
    Wykonuje wyszukiwanie wektorowe w Chroma, zwraca listę słowników.
    """
    if not query.strip():
        logger.warning("Empty query provided to search_vector_store.")
        return []

    try:
        results = client.similarity_search_with_score(
            query=query,
            k=n_results,
            filter={"user_id": user_id}
        )
        output = []
        for doc, score in results:
            output.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": score
            })

        logger.info(f"Found {len(output)} results for query: '{query}', user_id: {user_id}")
        return output
    except Exception as e:
        logger.error(f"Error querying vector store: {e}", exc_info=True)
        return []


# POPRAWKA: Całkowicie zmieniona implementacja funkcji usuwającej
def delete_file_from_vector_store(user_id: str, file_name: str) -> bool:
    """
    Usuwa wektory z ChromaDB na podstawie user_id i file_name,
    używając poprawnego filtra z operatorem $and.
    """
    try:
        client.delete(
            where={
                "$and": [
                    {"user_id": {"$eq": user_id}},
                    {"file_name": {"$eq": file_name}}
                ]
            }
        )
        logger.info(f"Deletion request sent for documents from ChromaDB for user_id={user_id}, file_name={file_name}")
        return True
    except Exception as e:
        # Ten błąd może wystąpić, jeśli składnia filtra jest nieprawidłowa lub ChromaDB ma problem.
        logger.error(f"Error deleting documents from ChromaDB: {e}", exc_info=True)
        return False