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

    # 3. Process vector results and calculate similarity scores
    vector_reranked_results = []
    if vector_results and 'embeddings' in vector_results:
        doc_embeddings = vector_results['embeddings']
        documents = vector_results['documents']
        metadatas = vector_results['metadatas']

        # Calculate cosine similarity between query and document embeddings
        similarities = cosine_similarity([query_embedding], doc_embeddings)[0]

        # Combine results with their similarity scores
        for doc, metadata, score in zip(documents, metadatas, similarities):
            vector_reranked_results.append({
                'content': doc,
                'metadata': metadata,
                'similarity_score': score,
                'source': 'vector'
            })

    # 4. Search the graph store
    graph_results = search_graph_store(query, user_id)
    graph_reranked_results = search_graph_store(query, user_id)

    # 5. Process graph results and assign relevance scores
    graph_reranked_results = []
    if graph_results:
        for result in graph_results:
            if len(result) == 2:
                # Entity result
                entity, entity_type = result
                score = 0.6  # Assign a base score for entities
                graph_reranked_results.append({
                    'content': f"Entity: {entity} (Type: {entity_type})",
                    'metadata': {'type': entity_type},
                    'similarity_score': score,
                    'source': 'graph'
                })
            elif len(result) == 3:
                # Relationship result
                entity1, entity2, relation = result
                score = 0.7  # Assign a higher base score for relationships
                graph_reranked_results.append({
                    'content': f"Relation: {entity1} -[{relation}]-> {entity2}",
                    'metadata': {'relation': relation},
                    'similarity_score': score,
                    'source': 'graph'
                })

    # 6. Combine and rerank results
    combined_results = vector_reranked_results + graph_reranked_results

    # Normalize similarity scores to [0, 1]
    max_score = max([result['similarity_score'] for result in combined_results] + [1])
    min_score = min([result['similarity_score'] for result in combined_results] + [0])

    for result in combined_results:
        result['normalized_score'] = (result['similarity_score'] - min_score) / (max_score - min_score)

    # Sort combined results based on normalized scores
    combined_results.sort(key=lambda x: x['normalized_score'], reverse=True)

    # Return top n_results
    return combined_results[:n_results]
