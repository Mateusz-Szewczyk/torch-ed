# config.py

import os

# ChromaDB settings
# Local development: uses persist_directory
# Production (Railway): uses remote ChromaDB server via CHROMA_HOST/CHROMA_PORT

# Check if we're using remote ChromaDB (Railway production)
CHROMA_HOST = os.getenv('CHROMA_HOST', None)  # e.g., "chromadb.railway.internal" or public domain
CHROMA_PORT = os.getenv('CHROMA_PORT', '8000')

# For Railway: use private URL if available, otherwise fall back to public
CHROMA_PRIVATE_URL = os.getenv('CHROMA_PRIVATE_URL', None)  # http://chromadb.railway.internal
CHROMA_PUBLIC_URL = os.getenv('CHROMA_PUBLIC_URL', None)    # https://chromadb-xxx.up.railway.app

# Determine if we're using remote ChromaDB
USE_REMOTE_CHROMA = bool(CHROMA_HOST or CHROMA_PRIVATE_URL or CHROMA_PUBLIC_URL)

# Local persist directory (only used when not using remote ChromaDB)
PERSIST_DIRECTORY = os.getenv('PERSIST_DIRECTORY', "/app/vector_store_data")

# Neo4j settings
NEO4J_URI = os.getenv('NEO4J_URI', "bolt://localhost:7687")
NEO4J_USERNAME = os.getenv('NEO4J_USERNAME', "neo4j")
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', "password")

# LLM model
LLM_MODEL_NAME = os.getenv('LLM_MODEL_NAME', "claude-3-haiku-20240307")


def get_chroma_client_settings():
    """
    Returns the appropriate ChromaDB client configuration.
    For local: returns persist_directory
    For production: returns host/port for HTTP client
    """
    if USE_REMOTE_CHROMA:
        # Prefer private URL (internal Railway network), then public, then host:port
        if CHROMA_PRIVATE_URL:
            # Extract host from URL like "http://chromadb.railway.internal"
            url = CHROMA_PRIVATE_URL.rstrip('/')
            if url.startswith('http://'):
                host = url[7:]  # Remove http://
            elif url.startswith('https://'):
                host = url[8:]  # Remove https://
            else:
                host = url
            return {
                'mode': 'remote',
                'host': host,
                'port': int(CHROMA_PORT),
                'ssl': False  # Internal Railway network doesn't need SSL
            }
        elif CHROMA_PUBLIC_URL:
            url = CHROMA_PUBLIC_URL.rstrip('/')
            if url.startswith('https://'):
                host = url[8:]
                return {
                    'mode': 'remote',
                    'host': host,
                    'port': 443,
                    'ssl': True
                }
            elif url.startswith('http://'):
                host = url[7:]
                return {
                    'mode': 'remote',
                    'host': host,
                    'port': int(CHROMA_PORT),
                    'ssl': False
                }
        elif CHROMA_HOST:
            return {
                'mode': 'remote',
                'host': CHROMA_HOST,
                'port': int(CHROMA_PORT),
                'ssl': False
            }

    # Local development mode
    return {
        'mode': 'local',
        'persist_directory': PERSIST_DIRECTORY
    }


class Config:
    PUP_PATH: str = "pup_key.pem"
