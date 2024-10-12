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
    Przeszukuje bazę grafową Neo4j w poszukiwaniu encji i relacji pasujących do zapytania,
    wykorzystując wyszukiwanie pełnotekstowe, i oblicza ich relewancję.

    Args:
        query (str): Zapytanie użytkownika.
        user_id (str, opcjonalnie): Identyfikator użytkownika do filtrowania wyników.

    Returns:
        List[dict]: Lista encji i relacji z oceną relewancji.
    """
    with driver.session() as session:
        # Parametry zapytania
        params = {'query': query}
        if user_id:
            params['user_id'] = user_id

        # Zapytanie dla encji z fragmentem tekstu
        entity_query = """
        CALL db.index.fulltext.queryNodes('entityNameIndex', $query) YIELD node AS e, score
        """

        if user_id:
            entity_query += "WHERE e.user_id = $user_id\n"

        entity_query += """
        MATCH (c:Chunk {user_id: $user_id})-[:CONTAINS_ENTITY]->(e)
        RETURN e.name AS entity, e.type AS type, c.text AS chunk_text, score ORDER BY score DESC
        """

        # Wykonanie zapytania dla encji
        result = session.run(entity_query, params)

        entities = []
        for record in result:
            entity_name = record["entity"]
            entity_type = record["type"]
            chunk_text = record["chunk_text"]
            score = record["score"]
            entities.append({
                'content': f"Entity: {entity_name} (Type: {entity_type})\nFragment tekstu: {chunk_text}",
                'metadata': {'type': entity_type},
                'similarity_score': score,
                'source': 'graph_entity'
            })

        # Zapytanie dla relacji z fragmentem tekstu
        relation_query = """
        CALL db.index.fulltext.queryNodes('entityNameIndex', $query) YIELD node AS e1, score AS score1
        MATCH (e1)-[r]-(e2)
        """

        if user_id:
            relation_query += "WHERE e1.user_id = $user_id AND e2.user_id = $user_id\n"

        relation_query += """
        MATCH (c:Chunk {user_id: $user_id})-[:CONTAINS_ENTITY]->(e1)
        WHERE (c)-[:CONTAINS_ENTITY]->(e2)
        RETURN e1.name AS entity1, e2.name AS entity2, type(r) AS relation, c.text AS chunk_text, score1 ORDER BY score1 DESC
        """

        # Wykonanie zapytania dla relacji
        result = session.run(relation_query, params)

        relations = []
        for record in result:
            entity1 = record["entity1"]
            entity2 = record["entity2"]
            relation = record["relation"]
            chunk_text = record["chunk_text"]
            score = record["score1"]
            relations.append({
                'content': f"Relation: {entity1} -[{relation}]-> {entity2}\nFragment tekstu: {chunk_text}",
                'metadata': {'relation': relation},
                'similarity_score': score,
                'source': 'graph_relation'
            })

    # Połączenie wyników encji i relacji
    graph_results = entities + relations
    return graph_results
