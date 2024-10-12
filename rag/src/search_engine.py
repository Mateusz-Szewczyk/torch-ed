from .vector_store import search_vector_store
from .graph_store import search_graph_store
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

def search_and_rerank(query, model, user_id, n_results=5):
    """
    Combines search results from the vector store and graph database,
    and reranks them based on relevance scores.

    Args:
        query (str): The user's query.
        model: The embedding model used to encode the query.
        user_id (str): The user ID to filter the search.
        n_results (int): The number of results to return.

    Returns:
        List[dict]: Reranked search results.
    """
    # 1. Encode the query using the embedding model
    query_embedding = model.encode(query)

    # 2. Search the vector store
    vector_results = search_vector_store(query, model, user_id, n_results*2)
    print("Vector store results:", vector_results)

    # 3. Process vector results and calculate similarity scores
    vector_reranked_results = []
    if vector_results and 'embeddings' in vector_results and vector_results['embeddings']:
        # Extract embeddings
        doc_embeddings = vector_results['embeddings'][0]  # May have shape (N, D) or (1, N, D)
        documents = vector_results['documents'][0]
        metadatas = vector_results['metadatas'][0]

        # Ensure embeddings are numpy arrays
        doc_embeddings = np.array(doc_embeddings)
        query_embedding = np.array(query_embedding)

        # Reshape embeddings if necessary
        if doc_embeddings.ndim == 3:
            # Reshape from (1, N, D) to (N, D)
            doc_embeddings = doc_embeddings.reshape(-1, doc_embeddings.shape[-1])

        # Reshape query_embedding to (1, D)
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)

        # Calculate cosine similarity between query and document embeddings
        similarities = cosine_similarity(query_embedding, doc_embeddings)[0]

        # Combine results with their similarity scores
        for doc, metadata, score in zip(documents, metadatas, similarities):
            vector_reranked_results.append({
                'content': doc,
                'metadata': metadata,
                'similarity_score': score,
                'source': 'vector'
            })
    else:
        print("No embeddings returned from vector store.")

    # 4. Search the graph store
    graph_results = search_graph_store(query, user_id)

    # 5. Process graph results and assign relevance scores
    graph_reranked_results = []
    if graph_results:
        for result in graph_results:
            if 'content' in result and 'metadata' in result:
                graph_reranked_results.append({
                    'content': result['content'],
                    'metadata': result['metadata'],
                    'similarity_score': result.get('similarity_score', 0.6),
                    'source': result.get('source', 'graph')
                })

    # 6. Combine and rerank results
    combined_results = vector_reranked_results + graph_reranked_results

    # Normalize similarity scores to [0, 1]
    if combined_results:
        max_score = max([result['similarity_score'] for result in combined_results])
        min_score = min([result['similarity_score'] for result in combined_results])

        for result in combined_results:
            if max_score != min_score:
                result['normalized_score'] = (result['similarity_score'] - min_score) / (max_score - min_score)
            else:
                result['normalized_score'] = 1.0  # Jeśli wszystkie wyniki mają ten sam score
    else:
        print("No combined results to rerank.")
        return []

    # Sort combined results based on normalized scores
    combined_results.sort(key=lambda x: x['normalized_score'], reverse=True)

    # Return top n_results
    return combined_results[:n_results]
