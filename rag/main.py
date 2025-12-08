import os
import logging
import uvicorn
import redis.asyncio as redis
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
import base64

from src.routers import (
    files, decks, flashcards, query, chats, exams,
    study_sessions, user_flashcards, dashboard
)
from src.config import Config


def load_private_keys():
    prp_key_base64 = os.getenv("PUP_KEY")
    if prp_key_base64:
        prp_key_bytes = base64.b64decode(prp_key_base64)
        with open(Config.PUP_PATH, "wb") as f:
            f.write(prp_key_bytes)
    else:
        raise ValueError("PUP_KEY environment variable is missing!")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    load_private_keys()

    # Initialize Redis for caching
    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        redis_client = redis.from_url(redis_url, encoding="utf-8", decode_responses=True)

        # Test Redis connection
        await redis_client.ping()

        # Initialize FastAPI Cache
        FastAPICache.init(RedisBackend(redis_client), prefix="fastapi-cache")

        logger.info("Application startup complete with Redis cache enabled.")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}. Running without cache.")
        # Initialize with in-memory cache as fallback
        from fastapi_cache.backends.inmemory import InMemoryBackend
        FastAPICache.init(InMemoryBackend(), prefix="fastapi-cache")

    yield

    # Shutdown
    try:
        if 'redis_client' in locals():
            await redis_client.close()
    except:
        pass
    logger.info("Application shutdown complete.")


# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="RAG Knowledge Base API",
    description="API for uploading documents, querying a knowledge base using RAG, and managing flashcards, decks, and chats.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware (first)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://torch-9vlkoolu7-mateusz-szewczyks-projects.vercel.app",
        "https://torch-ed.vercel.app",
        "https://torched.pl",
        "localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip middleware (last middleware to be applied first in processing)
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Simple error handling middleware
@app.middleware("http")
async def error_handling_middleware(request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger.error(f"Unhandled error in {request.method} {request.url}: {str(e)}")
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )


# Endpoints
@app.get("/health")
async def health_check():
    return {"status": "OK", "cache": "enabled" if FastAPICache.get_backend() else "disabled"}


@app.get("/")
async def read_root():
    return {
        "message": "RAG Knowledge Base API",
        "version": "1.0.0",
        "status": "running"
    }


# Cache management endpoints
@app.post("/api/cache/clear")
async def clear_cache():
    """Clear all cache"""
    try:
        backend = FastAPICache.get_backend()
        if backend:
            await backend.clear()
            return {"message": "Cache cleared successfully"}
        else:
            return {"message": "No cache backend available"}
    except Exception as e:
        logger.error(f"Cache clear error: {e}")
        return {"error": "Failed to clear cache"}


# Include routers
app.include_router(files.router, prefix="/api/files", tags=["Files"])
app.include_router(decks.router, prefix="/api/decks", tags=["Decks"])
app.include_router(flashcards.router, prefix="/api/flashcards", tags=["Flashcards"])
app.include_router(query.router, prefix="/api/query", tags=["Query"])
app.include_router(chats.router, prefix="/api/chats", tags=["Chats"])
app.include_router(exams.router, prefix="/api/exams", tags=["Exams"])
app.include_router(study_sessions.router, prefix="/api/study_sessions", tags=["Study Sessions"])
app.include_router(user_flashcards.router, prefix="/api/user_flashcards", tags=["User Flashcards"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8043,
        reload=True,
        access_log=False  # Disable access logs for cleaner output
    )
