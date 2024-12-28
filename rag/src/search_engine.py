import os
from typing import List, Dict, Any
import logging
import numpy as np
import uuid
from langchain_openai import OpenAIEmbeddings
from sklearn.metrics.pairwise import cosine_similarity
from langchain.schema import Document
from langchain_community.retrievers import BM25Retriever

from rag.src.graph_store import search_graph_store
from rag.src.vector_store import search_vector_store

logger = logging.getLogger(__name__)

def search_and_rerank(query: str, model: Any, user_id: str, n_results: int = 5) -> List[Dict[str, Any]]:
    # Use embed_query instead of encode
    query_embedding = model.embed_query(query)

    vector_results = search_vector_store(query=query, n_results=n_results, user_id=user_id)
    vector_reranked_results = process_vector_results(vector_results, query_embedding)

    graph_results = search_graph_store(query, user_id)
    graph_reranked_results = process_graph_results(graph_results)

    combined_results = vector_reranked_results + graph_reranked_results
    if not combined_results:
        logger.warning("Brak wyników do rerankowania.")
        return []

    for res in combined_results:
        if '_id' not in res:
            res['_id'] = str(uuid.uuid4())

    documents = [Document(page_content=res['content'], metadata={**res['metadata'], '_id': res['_id']}) for res in combined_results]
    retriever = BM25Retriever.from_documents(documents)
    bm25_docs = retriever.invoke(query)

    bm25_mapping = {}
    for rank, doc in enumerate(bm25_docs, start=1):
        doc_id = doc.metadata.get('_id')
        if doc_id:
            bm25_mapping[doc_id] = rank

    final_results = []
    for res in combined_results:
        sim_score = res['similarity_score']
        bm25_rank = bm25_mapping.get(res['_id'], None)

        if bm25_rank is not None:
            bm25_score = 1 / (bm25_rank + 1e-9)
        else:
            bm25_score = 0.1

        final_score = sim_score + bm25_score
        res['final_score'] = final_score
        final_results.append(res)

    final_results = sorted(final_results, key=lambda x: x['final_score'], reverse=True)
    final_docs = final_results[:n_results]

    if not final_docs:
        logger.info("Nie znaleziono sensownych informacji.")
    else:
        logger.info(f"Znaleziono {len(final_docs)} dopasowań po hybrydowym rankingu.")

    return final_docs

def process_vector_results(vector_results: Dict[str, Any], query_embedding: np.ndarray) -> List[Dict[str, Any]]:
    if not vector_results or 'embeddings' not in vector_results or not vector_results['embeddings']:
        logger.warning("No embeddings returned from vector store.")
        return []

    doc_embeddings = np.array(vector_results['embeddings'][0])
    documents = vector_results['documents'][0]
    metadatas = vector_results['metadatas'][0]

    if len(doc_embeddings) == 0:
        logger.warning("Document embeddings are empty.")
        return []

    if doc_embeddings.ndim == 3:
        doc_embeddings = doc_embeddings.reshape(-1, doc_embeddings.shape[-1])

    if query_embedding.ndim == 1:
        query_embedding = query_embedding.reshape(1, -1)

    if doc_embeddings.size == 0:
        logger.warning("No document embeddings available for similarity calculation.")
        return []

    try:
        similarities = cosine_similarity(query_embedding, doc_embeddings)[0]
    except ValueError as ve:
        logger.error(f"Error computing cosine similarity: {ve}")
        return []

    results = [
        {
            'content': doc,
            'metadata': metadata,
            'similarity_score': float(score),
            'source': 'vector'
        }
        for doc, metadata, score in zip(documents, metadatas, similarities)
    ]

    results = sorted(results, key=lambda x: x['similarity_score'], reverse=True)
    logger.info(f"Uzyskano {len(results)} wyników z wektorów. Najwyższy similarity_score: {results[0]['similarity_score'] if results else 'Brak'}")
    return results

def process_graph_results(graph_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    filtered = [
        {
            'content': result['content'],
            'metadata': result.get('metadata', {}),
            'similarity_score': float(result.get('similarity_score', 0.6)),
            'source': result.get('source', 'graph')
        }
        for result in graph_results
        if 'content' in result
    ]

    if filtered:
        filtered = sorted(filtered, key=lambda x: x['similarity_score'], reverse=True)
        logger.info(f"Uzyskano {len(filtered)} wyników z grafu. Najwyższy similarity_score: {filtered[0]['similarity_score']}")
    else:
        logger.info("Brak wyników z grafu.")

    return filtered

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    embedding_model = OpenAIEmbeddings(model="text-embedding-3-large")

    user_id = "user-123"
    query = "Jakiego koloru jest kot Jędrek?"
    results = search_and_rerank(query, embedding_model, user_id, n_results=8)
    print("Wyniki:")
    for r in results:
        print(r.get('content', 'Brak treści'))
