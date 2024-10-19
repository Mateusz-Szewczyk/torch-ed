from .vector_store import search_vector_store
from .graph_store import search_graph_store
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from typing import List, Dict, Any
import logging

def search_and_rerank(query: str, model: Any, user_id: str, n_results: int = 5) -> List[Dict[str, Any]]:
    """
    Combines search results from the vector store and graph database,
    and reranks them based on relevance scores.

    Args:
        query (str): The user's query.
        model: The embedding model used to encode the query.
        user_id (str): The user ID to filter the search.
        n_results (int): The number of results to return.

    Returns:
        List[Dict[str, Any]]: Reranked search results.
    """
    query_embedding = model.encode(query)

    vector_results = search_vector_store(query, model, user_id, n_results * 2)

    vector_reranked_results = process_vector_results(vector_results, query_embedding)

    graph_results = search_graph_store(query, user_id)
    graph_reranked_results = process_graph_results(graph_results)

    combined_results = vector_reranked_results + graph_reranked_results
    return rerank_results(combined_results, n_results)

logger = logging.getLogger(__name__)

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

    # Ensure query_embedding is 2D
    if query_embedding.ndim == 1:
        query_embedding = query_embedding.reshape(1, -1)

    # Check if doc_embeddings has at least one embedding
    if doc_embeddings.size == 0:
        logger.warning("No document embeddings available for similarity calculation.")
        return []

    try:
        similarities = cosine_similarity(query_embedding, doc_embeddings)[0]
    except ValueError as ve:
        logger.error(f"Error computing cosine similarity: {ve}")
        return []

    return [
        {
            'content': doc,
            'metadata': metadata,
            'similarity_score': score,
            'source': 'vector'
        }
        for doc, metadata, score in zip(documents, metadatas, similarities)
    ]

def process_graph_results(graph_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            'content': result['content'],
            'metadata': result['metadata'],
            'similarity_score': result.get('similarity_score', 0.6),
            'source': result.get('source', 'graph')
        }
        for result in graph_results
        if 'content' in result and 'metadata' in result
    ]

def rerank_results(combined_results: List[Dict[str, Any]], n_results: int) -> List[Dict[str, Any]]:
    if not combined_results:
        print("No combined results to rerank.")
        return []

    scores = [result['similarity_score'] for result in combined_results]
    max_score, min_score = max(scores), min(scores)

    for result in combined_results:
        result['normalized_score'] = (result['similarity_score'] - min_score) / (max_score - min_score) if max_score != min_score else 1.0

    return sorted(combined_results, key=lambda x: x['normalized_score'], reverse=True)[:n_results]