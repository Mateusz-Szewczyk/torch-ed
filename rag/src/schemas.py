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
    question: str
    answer: str
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
    name: str
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
    category: str

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



class ExamAnswerCreate(BaseModel):
    text: str = Field(..., example="3.14")
    is_correct: bool = Field(..., example=True)

class ExamAnswerRead(ExamAnswerCreate):
    id: int

    class Config:
        orm_mode = True

class ExamQuestionCreate(BaseModel):
    text: str = Field(..., example="Jaka jest wartość liczby pi?")
    answers: List[ExamAnswerCreate]

    @validator('answers')
    def validate_answers(cls, v):
        if len(v) != 4:
            raise ValueError("Każde pytanie musi mieć dokładnie 4 odpowiedzi.")
        correct_answers = [answer for answer in v if answer.is_correct]
        if len(correct_answers) != 1:
            raise ValueError("Każde pytanie musi mieć dokładnie jedną poprawną odpowiedź.")
        return v

class ExamQuestionRead(BaseModel):
    id: int
    text: str
    answers: List[ExamAnswerRead]

    class Config:
        orm_mode = True

class ExamCreate(BaseModel):
    name: str = Field(..., example="Egzamin z Matematyki")
    description: Optional[str] = Field(None, example="Egzamin końcowy z matematyki.")
    questions: List[ExamQuestionCreate]

    @validator('questions')
    def validate_questions(cls, v):
        if len(v) == 0:
            raise ValueError("Egzamin musi zawierać przynajmniej jedno pytanie.")
        return v

class ExamRead(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: datetime
    questions: List[ExamQuestionRead]

    class Config:
        orm_mode = True

class ExamUpdate(BaseModel):
    name: Optional[str] = Field(None, example="Nowa Nazwa Egzaminu")
    description: Optional[str] = Field(None, example="Nowy opis egzaminu.")
    questions: Optional[List[ExamQuestionCreate]] = None

    @validator('questions')
    def validate_questions(cls, v):
        if v is not None:
            if len(v) == 0:
                raise ValueError("Egzamin musi zawierać przynajmniej jedno pytanie.")
        return v