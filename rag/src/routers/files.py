# routers/files.py

from fastapi import APIRouter, HTTPException, Depends, Form, File, UploadFile
from fastapi_cache.decorator import cache
from pix2text.utils import overlap
from sqlalchemy.orm import Session
from typing import List

from ..models import ORMFile, User
from ..schemas import (
    UploadResponse,
    UploadedFileRead,
    DeleteKnowledgeRequest,
    DeleteKnowledgeResponse,
)
from ..dependencies import get_db
from ..auth import get_current_user
from ..vector_store import delete_file_from_vector_store, create_vector_store
from ..file_processor.pdf_processor import PDFProcessor
from ..file_processor.documents_processor import DocumentProcessor
from ..chunking import create_chunks

import os
from pathlib import Path
import aiofiles
import asyncio
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# Inicjalizacja procesorów plików
pdf_processor = PDFProcessor()
document_processor = DocumentProcessor()

# Inicjalizacja modelu embedującego
from langchain_openai import OpenAIEmbeddings
try:
    embedding_model = OpenAIEmbeddings(model="text-embedding-3-large")
except Exception as e:
    raise

@router.post("/upload/", response_model=UploadResponse)
async def upload_file(
    file_description: str = Form(None, description="Description of the uploaded file."),
    category: str = Form(None, description="Category of the document."),
    start_page: int = Form(None, description="Starting page number for PDF processing."),
    end_page: int = Form(None, description="Ending page number for PDF processing."),
    file: UploadFile = File(..., description="The file to be uploaded and processed."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_id = str(current_user.id_)
    logger.info(f"Received upload request from user_id: {user_id} for file: {file.filename}")

    if start_page is None:
        start_page = 0
    if end_page is not None and end_page < 0:
        logger.error("end_page must be a non-negative integer.")
        raise HTTPException(status_code=400, detail="end_page must be a non-negative integer.")

    upload_dir = "uploads"
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
        logger.info(f"Created upload directory at '{upload_dir}'.")

    safe_filename = Path(file.filename).name
    existing_file = db.query(ORMFile).filter(ORMFile.user_id == user_id, ORMFile.name == safe_filename).first()
    if existing_file:
        logger.error(f"File with name '{safe_filename}' already exists for user_id: {user_id}.")
        raise HTTPException(status_code=400, detail="File with this name already exists.")

    file_path = os.path.join(upload_dir, safe_filename)

    try:
        content = await file.read()
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)
        logger.info(f"Saved uploaded file: {safe_filename} to {file_path}")

        file_extension = os.path.splitext(safe_filename)[1].lower()
        logger.info(f"Determined file type: {file_extension} for file: {safe_filename}")

        if file_extension == '.txt':
            async with aiofiles.open(file_path, "r", encoding='utf-8') as f:
                text_content = await f.read()
        elif file_extension == '.pdf':
            text_content = await asyncio.to_thread(pdf_processor.process_pdf, file_path, start_page=start_page, end_page=end_page)
        elif file_extension in ['.docx', '.odt', '.rtf']:
            text_content = await asyncio.to_thread(document_processor.process_document, file_path)
        else:
            logger.error(f"Unsupported file type: {file_extension}")
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_extension}")

        if not text_content:
            logger.error("Failed to extract text from the document.")
            raise HTTPException(status_code=400, detail="Failed to extract text from the document.")

        chunks = await asyncio.to_thread(create_chunks, text_content, chunk_size=400, overlap=100)
        if not chunks:
            logger.error("Failed to create text chunks from the document.")
            raise HTTPException(status_code=500, detail="Failed to create text chunks from the document.")

        await asyncio.to_thread(
            create_vector_store,
            chunks=chunks,
            user_id=user_id,
            file_name=safe_filename,
            file_description=file_description,
            category=category,
        )
        logger.info(f"Vector store updated for user_id: {user_id}")

        new_file = ORMFile(
            user_id=user_id,
            name=safe_filename,
            category=category if category else "Uncategorized",
            description=file_description
        )
        db.add(new_file)
        db.commit()
        db.refresh(new_file)
        logger.info(f"Saved file record to database: {new_file}")

        uploaded_files = [
            UploadedFileRead(
                id=new_file.id,
                name=new_file.name,
                description=new_file.description,
                category=new_file.category,
                created_at=new_file.created_at.isoformat()
            )
        ]

        return UploadResponse(
            message="File processed successfully.",
            user_id=user_id,
            file_name=safe_filename,
            file_description=file_description,
            category=category,
            uploaded_files=uploaded_files
        )

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Unexpected error during file upload and processing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred during file processing.")
    finally:
        if os.path.exists(file_path):
            try:
                await asyncio.to_thread(os.remove, file_path)
                logger.info(f"Deleted uploaded file: {safe_filename} from {file_path}")
            except Exception as e:
                logger.error(f"Failed to delete uploaded file: {safe_filename}. Error: {e}")

@cache(expire=300)
@router.get("/list/", response_model=List[UploadedFileRead])
async def list_uploaded_files(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_id = str(current_user.id_)
    logger.info(f"Fetching uploaded files for user_id: {user_id}")
    try:
        files = db.query(ORMFile).filter(ORMFile.user_id == user_id).all()
        uploaded_files = [
            UploadedFileRead(
                id=file.id,
                name=file.name,
                description=file.description,
                category=file.category,
                created_at=file.created_at.isoformat(),
            )
            for file in files
        ]
        return uploaded_files
    except Exception as e:
        logger.error(f"Error fetching uploaded files: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching uploaded files: {str(e)}")

@router.delete("/delete-file/", response_model=DeleteKnowledgeResponse)
async def delete_knowledge(
    request: DeleteKnowledgeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_id = str(current_user.id_)
    file_name = request.file_name

    deleted_from_vector_store = delete_file_from_vector_store(user_id, file_name)
    if not deleted_from_vector_store:
        logger.warning(f"Could not delete vectors for file: {file_name} from vector store.")

    # Usunięcie rekordu z bazy danych
    try:
        file_record = db.query(ORMFile).filter(ORMFile.user_id == user_id, ORMFile.name == file_name).first()
        if file_record:
            db.delete(file_record)
            db.commit()
            logger.info(f"Deleted file record from database: {file_record}")
        else:
            logger.warning(f"No file record found in database for user_id: {user_id}, file_name: {file_name}")
            # Mimo braku rekordu w DB, wektory mogły istnieć, więc kontynuujemy
    except Exception as e:
        logger.error(f"Error deleting file record from database: {e}")
        raise HTTPException(status_code=500, detail="Error deleting file record from database.")

    return DeleteKnowledgeResponse(
        message="Deletion process completed.",
        deleted_from_vector_store=deleted_from_vector_store
    )