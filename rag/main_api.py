# main_api.py

"""
Main API Module
==============
This module defines the FastAPI application with endpoints for uploading files and querying knowledge.
It includes processing for PDF and document files, chunking, embedding, metadata extraction, and knowledge graph creation.

Endpoints:
- `/upload/`: Upload a file and process it.
- `/query/`: Query the knowledge base and get answers.

Dependencies:
- FastAPI
- SentenceTransformer
- Pydantic
- Torch
- Uvicorn
- Requests
"""

import os
from typing import Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
import uvicorn
import logging

# Importing custom modules
from src.graph_store import create_graph_entries, create_entity_relationships
from src.vector_store import create_vector_store
from src.metadata_extraction import MetadataExtractor
from file_processor.pdf_processor import PDFProcessor
from file_processor.documents_processor import DocumentProcessor
from src.agent.agent import agent_response
from src.chunking import create_chunks

# Initialize FastAPI app
app = FastAPI(
    title="RAG Knowledge Base API",
    description="API for uploading documents and querying a knowledge base using RAG.",
    version="1.0.0"
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

# Define a response model for the upload endpoint
class UploadResponse(BaseModel):
    message: str
    user_id: str
    file_name: str
    file_description: Optional[str]
    category: Optional[str]


@app.get("/health")
async def health_check():
    return {"status": "OK"}


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.post("/upload/", response_model=UploadResponse)
async def upload_file(
    user_id: str = Form(..., description="Unique identifier for the user."),
    file_description: Optional[str] = Form(None, description="Description of the uploaded file."),
    category: Optional[str] = Form(None, description="Category of the document."),
    start_page: Optional[int] = Form(None, description="Starting page number for PDF processing."),
    end_page: Optional[int] = Form(None, description="Ending page number for PDF processing."),
    file: UploadFile = File(..., description="The file to be uploaded and processed.")
):
    """
    Upload Endpoint
    ---------------
    Handles file uploads, processes the content, generates embeddings, extracts metadata, and updates the knowledge graph.
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
    from pathlib import Path
    safe_filename = Path(file.filename).name  # Extracts the filename without any path components

    file_path = os.path.join(upload_dir, safe_filename)

    try:
        content = await file.read()
        # Save the uploaded file asynchronously
        import aiofiles
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
            text_content = pdf_processor.process_pdf(file_path, start_page=start_page, end_page=end_page)
        elif file_extension in ['.docx', '.odt', '.rtf']:
            text_content = document_processor.process_document(file_path)
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
        chunks = create_chunks(text_content)
        if not chunks:
            logger.error("Failed to create text chunks from the document.")
            raise ValueError("Failed to create text chunks from the document.")
        logger.info(f"Created {len(chunks)} chunks from file: {safe_filename}")
    except Exception as e:
        logger.error(f"Error creating chunks from file: {safe_filename}. Error: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating chunks: {str(e)}")

    # Generate embeddings using batch encoding
    try:
        embeddings = embedding_model.encode(chunks, batch_size=32, show_progress_bar=False)
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
        extracted_metadatas = [
            metadata_extractor.extract_metadata(chunk=chunk, category=category) for chunk in chunks
        ]
        logger.info(f"Extracted metadata for chunks from file: {safe_filename}")
    except Exception as e:
        logger.error(f"Error extracting metadata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error extracting metadata: {str(e)}")

    # Create vector store (after metadata extraction)
    try:
        create_vector_store(chunks, embeddings, user_id, file_description, category, extracted_metadatas)
        logger.info(f"Vector store updated for user_id: {user_id}")
    except Exception as e:
        logger.error(f"Error creating/updating vector store: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating/updating vector store: {str(e)}")

    # Create graph entries (nodes and relationships)
    try:
        create_graph_entries(chunks, extracted_metadatas, user_id)
        create_entity_relationships(extracted_metadatas, user_id)
        logger.info(f"Knowledge graph updated for user_id: {user_id}")
    except Exception as e:
        logger.error(f"Error creating knowledge graph: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating knowledge graph: {str(e)}")

    # Return a success message
    return UploadResponse(
        message="File processed successfully. Metadata and knowledge graph extracted successfully.",
        user_id=user_id,
        file_name=safe_filename,
        file_description=file_description,
        category=category
    )


class QueryResponse(BaseModel):
    user_id: str
    query: str
    answer: str

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
        # Generate the answer using the answer generator module
        answer = agent_response(user_id, query, max_iterations=2, max_generated_passages=5)
        logger.info(f"Generated answer for user_id: {user_id} with query: '{query}'")
        return QueryResponse(
            user_id=user_id,
            query=query,
            answer=answer
        )
    except Exception as e:
        logger.error(f"Error generating answer for user_id: {user_id}, query '{query}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating answer: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8042)
