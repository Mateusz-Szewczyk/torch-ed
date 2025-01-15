# main.py

import os
import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import base64
from werkzeug.middleware.proxy_fix import ProxyFix  # Import ProxyFix

from src.routers import files, decks, flashcards, query, chats, exams, study_sessions, user_flashcards, dashboard
from src.config import Config

def load_private_keys():
    prp_key_base64 = os.getenv("PUP_KEY")

    if prp_key_base64:
        prp_key = base64.b64decode(prp_key_base64).decode('utf-8')
        with open(Config.PUP_PATH, "w") as f:
            f.write(prp_key)
    else:
        raise ValueError("PUP_KEY environment variable is missing!")

load_private_keys()

# Inicjalizacja logowania
logging.basicConfig(
    level=logging.INFO,  # Ustaw na DEBUG dla bardziej szczegółowych logów
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Inicjalizacja FastAPI aplikacji
app = FastAPI(
    title="RAG Knowledge Base API",
    description="API for uploading documents, querying a knowledge base using RAG, and managing flashcards, decks, and chats.",
    version="1.0.0"
)

# Dodanie ProxyFix middleware
app.add_middleware(ProxyFix, x_proto=1, x_host=1)

# Dodanie CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://torch-9vlkoolu7-mateusz-szewczyks-projects.vercel.app",
        "https://torch-ed.vercel.app",
        "https://torched.pl"
    ],  # Zaktualizuj URL frontend jeśli potrzebne
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Event Handlers
@app.on_event("startup")
def on_startup():
    logger.info("Application startup complete.")

@app.on_event("shutdown")
def on_shutdown():
    logger.info("Application is shutting down.")

# Endpoint zdrowia
@app.get("/health")
async def health_check():
    logger.info("Health check endpoint was called.")
    return {"status": "OK"}

# Root endpoint
@app.get("/")
def read_root():
    return {"Hello": "World"}

# Includowanie routerów
app.include_router(files.router, prefix="/api/files", tags=["Files"])
app.include_router(decks.router, prefix="/api/decks", tags=["Decks"])
app.include_router(flashcards.router, prefix="/api/flashcards", tags=["Flashcards"])
app.include_router(query.router, prefix="/api/query", tags=["Query"])
app.include_router(chats.router, prefix="/api/chats", tags=["Chats"])
app.include_router(exams.router, prefix="/api/exams", tags=["Exams"])
app.include_router(study_sessions.router, prefix="/api/study_sessions", tags=["Study Sessions"])
app.include_router(user_flashcards.router, prefix="/api/user_flashcards", tags=["User Flashcards"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])

# Uruchomienie aplikacji
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8043, reload=True)
