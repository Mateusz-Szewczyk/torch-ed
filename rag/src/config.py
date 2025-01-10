# config.py

import os

# ChromaDB settings
CHROMA_DB_IMPL = "sqlite"
PERSIST_DIRECTORY = os.getenv('PERSIST_DIRECTORY', "/app/vector_store_data")

# Neo4j settings
NEO4J_URI = os.getenv('NEO4J_URI', "bolt://localhost:7687")
NEO4J_USERNAME = os.getenv('NEO4J_USERNAME', "neo4j")
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', "password")

# LLM model
LLM_MODEL_NAME = os.getenv('LLM_MODEL_NAME', "claude-3-haiku-20240307")

class Config:
    PUP_PATH: str = "pup_key.pem"
