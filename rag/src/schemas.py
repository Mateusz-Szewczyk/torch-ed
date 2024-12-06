# src/schemas.py

from pydantic import BaseModel, validator, Field, field_validator
from typing import Optional, List
from datetime import datetime

class FlashcardBase(BaseModel):
    question: str
    answer: str

class FlashcardCreate(FlashcardBase):
    id: Optional[int] = None

    @validator('question', 'answer')
    def not_empty(cls, v):
        if not v.strip():
            raise ValueError('Cannot be empty')
        return v

class FlashcardRead(FlashcardBase):
    id: int
    deck_id: int

    class Config:
        orm_mode = True

class DeckBase(BaseModel):
    name: str
    description: Optional[str] = None

class DeckCreate(DeckBase):
    flashcards: List[FlashcardCreate]

    @validator('name')
    def name_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Deck name cannot be empty')
        return v

class DeckRead(DeckBase):
    id: int
    flashcards: List[FlashcardRead]

    class Config:
        orm_mode = True

class QueryRequest(BaseModel):
    user_id: str
    query: str
    conversation_id: int

class QueryResponse(BaseModel):
    user_id: str
    query: str
    answer: str

class UploadResponse(BaseModel):
    message: str
    uploaded_files: List['UploadedFileRead']  # Upewnij się, że UploadedFileRead jest poprawnie zdefiniowany
    user_id: str
    file_name: str
    file_description: Optional[str]
    category: Optional[str]

class UploadedFileRead(BaseModel):
    id: int
    name: str
    description: Optional[str] = None  # Opcjonalne pole

    class Config:
        orm_mode = True

class DeleteKnowledgeRequest(BaseModel):
    user_id: str
    file_name: str

class DeleteKnowledgeResponse(BaseModel):
    message: str
    deleted_from_vector_store: bool
    deleted_from_graph: bool

class ListFilesRequest(BaseModel):
    user_id: str

class ConversationBase(BaseModel):
    user_id: str
    title: Optional[str] = None  # Add this line

class ConversationCreate(ConversationBase):
    pass

class ConversationRead(ConversationBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True

class MessageCreate(BaseModel):
    sender: str
    text: str

class MessageRead(BaseModel):
    id: int
    conversation_id: int
    sender: str
    text: str
    created_at: datetime = datetime.now()

    class Config:
        orm_mode = True

class ConversationUpdate(BaseModel):
    title: Optional[str] = None

    @field_validator('title')
    def title_not_empty(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Title cannot be empty')
        return v