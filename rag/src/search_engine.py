import os
from typing import List, Dict, Any
import logging
import numpy as np
import uuid
from langchain_openai import OpenAIEmbeddings
from sklearn.metrics.pairwise import cosine_similarity
from langchain.schema import Document
from langchain_community.retrievers import BM25Retriever

from .vector_store import search_vector_store  # Import z pliku vector_store.py

logger = logging.getLogger(__name__)


def search_and_rerank(query: str,
                      user_id: str,
                      n_results: int = 5) -> List[Dict[str, Any]]:
    """
    Wyszukiwanie wektorowe + BM25 + reranking wyników.
    Zwraca listę słowników z kluczami:
    - content
    - metadata
    - similarity_score
    - bm25_score
    - final_score
    - _id
    """
    # 1. Wyszukanie w wektorach
    vector_results = search_vector_store(query=query, user_id=user_id, n_results=n_results)

    if not vector_results:
        logger.info("Brak wyników z wyszukiwania wektorowego.")
        return []

    # 2. Nadanie unikalnych _id jeśli nie istnieją
    for res in vector_results:
        if "metadata" not in res:
            res["metadata"] = {}
        if "_id" not in res["metadata"]:
            new_id = str(uuid.uuid4())
            res["metadata"]["_id"] = new_id
        else:
            new_id = res["metadata"]["_id"]

        # Zmieniamy klucz, by łatwiej się odwoływać w doc
        res["_id"] = new_id

    # 3. BM25 Reranking
    # Zamieniamy wyniki wektorowe w listę Document
    documents = []
    for res in vector_results:
        doc = Document(
            page_content=res["content"],
            metadata=res["metadata"]
        )
        documents.append(doc)

    # Tworzymy BM25Retriever
    retriever = BM25Retriever.from_documents(documents)
    bm25_docs = retriever.invoke(query)

    # Mapa doc_id -> rank
    bm25_mapping = {}
    for rank, doc in enumerate(bm25_docs, start=1):
        doc_id = doc.metadata.get("_id")
        if doc_id:
            bm25_mapping[doc_id] = rank

    # 4. Hybrydowe łączenie wyników: sim_score + bm25_score
    final_results = []
    for res in vector_results:
        sim_score = res.get("score", 0.0)  # z wektora
        doc_id = res["_id"]
        bm25_rank = bm25_mapping.get(doc_id)
        if bm25_rank:
            bm25_score = 1 / (bm25_rank + 1e-9)
        else:
            bm25_score = 0.1  # default

        final_score = sim_score + bm25_score
        new_res = {
            "content": res["content"],
            "metadata": res["metadata"],
            "similarity_score": sim_score,
            "bm25_score": bm25_score,
            "final_score": final_score,
            "_id": doc_id
        }
        final_results.append(new_res)

    # Sortowanie malejąco po final_score
    final_results.sort(key=lambda x: x["final_score"], reverse=True)
    final_docs = final_results[:n_results]

    if not final_docs:
        logger.info("Nie znaleziono sensownych informacji.")
    else:
        logger.info(f"Znaleziono {len(final_docs)} dopasowań po hybrydowym rankingu.")

    return final_docs


def process_vector_results(vector_results: Dict[str, Any], query_embedding: np.ndarray) -> List[Dict[str, Any]]:
    """
    Przetwarza wyniki z vector_store i oblicza cosinus similarity z query_embedding.
    """
    if not vector_results or 'embeddings' not in vector_results or not vector_results['embeddings']:
        logger.warning("No embeddings returned from vector store.")
        return []

    doc_embeddings = np.array(vector_results['embeddings'][0])     # (k, 384) np.
    documents = vector_results['documents'][0]                     # (k) list str
    metadatas = vector_results['metadatas'][0]                     # (k) list dict

    if len(doc_embeddings) == 0:
        logger.warning("Document embeddings are empty.")
        return []

    # Upewniamy się, że doc_embeddings jest 2D
    if doc_embeddings.ndim == 3:
        # Bywa, że Chroma zwraca [1, k, dim]
        doc_embeddings = doc_embeddings.reshape(-1, doc_embeddings.shape[-1])

    if query_embedding.ndim == 1:
        query_embedding = query_embedding.reshape(1, -1)

    if doc_embeddings.size == 0:
        logger.warning("No document embeddings available for similarity calculation.")
        return []

    # Liczymy cosinus similarity
    try:
        similarities = cosine_similarity(query_embedding, doc_embeddings)[0]
    except ValueError as ve:
        logger.error(f"Error computing cosine similarity: {ve}")
        return []

    # Tworzymy listę wyników
    results = []
    for doc, meta, score in zip(documents, metadatas, similarities):
        results.append({
            'content': doc,
            'metadata': meta,
            'similarity_score': float(score),
            'source': 'vector'
        })

    # Sortujemy malejąco po similarity_score
    results.sort(key=lambda x: x['similarity_score'], reverse=True)

    if results:
        logger.info(f"Uzyskano {len(results)} wyników z wektorów. Najwyższy similarity_score: {results[0]['similarity_score']}")
    else:
        logger.info("Brak wyników z wektorów.")

    return results



def retrieve(query: str):
    logging.basicConfig(level=logging.INFO)
    embedding_model = OpenAIEmbeddings(model="text-embedding-3-large")

    user_id = "1"
    results = search_and_rerank(query, user_id, n_results=3)
    print("Wyniki:")
    for r in results:
        print(r.get('content', 'Brak treści'))

from .chunking import create_chunks
from .vector_store import create_vector_store

def upload():
    # Parametry testowe
    test_file_path = '../data/amos_pulapki.txt'  # Ścieżka do pliku
    test_user_id = 'user-123'
    test_file_description = 'Testowy plik Jedrek'
    test_category = 'test-category'

    # Otwieranie i czytanie pliku

    with open(test_file_path, 'r', encoding='utf-8') as f:
        text = f.read()
    logger.info(f"Pobrano tekst z pliku: {test_file_path}")

    # Tworzenie chunków za pomocą funkcji create_chunks
    chunks = create_chunks(text)

    # Dodawanie chunków do vector store
    try:
        create_vector_store(
            chunks=chunks,
            user_id=test_user_id,
            file_description=test_file_description,
            category=test_category
        )
        logger.info("Chunku zostały pomyślnie dodane do vector store.")
    except Exception as e:
        logger.error(f"Error adding chunks to vector store: {e}", exc_info=True)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Prosty interfejs tekstowy
    print("Wybierz opcję:")
    print("1) Upload (dodaj/chunkuj plik i zapisz wektory).")
    print("2) Wyszukaj (zadaj zapytanie i zobacz wyniki).")

    choice = input("Twój wybór (1/2): ").strip()

    if choice == "1":
        # Wywołuje funkcję upload()
        print("Uruchamiam upload()...")
        upload()

    elif choice == "2":
        # Pytamy użytkownika o query
        query_text = input("Podaj zapytanie: ")
        print(f"Uruchamiam retrieve() z zapytaniem: '{query_text}'\n")
        retrieve(query_text)

    else:
        print("Nieznana opcja. Zakończono.")
