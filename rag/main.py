# main.py

import os
import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Importuj modele i bazę danych
from src.models import Base, ORMFile, Deck, Flashcard, Conversation, Message  # Dodano Conversation i Message
from src.routers import files, decks, flashcards, query, chats  # Dodano 'chats'
from src.database import engine

# Inicjalizacja logowania
logging.basicConfig(
    level=logging.INFO,  # Ustaw na DEBUG dla bardziej szczegółowych logów
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Inicjalizacja bazy danych
Base.metadata.create_all(bind=engine)
logger.info("Database tables created.")

# Inicjalizacja FastAPI aplikacji
app = FastAPI(
    title="RAG Knowledge Base API",
    description="API for uploading documents, querying a knowledge base using RAG, and managing flashcards, decks, and chats.",
    version="1.0.0"
)

# Dodanie CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Zaktualizuj URL frontend jeśli potrzebne
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

# Uruchomienie aplikacji
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8043, reload=True)
