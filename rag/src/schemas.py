# src/schemas.py

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime

class FlashcardBase(BaseModel):
    question: str
    answer: str

class FlashcardCreate(FlashcardBase):
    id: Optional[int] = None
    media_url: Optional[str] = None

    @field_validator('question', 'answer')
    def not_empty(cls, v):
        if not v.strip():
            raise ValueError('Cannot be empty')
        return v

class FlashcardRead(FlashcardBase):
    id: int
    question: str
    answer: str
    deck_id: int
    media_url: Optional[str] = None

    class Config:
        from_attributes = True

class UserFlashcardRead(BaseModel):
    id: int
    flashcard: FlashcardRead
    ef: float
    interval: int
    repetitions: int
    next_review: datetime

    class Config:
        from_attributes = True


class StudySessionCreate(BaseModel):
    deck_id: int

class StudySessionRead(BaseModel):
    id: int
    user_id: int  # Zmieniono z str na int
    deck_id: int
    started_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class StudyRecordCreate(BaseModel):
    user_flashcard_id: int
    rating: int  # 0 to 5

class StudyRecordRead(BaseModel):
    id: int
    session_id: int
    user_flashcard_id: int
    rating: Optional[int] = None
    reviewed_at: datetime

    class Config:
        from_attributes = True

class StudySessionUpdate(BaseModel):
    completed_at: Optional[datetime] = None


class DeckBase(BaseModel):
    name: str
    description: Optional[str] = None
    conversation_id: Optional[int] = None

class DeckCreate(DeckBase):
    flashcards: List[FlashcardCreate]

    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Deck name cannot be empty')
        return v

class DeckRead(BaseModel):
    id: int
    user_id: int
    name: str
    description: Optional[str] = None
    conversation_id: Optional[int] = None
    flashcards: List[FlashcardRead]

    class Config:
        from_attributes = True

class DeckInfoRead(BaseModel):
    id: int
    user_id: int
    name: str
    description: Optional[str] = None
    conversation_id: Optional[int] = None
    flashcard_count: int
    created_at: Optional[datetime] = None
    last_session: Optional[datetime] = None

    class Config:
        from_attributes = True

class UploadedFileRead(BaseModel):
    id: int
    name: str
    description: Optional[str] = None  # Opcjonalne pole
    category: str
    created_at: datetime

    class Config:
        from_attributes = True

class UploadResponse(BaseModel):
    message: str
    uploaded_files: List[UploadedFileRead]  # Poprawnie zdefiniowany UploadedFileRead
    user_id: int  # Zmieniono z str na int
    file_name: str
    file_description: Optional[str]
    category: Optional[str]

class QueryRequest(BaseModel):
    query: str
    conversation_id: int
    selected_tools: Optional[List[str]] = None

class QueryResponse(BaseModel):
    user_id: int
    query: str
    answer: str

class DeleteKnowledgeRequest(BaseModel):
    file_name: str

class DeleteKnowledgeResponse(BaseModel):
    message: str
    deleted_from_vector_store: bool

class ListFilesRequest(BaseModel):
    user_id: int

class ConversationBase(BaseModel):
    user_id: int
    title: Optional[str] = None

class ConversationCreate(ConversationBase):
    pass

class ConversationRead(BaseModel):
    id: int
    user_id: int
    title: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Metadata schemas for message steps and actions
class MessageStepSchema(BaseModel):
    content: str
    status: str  # "loading" or "complete"


class MessageActionSchema(BaseModel):
    type: str  # "flashcards" or "exam"
    id: int
    name: str
    count: int


class MessageMetadataSchema(BaseModel):
    steps: Optional[List[MessageStepSchema]] = None
    actions: Optional[List[MessageActionSchema]] = None


class MessageCreate(BaseModel):
    sender: str
    text: str
    # Accept 'metadata' from API request
    metadata: Optional[str] = None


class MessageRead(BaseModel):
    id: int
    conversation_id: int
    sender: str
    text: str
    created_at: datetime = Field(default_factory=datetime.now)
    # Metadata field containing steps and actions JSON
    metadata: Optional[str] = None

    class Config:
        from_attributes = True

class ConversationUpdate(BaseModel):
    title: Optional[str] = None

    @field_validator('title')
    def title_not_empty(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Title cannot be empty')
        return v

class ExamBase(BaseModel):
    name: str
    description: Optional[str] = None
    conversation_id: Optional[int] = None

class ExamAnswerCreate(BaseModel):
    id: Optional[int] = None
    text: str = Field(..., example="3.14")
    is_correct: bool = Field(..., example=True)

class ExamAnswerRead(BaseModel):
    id: int
    text: str
    is_correct: bool

    class Config:
        from_attributes = True

class ExamQuestionCreate(BaseModel):
    id: Optional[int] = None
    text: str = Field(..., example="Jaka jest wartość liczby pi?")
    answers: List[ExamAnswerCreate]

    @field_validator('answers')
    def validate_answers(cls, v):
        if len(v) <= 2:
            raise ValueError("Każde pytanie musi mieć minimalnie 2 odpowiedzi.")
        correct_answers = [answer for answer in v if answer.is_correct]
        if len(correct_answers) < 1:
            raise ValueError("Każde pytanie musi mieć conajmniej jedną poprawną odpowiedź.")
        return v

class ExamQuestionRead(BaseModel):
    id: int
    text: str
    answers: List[ExamAnswerRead]

    class Config:
        from_attributes = True

class ExamCreate(ExamBase):
    questions: List[ExamQuestionCreate]

    @field_validator('name')
    def validate_questions(cls, v):
        if len(v) == 0:
            raise ValueError("Exam cannot be empty.")
        return v

class ExamRead(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: datetime
    questions: List[ExamQuestionRead]
    conversation_id: Optional[int] = None

    class Config:
        from_attributes = True

class ExamUpdate(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = Field(None, example="Nowa Nazwa Egzaminu")
    description: Optional[str] = Field(None, example="Nowy opis egzaminu.")
    questions: Optional[List[ExamQuestionCreate]] = None
    conversation_id: Optional[int] = None  # Allow updating conversation_id if needed

    @field_validator('questions')
    def validate_questions(cls, v):
        if v is not None and len(v) == 0:
            raise ValueError("Exam must contain at least one question.")
        return v


class ExamResultAnswerCreate(BaseModel):
    question_id: int
    selected_answer_id: int
    answer_time: datetime

class ExamResultCreate(BaseModel):
    exam_id: int
    answers: List[ExamResultAnswerCreate]

class ExamResultAnswerRead(BaseModel):
    id: int
    question_id: int
    selected_answer_id: int
    is_correct: bool
    answer_time: datetime

    class Config:
        from_attributes = True

class ExamResultRead(BaseModel):
    id: int
    exam_id: int
    user_id: int  # Zmieniono z str na int
    started_at: datetime
    completed_at: Optional[datetime]
    score: Optional[float]
    answers: List[ExamResultAnswerRead]

    class Config:
        from_attributes = True

class StudyRecord(BaseModel):
    id: int
    session_id: Optional[int]
    user_flashcard_id: Optional[int]
    rating: Optional[int]
    reviewed_at: Optional[datetime]

    class Config:
        from_attributes = True

# Schematy dla user_flashcards
class UserFlashcard(BaseModel):
    id: int
    user_id: int
    flashcard_id: int
    ef: float
    interval: int
    repetitions: int
    next_review: Optional[datetime]

    class Config:
        from_attributes = True

# Schematy dla study_sessions
class StudySession(BaseModel):
    id: int
    user_id: int
    deck_id: int
    started_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True

# Schematy dla exam_result_answers
class ExamResultAnswer(BaseModel):
    id: int
    exam_result_id: int
    question_id: int
    selected_answer_id: int
    is_correct: bool
    answer_time: datetime

    class Config:
        from_attributes = True

# Schematy dla exam_results
class ExamResult(BaseModel):
    id: int
    exam_id: int
    user_id: int
    started_at: datetime
    completed_at: Optional[datetime]
    score: float

    class Config:
        from_attributes = True

# Schemat dla Dashboard Data
class DashboardData(BaseModel):
    study_records: List[StudyRecord]
    user_flashcards: List[UserFlashcard]
    study_sessions: List[StudySession]
    exam_result_answers: List[ExamResultAnswer]
    exam_results: List[ExamResult]

