# main_api.py

"""
Main API Module
===============
This module defines the FastAPI application with endpoints for uploading files, querying knowledge,
and managing flashcards and decks. It includes processing for PDF and document files, chunking,
embedding, metadata extraction, knowledge graph creation, and CRUD operations for flashcards and decks.

Endpoints:
- `/upload/`: Upload a file and process it.
- `/query/`: Query the knowledge base and get answers.
- `/decks/`: CRUD operations for decks.
- `/decks/{deck_id}/flashcards/`: CRUD operations for flashcards within a deck.

Dependencies:
- FastAPI
- SQLAlchemy
- Pydantic
- SentenceTransformer
- Torch
- Uvicorn
- Requests
"""

# Load environment variables
from dotenv import load_dotenv

load_dotenv()

# # Importing custom modules
from src.graph_store import create_graph_entries, create_entity_relationships
from src.vector_store import create_vector_store
from src.metadata_extraction import MetadataExtractor
from file_processor.pdf_processor import PDFProcessor
from file_processor.documents_processor import DocumentProcessor
from src.agent.agent import agent_response
from src.chunking import create_chunks
from src.models import Deck, Flashcard  # Ensure all models are imported
from src.database import SessionLocal, engine, Base

# Import additional modules for CRUD operations
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session  # Correct import for Session
from sentence_transformers import SentenceTransformer
import uvicorn
import logging
import os
import aiofiles
from pathlib import Path
import asyncio

# ----------------- Pydantic Models -----------------

class FlashcardBase(BaseModel):
    question: str
    answer: str


class FlashcardCreate(FlashcardBase):
    pass


class FlashcardRead(FlashcardBase):
    id: int
    deck_id: int

    class Config:
        from_attributes = True


class DeckBase(BaseModel):
    name: str
    description: Optional[str] = None


class DeckCreate(DeckBase):
    pass


class DeckRead(DeckBase):
    id: int
    flashcards: List[FlashcardRead] = []

    class Config:
        from_attributes = True


class UploadResponse(BaseModel):
    message: str
    user_id: str
    file_name: str
    file_description: Optional[str]
    category: Optional[str]


class QueryResponse(BaseModel):
    user_id: str
    query: str
    answer: str

# ---------------------------------------------------

# Initialize FastAPI app
app = FastAPI(
    title="RAG Knowledge Base API",
    description="API for uploading documents, querying a knowledge base using RAG, and managing flashcards and decks.",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Update with your frontend's URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Set to DEBUG for more detailed logs
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize file processors
pdf_processor = PDFProcessor()
document_processor = DocumentProcessor()

# Initialize the embedding model once at module level for performance
EMBEDDING_MODEL_NAME = os.getenv('EMBEDDING_MODEL_NAME', 'all-MiniLM-L6-v2')
try:
    embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    logger.info(f"Initialized embedding model: {EMBEDDING_MODEL_NAME}")
except Exception as e:
    logger.error(f"Failed to initialize embedding model '{EMBEDDING_MODEL_NAME}': {e}")
    raise

# Load API keys
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
if not ANTHROPIC_API_KEY:
    raise ValueError("Anthropic API key is not set. Please set the ANTHROPIC_API_KEY environment variable.")

TAVILY_API_KEY = os.getenv('TAVILY_API_KEY')
if not TAVILY_API_KEY:
    raise ValueError("Tavily API key is not set. Please set the TAVILY_API_KEY environment variable.")

# ----------------- Dependency to get DB session -----------------

def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ----------------- Event Handlers -----------------

@app.on_event("startup")
def on_startup():
    # Import all models to ensure they are registered with SQLAlchemy before creating tables
    from src.models import Deck, Flashcard  # Ensure all models are imported
    Base.metadata.create_all(bind=engine)
    logger.info("All tables are created on startup.")
    # Additional startup logic (e.g., initializing ML models) can be added here


@app.on_event("shutdown")
def on_shutdown():
    # Add shutdown logic here if needed
    logger.info("Application is shutting down.")

# ----------------- Endpoints -----------------

# Endpoint to check health
@app.get("/health")
async def health_check():
    logger.info("Health check endpoint was called.")
    return {"status": "OK"}


# Root endpoint
@app.get("/")
def read_root():
    return {"Hello": "World"}


# Upload Endpoint
@app.post("/upload/", response_model=UploadResponse)
async def upload_file(
        user_id: str = Form(..., description="Unique identifier for the user."),
        file_description: Optional[str] = Form(None, description="Description of the uploaded file."),
        category: Optional[str] = Form(None, description="Category of the document."),
        start_page: Optional[int] = Form(None, description="Starting page number for PDF processing."),
        end_page: Optional[int] = Form(None, description="Ending page number for PDF processing."),
        file: UploadFile = File(..., description="The file to be uploaded and processed."),
        db: Session = Depends(get_db)
):
    """
    Upload Endpoint
    ---------------
    Handles file uploads, processes the content, generates embeddings, extracts metadata,
    updates the knowledge graph, and stores relevant information in the database.
    """
    logger.info(f"Received upload request from user_id: {user_id} for file: {file.filename}")

    # Validate and set default values for start_page and end_page
    if start_page is None:
        start_page = 0
    if end_page is not None and end_page < 0:
        logger.error("end_page must be a non-negative integer.")
        raise HTTPException(status_code=400, detail="end_page must be a non-negative integer.")

    # Save the uploaded file
    upload_dir = "uploads"

    # Check if 'uploads' path exists
    if os.path.exists(upload_dir):
        if not os.path.isdir(upload_dir):
            logger.error(f"Upload path '{upload_dir}' exists and is not a directory.")
            raise HTTPException(status_code=500, detail=f"Upload path '{upload_dir}' exists and is not a directory.")
    else:
        try:
            os.makedirs(upload_dir)
            logger.info(f"Created upload directory at '{upload_dir}'.")
        except Exception as e:
            logger.error(f"Failed to create upload directory '{upload_dir}': {e}")
            raise HTTPException(status_code=500, detail=f"Failed to create upload directory: {str(e)}")

    # Ensure filename is secure
    safe_filename = Path(file.filename).name  # Extracts the filename without any path components

    file_path = os.path.join(upload_dir, safe_filename)

    try:
        content = await file.read()
        # Save the uploaded file asynchronously
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)
        logger.info(f"Saved uploaded file: {safe_filename} to {file_path}")
    except Exception as e:
        logger.error(f"Failed to save uploaded file: {safe_filename}. Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {str(e)}")

    # Determine file type and process file
    file_extension = os.path.splitext(safe_filename)[1].lower()
    logger.info(f"Determined file type: {file_extension} for file: {safe_filename}")

    try:
        if file_extension == '.txt':
            async with aiofiles.open(file_path, "r") as f:
                text_content = await f.read()
        elif file_extension == '.pdf':
            text_content = await asyncio.to_thread(pdf_processor.process_pdf, file_path, start_page=start_page, end_page=end_page)
        elif file_extension in ['.docx', '.odt', '.rtf']:
            text_content = await asyncio.to_thread(document_processor.process_document, file_path)
        else:
            logger.error(f"Unsupported file type: {file_extension}")
            raise ValueError(f"Unsupported file type: {file_extension}")

        if not text_content:
            logger.error("Failed to extract text from the document.")
            raise ValueError("Failed to extract text from the document.")

        logger.info(f"Extracted text from file: {safe_filename}")
    except Exception as e:
        logger.error(f"Error processing file: {safe_filename}. Error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    # Chunking the text
    try:
        chunks = await asyncio.to_thread(create_chunks, text_content)
        if not chunks:
            logger.error("Failed to create text chunks from the document.")
            raise ValueError("Failed to create text chunks from the document.")
        logger.info(f"Created {len(chunks)} chunks from file: {safe_filename}")
    except Exception as e:
        logger.error(f"Error creating chunks from file: {safe_filename}. Error: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating chunks: {str(e)}")

    # Generate embeddings using batch encoding
    try:
        embeddings = await asyncio.to_thread(embedding_model.encode, chunks, 32, False)
        if len(embeddings) != len(chunks):
            logger.warning(f"Number of embeddings ({len(embeddings)}) does not match number of chunks ({len(chunks)})")
        logger.info(f"Generated embeddings for chunks from file: {safe_filename}")
    except Exception as e:
        logger.error(f"Error generating embeddings: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating embeddings: {str(e)}")

    # Initialize the MetadataExtractor
    metadata_extractor = MetadataExtractor()

    # Extract metadata using LLM
    try:
        # Use asyncio.gather to perform metadata extraction in parallel
        extracted_metadatas = await asyncio.gather(*[
            asyncio.to_thread(metadata_extractor.extract_metadata, chunk, category) for chunk in chunks
        ])
        logger.info(f"Extracted metadata for chunks from file: {safe_filename}")
    except Exception as e:
        logger.error(f"Error extracting metadata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error extracting metadata: {str(e)}")

    # Create vector store (after metadata extraction)
    try:
        await asyncio.to_thread(create_vector_store, chunks, embeddings, user_id, file_description, category, extracted_metadatas)
        logger.info(f"Vector store updated for user_id: {user_id}")
    except Exception as e:
        logger.error(f"Error creating/updating vector store: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating/updating vector store: {str(e)}")

    # Create graph entries (nodes and relationships)
    try:
        await asyncio.to_thread(create_graph_entries, chunks, extracted_metadatas, user_id)
        await asyncio.to_thread(create_entity_relationships, extracted_metadatas, user_id)
        logger.info(f"Knowledge graph updated for user_id: {user_id}")
    except Exception as e:
        logger.error(f"Error creating knowledge graph: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating knowledge graph: {str(e)}")

    # Optionally, store the uploaded file info in the database (Decks and Flashcards)
    # This part can be customized based on how you want to associate uploads with decks/flashcards
    # For example, creating a new Deck from the uploaded file
    try:
        new_deck = Deck(name=safe_filename, description=file_description)
        db.add(new_deck)
        db.commit()
        db.refresh(new_deck)
        logger.info(f"Created new deck with ID {new_deck.id} from uploaded file.")

        # Optionally, create flashcards based on chunks or other logic
        # This part depends on your application's requirements
        # For demonstration, let's assume each chunk can be a flashcard
        for idx, chunk in enumerate(chunks, start=1):
            question = f"Flashcard {idx}: {chunk[:50]}..."  # Example question
            answer = extracted_metadatas[idx - 1].get('summary', 'No answer provided.')  # Example answer
            new_flashcard = Flashcard(question=question, answer=answer, deck_id=new_deck.id)
            db.add(new_flashcard)
        db.commit()
        logger.info(f"Created {len(chunks)} flashcards for deck ID {new_deck.id}.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating deck and flashcards in database: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating deck and flashcards: {str(e)}")

    # Return a success message
    return UploadResponse(
        message="File processed successfully. Metadata and knowledge graph extracted successfully.",
        user_id=user_id,
        file_name=safe_filename,
        file_description=file_description,
        category=category
    )

# Define CRUD endpoints for Decks and Flashcards

# Endpoint to create a new deck
@app.post("/decks/", response_model=DeckRead, status_code=status.HTTP_201_CREATED)
async def create_deck(deck: DeckCreate, db: Session = Depends(get_db)):
    """
    Create a new Deck
    -----------------
    Creates a new deck with the provided name and description.
    """
    logger.info(f"Creating a new deck with name: {deck.name}")
    try:
        existing_deck = db.query(Deck).filter(Deck.name == deck.name).first()
        if existing_deck:
            logger.error(f"Deck with name '{deck.name}' already exists.")
            raise HTTPException(status_code=400, detail="Deck with this name already exists.")

        new_deck = Deck(name=deck.name, description=deck.description)
        db.add(new_deck)
        db.commit()
        db.refresh(new_deck)
        logger.info(f"Created new deck with ID {new_deck.id}")
        return new_deck
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating deck: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating deck: {str(e)}")

# Endpoint to get all decks
@app.get("/decks/", response_model=List[DeckRead])
async def get_decks(db: Session = Depends(get_db)):
    """
    Get All Decks
    ------------
    Retrieves a list of all decks along with their flashcards.
    """
    logger.info("Fetching all decks.")
    try:
        decks = db.query(Deck).all()
        return decks
    except Exception as e:
        logger.error(f"Error fetching decks: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching decks: {str(e)}")

# Endpoint to get a specific deck by ID
@app.get("/decks/{deck_id}/", response_model=DeckRead)
async def get_deck(deck_id: int, db: Session = Depends(get_db)):
    """
    Get a Deck by ID
    ----------------
    Retrieves a specific deck by its ID along with its flashcards.
    """
    logger.info(f"Fetching deck with ID: {deck_id}")
    try:
        deck = db.query(Deck).filter(Deck.id == deck_id).first()
        if not deck:
            logger.error(f"Deck with ID {deck_id} not found.")
            raise HTTPException(status_code=404, detail="Deck not found.")
        return deck
    except Exception as e:
        logger.error(f"Error fetching deck: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching deck: {str(e)}")

# Endpoint to update a deck
@app.put("/decks/{deck_id}/", response_model=DeckRead)
async def update_deck(deck_id: int, deck: DeckCreate, db: Session = Depends(get_db)):
    """
    Update a Deck
    ------------
    Updates the name and/or description of an existing deck.
    """
    logger.info(f"Updating deck with ID: {deck_id}")
    try:
        existing_deck = db.query(Deck).filter(Deck.id == deck_id).first()
        if not existing_deck:
            logger.error(f"Deck with ID {deck_id} not found.")
            raise HTTPException(status_code=404, detail="Deck not found.")

        existing_deck.name = deck.name
        existing_deck.description = deck.description
        db.commit()
        db.refresh(existing_deck)
        logger.info(f"Updated deck with ID {deck_id}")
        return existing_deck
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating deck: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating deck: {str(e)}")

# Endpoint to delete a deck
@app.delete("/decks/{deck_id}/", response_model=DeckRead)
async def delete_deck(deck_id: int, db: Session = Depends(get_db)):
    """
    Delete a Deck
    ------------
    Deletes a deck and all its associated flashcards.
    """
    logger.info(f"Deleting deck with ID: {deck_id}")
    try:
        deck = db.query(Deck).filter(Deck.id == deck_id).first()
        if not deck:
            logger.error(f"Deck with ID {deck_id} not found.")
            raise HTTPException(status_code=404, detail="Deck not found.")

        db.delete(deck)
        db.commit()
        logger.info(f"Deleted deck with ID {deck_id}")
        return deck
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting deck: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting deck: {str(e)}")

# Endpoint to add flashcards to a deck
@app.post("/decks/{deck_id}/flashcards/", response_model=List[FlashcardRead], status_code=status.HTTP_201_CREATED)
async def add_flashcards(deck_id: int, flashcards: List[FlashcardCreate], db: Session = Depends(get_db)):
    """
    Add Flashcards to a Deck
    ------------------------
    Adds one or more flashcards to a specific deck.
    """
    logger.info(f"Adding {len(flashcards)} flashcards to deck ID: {deck_id}")
    try:
        deck = db.query(Deck).filter(Deck.id == deck_id).first()
        if not deck:
            logger.error(f"Deck with ID {deck_id} not found.")
            raise HTTPException(status_code=404, detail="Deck not found.")

        new_flashcards = []
        for fc in flashcards:
            new_flashcard = Flashcard(question=fc.question, answer=fc.answer, deck_id=deck_id)
            db.add(new_flashcard)
            new_flashcards.append(new_flashcard)

        db.commit()

        # Refresh flashcards to get their IDs
        for fc in new_flashcards:
            db.refresh(fc)

        logger.info(f"Added {len(new_flashcards)} flashcards to deck ID {deck_id}")
        return new_flashcards
    except Exception as e:
        db.rollback()
        logger.error(f"Error adding flashcards to deck: {e}")
        raise HTTPException(status_code=500, detail=f"Error adding flashcards: {str(e)}")

# Endpoint to get flashcards from a deck
@app.get("/decks/{deck_id}/flashcards/", response_model=List[FlashcardRead])
async def get_flashcards(deck_id: int, db: Session = Depends(get_db)):
    """
    Get Flashcards from a Deck
    --------------------------
    Retrieves all flashcards associated with a specific deck.
    """
    logger.info(f"Fetching flashcards for deck ID: {deck_id}")
    try:
        deck = db.query(Deck).filter(Deck.id == deck_id).first()
        if not deck:
            logger.error(f"Deck with ID {deck_id} not found.")
            raise HTTPException(status_code=404, detail="Deck not found.")

        flashcards = db.query(Flashcard).filter(Flashcard.deck_id == deck_id).all()
        logger.info(f"Fetched {len(flashcards)} flashcards for deck ID {deck_id}")
        return flashcards
    except Exception as e:
        logger.error(f"Error fetching flashcards: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching flashcards: {str(e)}")

# Endpoint to delete a flashcard
@app.delete("/flashcards/{flashcard_id}/", response_model=FlashcardRead)
async def delete_flashcard(flashcard_id: int, db: Session = Depends(get_db)):
    """
    Delete a Flashcard
    ------------------
    Deletes a specific flashcard by its ID.
    """
    logger.info(f"Deleting flashcard with ID: {flashcard_id}")
    try:
        flashcard = db.query(Flashcard).filter(Flashcard.id == flashcard_id).first()
        if not flashcard:
            logger.error(f"Flashcard with ID {flashcard_id} not found.")
            raise HTTPException(status_code=404, detail="Flashcard not found.")

        db.delete(flashcard)
        db.commit()
        logger.info(f"Deleted flashcard with ID {flashcard_id}")
        return flashcard
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting flashcard: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting flashcard: {str(e)}")

# Endpoint to update a flashcard
@app.put("/flashcards/{flashcard_id}/", response_model=FlashcardRead)
async def update_flashcard(flashcard_id: int, flashcard: FlashcardCreate, db: Session = Depends(get_db)):
    """
    Update a Flashcard
    ------------------
    Updates the question and/or answer of an existing flashcard.
    """
    logger.info(f"Updating flashcard with ID: {flashcard_id}")
    try:
        existing_flashcard = db.query(Flashcard).filter(Flashcard.id == flashcard_id).first()
        if not existing_flashcard:
            logger.error(f"Flashcard with ID {flashcard_id} not found.")
            raise HTTPException(status_code=404, detail="Flashcard not found.")

        existing_flashcard.question = flashcard.question
        existing_flashcard.answer = flashcard.answer
        db.commit()
        db.refresh(existing_flashcard)
        logger.info(f"Updated flashcard with ID {flashcard_id}")
        return existing_flashcard
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating flashcard: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating flashcard: {str(e)}")

# Query Endpoint
@app.post("/query/", response_model=QueryResponse)
async def query_knowledge(
        user_id: str = Form(..., description="Unique identifier for the user."),
        query: str = Form(..., description="The user's query to the knowledge base.")
):
    """
    Query Endpoint
    --------------
    Handles user queries by retrieving relevant information and generating answers using the knowledge base.
    """
    logger.info(f"Received query from user_id: {user_id} - '{query}'")
    try:
        # Generowanie odpowiedzi może być blokujące, więc uruchamiamy to w osobnym wątku
        answer = await asyncio.to_thread(
            agent_response,
            user_id,
            query,
            model_name="claude-3-haiku-20240307",
            anthropic_api_key=ANTHROPIC_API_KEY,
            tavily_api_key=TAVILY_API_KEY
        )
        logger.info(f"Generated answer for user_id: {user_id} with query: '{query}'")
        print(answer)
        return QueryResponse(
            user_id=user_id,
            query=query,
            answer=answer
        )
    except Exception as e:
        logger.error(f"Error generating answer for user_id: {user_id}, query '{query}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating answer: {str(e)}")

# ----------------- Run the Application -----------------

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8043)
