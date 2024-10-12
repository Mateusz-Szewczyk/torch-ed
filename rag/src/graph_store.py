from neo4j import GraphDatabase
from .config import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))


def create_graph_entries(chunks, extracted_metadatas):
    """
    Creates nodes and relationships in the graph database based on the chunks and extracted metadata.

    Args:
        chunks (List[str]): The list of text chunks.
        extracted_metadatas (List[dict]): The list of metadata dictionaries extracted from each chunk.

    Returns:
        None
    """
    with driver.session() as session:
        for i, (chunk, metadata) in enumerate(zip(chunks, extracted_metadatas)):
            session.run(
                """
                MERGE (c:Chunk {id: $chunk_id})
                SET c.text = $text
                """,
                chunk_id=str(i),
                text=chunk
            )

            for entity_type in ['names', 'locations', 'dates', 'key_terms']:
                entities = metadata.get(entity_type, [])
                if not isinstance(entities, list):
                    entities = entities.split(', ') if entities else []

                for entity in entities:
                    if entity:
                        session.run(
                            """
                            MERGE (e:Entity {name: $entity})
                            SET e.type = $type
                            """,
                            entity=entity.strip(),
                            type=entity_type
                        )

                        session.run(
                            """
                            MATCH (c:Chunk {id: $chunk_id})
                            MATCH (e:Entity {name: $entity})
                            MERGE (c)-[:CONTAINS_ENTITY]->(e)
                            """,
                            chunk_id=str(i),
                            entity=entity.strip()
                        )


def create_entity_relationships(extracted_metadatas):
    """
    Creates relationships between entities based on their co-occurrence in chunks.

    Args:
        extracted_metadatas (List[dict]): The list of metadata dictionaries extracted from each chunk.

    Returns:
        None
    """
    with driver.session() as session:
        for metadata in extracted_metadatas:
            entities = []
            for entity_type in ['names', 'locations', 'dates', 'key_terms']:
                entity_list = metadata.get(entity_type, [])
                if not isinstance(entity_list, list):
                    entity_list = entity_list.split(', ') if entity_list else []
                entities.extend([e.strip() for e in entity_list if e])

            for i in range(len(entities)):
                for j in range(i + 1, len(entities)):
                    entity_a = entities[i]
                    entity_b = entities[j]
                    session.run(
                        """
                        MATCH (a:Entity {name: $entity_a})
                        MATCH (b:Entity {name: $entity_b})
                        MERGE (a)-[:RELATED_TO]->(b)
                        """,
                        entity_a=entity_a,
                        entity_b=entity_b
                    )

def search_graph_store(query, user_id=None):
    """
    Searches the Neo4j graph database for entities and relationships matching the query,
    using full-text search, and calculates relevance scores.

    Args:
        query (str): User's query.
        user_id (str, optional): User ID for filtering results.

    Returns:
        List[dict]: List of entities and relationships with relevance scores.
    """
    with driver.session() as session:
        # Parameters for query
        params = {'query': query}
        if user_id:
            params['user_id'] = user_id

        # Build query with optional user_id filtering
        entity_query = """
        CALL db.index.fulltext.queryNodes('entityNameIndex', $query) YIELD node, score
        """

        if user_id:
            entity_query += "WHERE node.user_id = $user_id\n"

        entity_query += "RETURN node.name AS entity, node.type AS type, score ORDER BY score DESC"

        # Execute entity query
        result = session.run(entity_query, params)

        entities = []
        for record in result:
            entity_name = record["entity"]
            entity_type = record["type"]
            score = record["score"]
            entities.append({
                'content': f"Entity: {entity_name} (Type: {entity_type})",
                'metadata': {'type': entity_type},
                'similarity_score': score,
                'source': 'graph_entity'
            })

        # Build relationship query
        relation_query = """
        CALL db.index.fulltext.queryNodes('entityNameIndex', $query) YIELD node AS e1, score AS score1
        MATCH (e1)-[r]-(e2)
        """

        if user_id:
            relation_query += "WHERE e1.user_id = $user_id AND e2.user_id = $user_id\n"

        relation_query += "RETURN e1.name AS entity1, e2.name AS entity2, type(r) AS relation, score1 ORDER BY score1 DESC"

        # Execute relationship query
        result = session.run(relation_query, params)

        relations = []
        for record in result:
            entity1 = record["entity1"]
            entity2 = record["entity2"]
            relation = record["relation"]
            score = record["score1"]
            relations.append({
                'content': f"Relation: {entity1} -[{relation}]-> {entity2}",
                'metadata': {'relation': relation},
                'similarity_score': score,
                'source': 'graph_relation'
            })

    # Combine entities and relations
    graph_results = entities + relations
    return graph_results
