from neo4j import GraphDatabase
from .config import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

def create_graph_entries(chunks, extracted_metadatas, user_id):
    """
    Tworzy węzły i relacje w bazie grafowej na podstawie fragmentów tekstu i wyekstrahowanych metadanych.

    Args:
        chunks (List[str]): Lista fragmentów tekstu.
        extracted_metadatas (List[dict]): Lista słowników z wyekstrahowanymi metadanymi dla każdego fragmentu.
        user_id (str): Identyfikator użytkownika, do którego przypisane są dane.

    Returns:
        None
    """
    with driver.session() as session:
        for i, (chunk, metadata) in enumerate(zip(chunks, extracted_metadatas)):
            # Tworzenie węzła Chunk z właściwością user_id
            session.run(
                """
                MERGE (c:Chunk {id: $chunk_id, user_id: $user_id})
                SET c.text = $text
                """,
                chunk_id=str(i),
                text=chunk,
                user_id=user_id
            )

            for entity_type in ['names', 'locations', 'dates', 'key_terms']:
                entities = metadata.get(entity_type, [])
                if not isinstance(entities, list):
                    entities = entities.split(', ') if entities else []

                for entity in entities:
                    if entity:
                        # Tworzenie węzła Entity z właściwością user_id
                        session.run(
                            """
                            MERGE (e:Entity {name: $entity, user_id: $user_id})
                            SET e.type = $type
                            """,
                            entity=entity.strip(),
                            type=entity_type,
                            user_id=user_id
                        )

                        # Tworzenie relacji między Chunk a Entity
                        session.run(
                            """
                            MATCH (c:Chunk {id: $chunk_id, user_id: $user_id})
                            MATCH (e:Entity {name: $entity, user_id: $user_id})
                            MERGE (c)-[:CONTAINS_ENTITY]->(e)
                            """,
                            chunk_id=str(i),
                            entity=entity.strip(),
                            user_id=user_id
                        )

def create_entity_relationships(extracted_metadatas, user_id):
    """
    Tworzy relacje między encjami na podstawie ich współwystępowania w fragmentach.

    Args:
        extracted_metadatas (List[dict]): Lista słowników z wyekstrahowanymi metadanymi dla każdego fragmentu.
        user_id (str): Identyfikator użytkownika, do którego przypisane są dane.

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
                    # Tworzenie relacji między encjami z uwzględnieniem user_id
                    session.run(
                        """
                        MATCH (a:Entity {name: $entity_a, user_id: $user_id})
                        MATCH (b:Entity {name: $entity_b, user_id: $user_id})
                        MERGE (a)-[:RELATED_TO]->(b)
                        """,
                        entity_a=entity_a,
                        entity_b=entity_b,
                        user_id=user_id
                    )

def search_graph_store(query, user_id=None):
    """
    Searches the Neo4j graph database for entities and relations matching the query,
    aggregates them by chunk to avoid duplicate texts, and calculates relevance scores.

    Args:
        query (str): The user's query.
        user_id (str, optional): User ID for filtering results.

    Returns:
        List[dict]: List of aggregated entities and relations with relevance scores.
    """
    with driver.session() as session:
        # Parameters for the query
        params = {'query': query}
        if user_id:
            params['user_id'] = user_id

        # Entity query with aggregation
        entity_query = """
        CALL db.index.fulltext.queryNodes('entityNameIndex', $query) YIELD node AS e, score
        """

        if user_id:
            entity_query += "WHERE e.user_id = $user_id\n"

        entity_query += """
        MATCH (c:Chunk {user_id: $user_id})-[:CONTAINS_ENTITY]->(e)
        WITH c, COLLECT(DISTINCT e.name) AS entities, COLLECT(DISTINCT e.type) AS types, AVG(score) AS avg_score
        RETURN c.text AS chunk_text, entities, types, avg_score ORDER BY avg_score DESC
        """

        # Execute the entity query
        result = session.run(entity_query, params)

        entities = []
        for record in result:
            chunk_text = record["chunk_text"]
            entity_names = record["entities"]
            entity_types = record["types"]
            score = record["avg_score"]

            # Combine entities and types into a list of tuples
            entity_info = list(zip(entity_names, entity_types))

            entities.append({
                'content': f"Entities: {entity_info}\nFragment tekstu: {chunk_text}",
                'metadata': {'entities': entity_info},
                'similarity_score': score,
                'source': 'graph_entity'
            })

        # Relation query with aggregation
        relation_query = """
        CALL db.index.fulltext.queryNodes('entityNameIndex', $query) YIELD node AS e1, score AS score1
        MATCH (e1)-[r]->(e2)
        """

        if user_id:
            relation_query += "WHERE e1.user_id = $user_id AND e2.user_id = $user_id\n"

        relation_query += """
        MATCH (c:Chunk {user_id: $user_id})-[:CONTAINS_ENTITY]->(e1)
        WHERE (c)-[:CONTAINS_ENTITY]->(e2)
        WITH c, COLLECT(DISTINCT [e1.name, type(r), e2.name]) AS relations, AVG(score1) AS avg_score1
        RETURN c.text AS chunk_text, relations, avg_score1 ORDER BY avg_score1 DESC
        """

        # Execute the relation query
        result = session.run(relation_query, params)

        relations = []
        for record in result:
            chunk_text = record["chunk_text"]
            relations_list = record["relations"]
            score = record["avg_score1"]

            # Format the relations
            relations_info = [f"{e1} -[{rel}]-> {e2}" for e1, rel, e2 in relations_list]

            relations.append({
                'content': f"Relations: {relations_info}\nFragment tekstu: {chunk_text}",
                'metadata': {'relations': relations_info},
                'similarity_score': score,
                'source': 'graph_relation'
            })

    # Combine entity and relation results
    graph_results = entities + relations
    return graph_results
