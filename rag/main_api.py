# main_api.py

"""
Main API Module
===============

This module defines the FastAPI application with endpoints for uploading files and querying knowledge.
It includes processing for PDF and document files, chunking, embedding, metadata extraction, and knowledge graph creation.

Endpoints:
- `/upload/`: Upload a file and process it.
- `/query/`: Query the knowledge base and get answers.

Dependencies:
- FastAPI
- SentenceTransformer
- Tqdm
- Pydantic
"""

import os
from typing import Optional
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

from src.graph_store import create_graph_entries, create_entity_relationships
from src.vector_store import create_vector_store
from src.metadata_extraction import extract_metadata_using_llm
from file_processor.pdf_processor import PDFProcessor
from file_processor.documents_processor import DocumentProcessor
from src.answer_generator import generate_answer
from src.chunking import create_chunks

app = FastAPI()

# Initialize processors
pdf_processor = PDFProcessor()
doc_processor = DocumentProcessor()

# Define a response model (optional)
class UploadResponse(BaseModel):
    message: str
    user_id: str
    file_name: str
    file_description: Optional[str]
    category: Optional[str]

@app.post("/upload/")
async def upload_file(
    user_id: str = Form(...),
    file_description: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    start_page: Optional[str] = Form(None),
    end_page: Optional[str] = Form(None),
    file: UploadFile = File(...)
):
    # Save the uploaded file
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Determine file type
    file_extension = os.path.splitext(file.filename)[1].lower()

    # Convert start_page and end_page to integers if provided
    try:
        sp = int(start_page) if start_page else 0
        ep = int(end_page) if end_page else None
    except ValueError:
        return JSONResponse(
            status_code=400,
            content={
                "message": "Start page and end page must be integers.",
                "user_id": user_id,
                "file_name": file.filename
            }
        )

    # Process file based on type
    try:
        if file_extension == '.pdf':
            text_content = pdf_processor.process_pdf(file_path, start_page=sp, end_page=ep)

        elif file_extension in ['.docx', '.odt', '.rtf']:
            text_content = doc_processor.process_document(file_path)
        else:
            return JSONResponse(
                status_code=400,
                content={
                    "message": f"Unsupported file type: {file_extension}",
                    "user_id": user_id,
                    "file_name": file.filename
                }
            )

        if not text_content:
            return JSONResponse(
                status_code=500,
                content={
                    "message": "Failed to extract text from the document.",
                    "user_id": user_id,
                    "file_name": file.filename
                }
            )

        # Chunking the text
        chunks = create_chunks(text_content)
        embeddings = []
        extracted_metadatas = []

        # Initialize the embedding model
        embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

        # Use tqdm to track progress through the chunks
        for chunk in tqdm(chunks, desc="Processing chunks", unit="chunk"):
            # Generate embeddings
            embedding = embedding_model.encode(chunk)
            embeddings.append(embedding)

            # Extract metadata using LLM
            metadata = extract_metadata_using_llm(chunk, category)
            extracted_metadatas.append(metadata)

        # Create vector store (after metadata extraction)
        create_vector_store(chunks, embeddings, user_id, file_description, category, extracted_metadatas)

        # Create graph entries (nodes and relationships)
        create_graph_entries(chunks, extracted_metadatas, user_id)
        create_entity_relationships(extracted_metadatas, user_id)
        # Return a success message
        return JSONResponse(
            status_code=200,
            content={
                "message": "File processed successfully. Metadata and knowledge graph extracted successfully.",
                "user_id": user_id,
                "file_name": file.filename,
                "file_description": file_description,
                "category": category
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "message": f"Error processing file: {str(e)}",
                "user_id": user_id,
                "file_name": file.filename
            }
        )


@app.post("/query/")
async def query_knowledge(
    user_id: str = Form(...),
    query: str = Form(...)
):
    try:
        # Generate the answer
        answer = generate_answer(user_id, query)
        return JSONResponse(
            status_code=200,
            content={
                "user_id": user_id,
                "query": query,
                "answer": answer
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "message": f"Error generating answer: {str(e)}",
                "user_id": user_id,
                "query": query
            }
        )
