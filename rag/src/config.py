# Configuration settings

# ChromaDB settings
CHROMA_DB_IMPL = "sqlite"
PERSIST_DIRECTORY = "./vector_store_data"

# Neo4j settings
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "password"

# Embedding model
EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2'

# Ollama LLM model
LLM_MODEL_NAME = "llama3.2:3b-instruct-fp16"