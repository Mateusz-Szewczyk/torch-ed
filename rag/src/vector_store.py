# vector_store.py
from datetime import datetime
import logging
import uuid
from typing import List, Dict, Any

import chromadb
from chromadb.config import Settings
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from .config import get_chroma_client_settings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Inicjalizacja embeddings
embeddings = OpenAIEmbeddings(model="text-embedding-3-large")


def _create_chroma_client():
    """
    Creates appropriate ChromaDB client based on configuration.
    Local: uses PersistentClient with persist_directory
    Remote: uses HttpClient for Railway ChromaDB service
    """
    settings = get_chroma_client_settings()

    if settings['mode'] == 'remote':
        logger.info(f"Connecting to remote ChromaDB at {settings['host']}:{settings['port']} (SSL: {settings['ssl']})")
        return chromadb.HttpClient(
            host=settings['host'],
            port=settings['port'],
            ssl=settings['ssl'],
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=False
            )
        )
    else:
        logger.info(f"Using local ChromaDB with persist_directory: {settings['persist_directory']}")
        return chromadb.PersistentClient(
            path=settings['persist_directory'],
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )


# Create the ChromaDB client (shared between collections)
_chroma_client = _create_chroma_client()

# Initialize collections using langchain_chroma with our client
collection_name = 'torched-rag'
client = Chroma(
    client=_chroma_client,
    collection_name=collection_name,
    embedding_function=embeddings,
)

memory_collection_name = 'user-memories'
memory_client = Chroma(
    client=_chroma_client,
    collection_name=memory_collection_name,
    embedding_function=embeddings,
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


def add_user_memory(user_id: str, text: str, importance: float = 0.5) -> str:
    """
    Dodaje pojedynczy fakt do pamięci długoterminowej użytkownika.
    """
    try:
        doc_id = f"mem_{user_id}_{uuid.uuid4()}"
        meta = {
            "user_id": user_id,
            "type": "memory",
            "importance": importance,
            "created_at": datetime.now().isoformat(),
            "last_accessed": datetime.now().isoformat()
        }

        memory_client.add_texts(
            texts=[text],
            metadatas=[meta],
            ids=[doc_id]
        )
        logger.info(f"Memory added for user {user_id}: '{text[:30]}...'")
        return doc_id
    except Exception as e:
        logger.error(f"Error adding memory: {e}", exc_info=True)
        return ""


def search_user_memories(query: str, user_id: str, n_results: int = 5, min_importance: float = 0.0) -> List[str]:
    """
    Wyszukuje semantycznie pasujące wspomnienia użytkownika.
    Zwraca listę samych tekstów (faktów).
    """
    try:
        # Filtrujemy po user_id i opcjonalnie po ważności
        results = memory_client.similarity_search_with_score(
            query=query,
            k=n_results,
            filter={"user_id": user_id}
        )

        memories = []
        for doc, score in results:
            # Próg podobieństwa (OpenAI Large: dystans cosinusowy, im mniejszy tym lepiej)
            if doc.metadata.get("importance", 0) >= min_importance:
                memories.append(doc.page_content)

        logger.info(f"Retrieved {len(memories)} relevant memories for user {user_id}")
        return memories
    except Exception as e:
        logger.error(f"Error searching memories: {e}", exc_info=True)
        return []


def delete_all_user_memories(user_id: str) -> bool:
    """Czyści całą pamięć danego użytkownika (np. na jego prośbę)."""
    try:
        memory_client.delete(where={"user_id": user_id})
        logger.info(f"All memories deleted for user_id={user_id}")
        return True
    except Exception as e:
        logger.error(f"Error deleting memories: {e}", exc_info=True)
        return False