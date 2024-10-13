from neo4j import GraphDatabase
from .config import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD
from typing import List, Dict, Any

# Initialize the Neo4j driver
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

def ensure_fulltext_indexes():
    with driver.session() as session:
        # Check existing indexes using the updated Neo4j command
        existing_indexes = session.run("SHOW INDEXES YIELD name RETURN name")
        index_names = [record["name"] for record in existing_indexes]

        # Create 'entityFullTextIndex' if it doesn't exist
        if 'entityFullTextIndex' not in index_names:
            session.run("""
                CREATE FULLTEXT INDEX entityFullTextIndex FOR (n:Entity) ON EACH [n.name, n.type];
            """)
            print("Created 'entityFullTextIndex' full-text index.")

        # Create 'chunkTextIndex' if it doesn't exist
        if 'chunkTextIndex' not in index_names:
            session.run("""
                CREATE FULLTEXT INDEX chunkTextIndex FOR (n:Chunk) ON EACH [n.text];
            """)
            print("Created 'chunkTextIndex' full-text index.")

def create_graph_entries(chunks, extracted_metadatas, user_id):
    """
    Creates nodes and relationships in the graph database based on text chunks and extracted metadata.

    Args:
        chunks (List[str]): List of text chunks.
        extracted_metadatas (List[dict]): List of dictionaries with extracted metadata for each chunk.
        user_id (str): User identifier to which the data belongs.

    Returns:
        None
    """
    ensure_fulltext_indexes()
    with driver.session() as session:
        session.run("CALL db.awaitIndexes()")

    with driver.session() as session:
        for i, (chunk, metadata) in enumerate(zip(chunks, extracted_metadatas)):
            # Create Chunk node with user_id property
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
                        # Create Entity node with user_id and type properties
                        session.run(
                            """
                            MERGE (e:Entity {name: $entity, user_id: $user_id})
                            SET e.type = $type
                            """,
                            entity=entity.strip(),
                            type=entity_type,
                            user_id=user_id
                        )

                        # Create relationship between Chunk and Entity
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
    Creates relationships between entities based on their co-occurrence in chunks.

    Args:
        extracted_metadatas (List[dict]): List of dictionaries with extracted metadata for each chunk.
        user_id (str): User identifier to which the data belongs.

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

            # Avoid creating relationships if there's less than 2 entities
            if len(entities) < 2:
                continue

            # Create relationships in a single query
            session.run(
                """
                UNWIND $entity_pairs AS pair
                MATCH (a:Entity {name: pair[0], user_id: $user_id})
                MATCH (b:Entity {name: pair[1], user_id: $user_id})
                MERGE (a)-[:CO_OCCURS_WITH]->(b)
                """,
                entity_pairs=[list(pair) for pair in combinations(entities, 2)],
                user_id=user_id
            )

def search_graph_store(query: str, user_id: str = None) -> List[Dict[str, Any]]:
    """
    Searches the Neo4j graph database for entities, relations, and chunks matching the query,
    aggregates them, and calculates relevance scores.

    Args:
        query (str): The user's query.
        user_id (str, optional): User ID for filtering results.

    Returns:
        List[Dict[str, Any]]: List of aggregated results with relevance scores.
    """
    try:
        with driver.session() as session:
            params = {'query': query}
            if user_id:
                params['user_id'] = user_id

            entity_results = _execute_entity_query(session, params)
            relation_results = _execute_relation_query(session, params)
            chunk_results = _execute_chunk_query(session, params)

            graph_results = entity_results + relation_results + chunk_results
            return sorted(graph_results, key=lambda x: x['similarity_score'], reverse=True)
    except Exception as e:
        print(f"An error occurred while searching the graph store: {e}")
        return []

def _execute_entity_query(session, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    query = _build_entity_query(params)
    results = session.run(query, params)
    return [_process_entity_result(record) for record in results]

def _execute_relation_query(session, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    query = _build_relation_query(params)
    results = session.run(query, params)
    return [_process_relation_result(record) for record in results]

def _execute_chunk_query(session, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    query = _build_chunk_query(params)
    results = session.run(query, params)
    return [_process_chunk_result(record) for record in results]

def _build_entity_query(params: Dict[str, Any]) -> str:
    query = """
    CALL db.index.fulltext.queryNodes('entityFullTextIndex', $query) YIELD node AS e0, score
    MATCH (e0)-[:CO_OCCURS_WITH*0..2]-(e:Entity)
    MATCH (c:Chunk)-[:CONTAINS_ENTITY]->(e)
    """
    if params.get('user_id'):
        query += "WHERE c.user_id = $user_id AND e.user_id = $user_id\n"
    query += """
    WITH DISTINCT c, e, e.type AS type, score
    ORDER BY score DESC
    WITH c, COLLECT(DISTINCT e.name) AS entities, COLLECT(DISTINCT type) AS types, AVG(score) AS avg_score
    RETURN c.text AS chunk_text, entities, types, avg_score
    LIMIT 50
    """
    return query

def _build_relation_query(params: Dict[str, Any]) -> str:
    query = """
    CALL db.index.fulltext.queryNodes('entityFullTextIndex', $query) YIELD node AS e0, score AS score1
    MATCH (e0)-[:CO_OCCURS_WITH*0..2]-(e1:Entity)
    MATCH (e1)-[r:CO_OCCURS_WITH]->(e2:Entity)
    MATCH (c:Chunk)-[:CONTAINS_ENTITY]->(e1)
    WHERE (c)-[:CONTAINS_ENTITY]->(e2)
    """
    if params.get('user_id'):
        query += "AND c.user_id = $user_id AND e1.user_id = $user_id AND e2.user_id = $user_id\n"
    query += """
    WITH DISTINCT c, e1, e2, type(r) AS rel_type, score1
    ORDER BY score1 DESC
    WITH c, COLLECT(DISTINCT e1.name + ' -[' + rel_type + ']-> ' + e2.name) AS relations, AVG(score1) AS avg_score1
    RETURN c.text AS chunk_text, relations, avg_score1
    LIMIT 50
    """
    return query

def _build_chunk_query(params: Dict[str, Any]) -> str:
    # Upgraded query to search in chunk text and associated key terms
    query = """
    CALL db.index.fulltext.queryNodes('chunkTextIndex', $query) YIELD node AS c, score
    """
    if params.get('user_id'):
        query += "WHERE c.user_id = $user_id\n"
    query += """
    WITH c, score
    ORDER BY score DESC
    RETURN c.text AS chunk_text, score
    LIMIT 10
    """
    return query

def _process_entity_result(record) -> Dict[str, Any]:
    entities = record['entities']
    types = record['types']
    entity_info = list(zip(entities, types))
    return {
        'content': f"Entities: {entity_info}\nFragment tekstu: {record['chunk_text']}",
        'metadata': {'entities': entity_info},
        'similarity_score': record['avg_score'],
        'source': 'graph_entity'
    }

def _process_relation_result(record) -> Dict[str, Any]:
    return {
        'content': f"Relations: {record['relations']}\nFragment tekstu: {record['chunk_text']}",
        'metadata': {'relations': record['relations']},
        'similarity_score': record['avg_score1'],
        'source': 'graph_relation'
    }

def _process_chunk_result(record) -> Dict[str, Any]:
    return {
        'content': f"Fragment tekstu: {record['chunk_text']}",
        'metadata': {},
        'similarity_score': record['score'],
        'source': 'chunk_text'
    }

# Don't forget to import combinations
from itertools import combinations
