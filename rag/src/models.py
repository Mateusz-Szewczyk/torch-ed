import datetime
from typing import Optional

from pydantic import ConfigDict
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Boolean,
    Float,
    UniqueConstraint,
    func,
    Text,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from sqlalchemy.orm import (
    relationship,
    Mapped,
    mapped_column,
    scoped_session,
    backref,
)
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id_"), index=True, nullable=False)
    workspace_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    created_at = Column(
        DateTime, default=datetime.datetime.now(datetime.UTC), nullable=False
    )
    title = Column(String, nullable=True)

    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )
    decks = relationship("Deck", back_populates="conversation")
    workspace = relationship("Workspace", back_populates="conversations")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    sender = Column(String, nullable=False)
    text = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # JSON field for storing steps and actions metadata
    # Structure: {"steps": [...], "actions": [...]}
    # Note: 'metadata' is reserved in SQLAlchemy, so we use 'meta_json'
    meta_json = Column(String, nullable=True)

    conversation = relationship("Conversation", back_populates="messages")


class ORMFile(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id_"), index=True, nullable=False)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(
        DateTime, default=datetime.datetime.now(datetime.UTC), nullable=False
    )


class ShareableContent(Base):
    """Bazowa klasa dla udostępnialnej zawartości"""

    __tablename__ = "shareable_content"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    share_code = Column(String(12), unique=True, nullable=False, index=True)
    content_type = Column(String, nullable=False)
    content_id = Column(Integer, nullable=False)
    creator_id = Column(
        Integer, ForeignKey("users.id_", ondelete="SET NULL"), nullable=True
    )
    is_public = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.now(datetime.UTC))
    access_count = Column(Integer, default=0)

    __table_args__ = (UniqueConstraint("content_type", "content_id", name="uix_content"),)


class UserDeckAccess(Base):
    """Mapowanie dostępu użytkowników do udostępnionych talii (decków)"""

    __tablename__ = "user_deck_access"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id_"), nullable=False)
    original_deck_id = Column(Integer, ForeignKey("decks.id"), nullable=False)
    user_deck_id = Column(Integer, ForeignKey("decks.id"), nullable=False)
    accessed_via_code = Column(String(12), nullable=False)
    added_at = Column(DateTime, default=datetime.datetime.now(datetime.UTC))
    is_active = Column(Boolean, default=True)

    original_deck = relationship(
        "Deck",
        foreign_keys=[original_deck_id],
        back_populates="user_deck_accesses",
    )
    user_deck = relationship(
        "Deck",
        foreign_keys=[user_deck_id],
        back_populates="user_owned_deck_accesses",
    )

    __table_args__ = (
        UniqueConstraint("user_id", "original_deck_id", name="uix_user_original_deck"),
    )


class UserExamAccess(Base):
    """Mapowanie dostępu użytkowników do udostępnionych egzaminów"""

    __tablename__ = "user_exam_access"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id_"), nullable=False)
    original_exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False)
    user_exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False)
    accessed_via_code = Column(String(12), nullable=False)
    added_at = Column(DateTime, default=datetime.datetime.now(datetime.UTC))
    is_active = Column(Boolean, default=True)

    original_exam = relationship(
        "Exam",
        foreign_keys=[original_exam_id],
        back_populates="user_exam_accesses",
    )
    user_exam = relationship(
        "Exam",
        foreign_keys=[user_exam_id],
        back_populates="user_owned_exam_accesses",
    )

    __table_args__ = (
        UniqueConstraint("user_id", "original_exam_id", name="uix_user_original_exam"),
    )


class Deck(Base):
    __tablename__ = "decks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id_"), index=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    conversation_id = Column(
        Integer, ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True
    )

    created_at = Column(
        DateTime, default=datetime.datetime.now(datetime.UTC), nullable=False
    )
    flashcards = relationship("Flashcard", back_populates="deck", cascade="all, delete-orphan")
    study_sessions = relationship(
        "StudySession", back_populates="deck", cascade="all, delete-orphan"
    )
    is_template = Column(Boolean, default=False)
    template_id = Column(Integer, ForeignKey("decks.id", ondelete="SET NULL"), nullable=True)

    conversation = relationship("Conversation", back_populates="decks")
    template = relationship("Deck", remote_side=[id], backref="copies")
    shared_content = relationship(
        "ShareableContent",
        primaryjoin="and_(Deck.id == foreign(ShareableContent.content_id), "
        "ShareableContent.content_type == 'deck')",
        viewonly=True,
    )

    # Dostępy do oryginalnej talii
    user_deck_accesses = relationship(
        "UserDeckAccess",
        foreign_keys=[UserDeckAccess.original_deck_id],
        back_populates="original_deck",
        cascade="all, delete-orphan",
    )
    # Dostępy do kopii talii przypisanych użytkownikowi
    user_owned_deck_accesses = relationship(
        "UserDeckAccess",
        foreign_keys=[UserDeckAccess.user_deck_id],
        back_populates="user_deck",
        cascade="all, delete-orphan",
    )


class Flashcard(Base):
    __tablename__ = "flashcards"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    question = Column(String, nullable=False)
    answer = Column(String, nullable=False)
    deck_id = Column(Integer, ForeignKey("decks.id"), nullable=False)
    media_url = Column(String, nullable=True)

    deck = relationship("Deck", back_populates="flashcards")
    user_flashcards = relationship(
        "UserFlashcard", back_populates="flashcard", cascade="all, delete-orphan"
    )


class UserFlashcard(Base):
    __tablename__ = "user_flashcards"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id_"), index=True)
    flashcard_id = Column(Integer, ForeignKey("flashcards.id"))

    ef = Column(Float, default=2.5)
    interval = Column(Integer, default=0)
    repetitions = Column(Integer, default=0)
    next_review = Column(DateTime, default=datetime.datetime.now(datetime.UTC).date())
    last_review = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="user_flashcards")
    flashcard = relationship("Flashcard", back_populates="user_flashcards")
    study_records = relationship(
        "StudyRecord", back_populates="user_flashcard", cascade="all, delete-orphan"
    )

    __table_args__ = (UniqueConstraint("user_id", "flashcard_id", name="uix_user_flashcard"),)

    model_config = ConfigDict(from_attributes=True)


class StudySession(Base):
    __tablename__ = "study_sessions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id_"), index=True)
    deck_id = Column(Integer, ForeignKey("decks.id"))
    started_at = Column(DateTime, default=datetime.datetime.now(datetime.UTC))
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="study_sessions")
    deck = relationship("Deck", back_populates="study_sessions")
    study_records = relationship(
        "StudyRecord", back_populates="session", cascade="all, delete-orphan"
    )

    model_config = ConfigDict(from_attributes=True)


class StudyRecord(Base):
    __tablename__ = "study_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("study_sessions.id"))
    user_flashcard_id = Column(Integer, ForeignKey("user_flashcards.id"))
    rating = Column(Integer, nullable=True)  # Ocena użytkownika (0-5)
    reviewed_at = Column(DateTime, default=datetime.datetime.now(datetime.UTC))

    session = relationship("StudySession", back_populates="study_records")
    user_flashcard = relationship("UserFlashcard", back_populates="study_records")

    model_config = ConfigDict(from_attributes=True)


class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(
        DateTime, default=datetime.datetime.now(datetime.UTC), nullable=False
    )
    user_id = Column(Integer, ForeignKey("users.id_"), index=True, nullable=False)
    conversation_id = Column(Integer, nullable=True)

    questions = relationship(
        "ExamQuestion", back_populates="exam", cascade="all, delete-orphan"
    )
    is_template = Column(Boolean, default=False)
    template_id = Column(Integer, ForeignKey("exams.id", ondelete="SET NULL"), nullable=True)

    template = relationship("Exam", remote_side=[id], backref="copies")
    shared_content = relationship(
        "ShareableContent",
        primaryjoin="and_(Exam.id == foreign(ShareableContent.content_id), "
        "ShareableContent.content_type == 'exam')",
        viewonly=True,
    )

    # Dostępy do oryginalnego egzaminu
    user_exam_accesses = relationship(
        "UserExamAccess",
        foreign_keys=[UserExamAccess.original_exam_id],
        back_populates="original_exam",
        cascade="all, delete-orphan",
    )
    # Dostępy do kopii egzaminu przypisanych użytkownikowi
    user_owned_exam_accesses = relationship(
        "UserExamAccess",
        foreign_keys=[UserExamAccess.user_exam_id],
        back_populates="user_exam",
        cascade="all, delete-orphan",
    )


class ExamQuestion(Base):
    __tablename__ = "exam_questions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    text = Column(String, nullable=False)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False)

    exam = relationship("Exam", back_populates="questions")
    answers = relationship(
        "ExamAnswer", back_populates="question", cascade="all, delete-orphan"
    )


class ExamAnswer(Base):
    __tablename__ = "exam_answers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    text = Column(String, nullable=False)
    is_correct = Column(Boolean, nullable=False, default=False)
    question_id = Column(Integer, ForeignKey("exam_questions.id"), nullable=False)

    question = relationship("ExamQuestion", back_populates="answers")


class ExamResult(Base):
    __tablename__ = "exam_results"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    exam_id = Column(
        Integer, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(Integer, ForeignKey("users.id_"), index=True, nullable=False)
    started_at = Column(
        DateTime, default=datetime.datetime.now(datetime.UTC), nullable=False
    )
    completed_at = Column(DateTime, nullable=True)
    score = Column(Float, nullable=True)

    exam = relationship("Exam", backref=backref("results", cascade="all, delete-orphan"))
    answers = relationship(
        "ExamResultAnswer", back_populates="exam_result", cascade="all, delete-orphan"
    )


class ExamResultAnswer(Base):
    __tablename__ = "exam_result_answers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    exam_result_id = Column(
        Integer, ForeignKey("exam_results.id", ondelete="CASCADE"), nullable=False
    )
    question_id = Column(Integer, ForeignKey("exam_questions.id"), nullable=False)
    selected_answer_id = Column(Integer, ForeignKey("exam_answers.id"), nullable=False)
    is_correct = Column(Boolean, nullable=False)
    answer_time = Column(
        DateTime, default=datetime.datetime.now(datetime.UTC), nullable=False
    )

    exam_result = relationship("ExamResult", back_populates="answers")
    question = relationship("ExamQuestion")
    selected_answer = relationship("ExamAnswer")


# =============================================================================
# WORKSPACE & CATEGORY MODELS
# =============================================================================

class FileCategory(Base):
    """
    Kategoria pliku - może być systemowa (user_id=NULL) lub użytkownika.
    """
    __tablename__ = "file_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("users.id_", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    documents = relationship("WorkspaceDocument", back_populates="category")
    workspace_categories = relationship("WorkspaceCategory", back_populates="category", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_category_name_user", postgresql_nulls_not_distinct=True),
    )

    model_config = ConfigDict(from_attributes=True)


class Workspace(Base):
    """
    Workspace - kontekst pracy użytkownika.
    Filtruje dokumenty na podstawie wybranych kategorii.
    """
    __tablename__ = "workspaces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("users.id_", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    workspace_categories = relationship("WorkspaceCategory", back_populates="workspace", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="workspace", cascade="all, delete-orphan")

    model_config = ConfigDict(from_attributes=True)


class WorkspaceCategory(Base):
    """
    Tabela asocjacyjna: Workspace <-> FileCategory (many-to-many).
    """
    __tablename__ = "workspace_categories"

    workspace_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        primary_key=True
    )
    category_id = Column(
        UUID(as_uuid=True),
        ForeignKey("file_categories.id", ondelete="CASCADE"),
        primary_key=True
    )
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    workspace = relationship("Workspace", back_populates="workspace_categories")
    category = relationship("FileCategory", back_populates="workspace_categories")

    model_config = ConfigDict(from_attributes=True)


class User(Base):
    __tablename__ = "users"

    id_: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    role: Mapped[str] = mapped_column(String, nullable=False, default="user")
    role_expiry: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    user_flashcards = relationship(
        "UserFlashcard", back_populates="user", cascade="all, delete-orphan"
    )
    study_sessions = relationship(
        "StudySession", back_populates="user", cascade="all, delete-orphan"
    )
    conversations = relationship("Conversation", backref="user", cascade="all, delete-orphan")
    files = relationship("ORMFile", backref="user", cascade="all, delete-orphan")
    decks = relationship("Deck", backref="user", cascade="all, delete-orphan")
    exams = relationship("Exam", backref="user", cascade="all, delete-orphan")
    exam_results = relationship("ExamResult", backref="user", cascade="all, delete-orphan")
    deck_accesses = relationship("UserDeckAccess", backref="user", cascade="all, delete-orphan")
    exam_accesses = relationship("UserExamAccess", backref="user", cascade="all, delete-orphan")
    shared_contents = relationship(
        "ShareableContent", backref="creator", cascade="save-update, merge"
    )
    workspaces = relationship("Workspace", backref="user", cascade="all, delete-orphan")
    categories = relationship("FileCategory", backref="user", cascade="all, delete-orphan")
    workspace_documents = relationship("WorkspaceDocument", backref="user", cascade="all, delete-orphan")

    @staticmethod
    def get_user(session: scoped_session, user_name: str) -> Optional["User"] | None:
        return session.query(User).filter_by(user_name=user_name).first()


# =============================================================================
# WORKSPACE MODELS - Document Reader & AI Assistant
# =============================================================================

class WorkspaceDocument(Base):
    """
    Główna tabela dokumentu w Workspace.
    Przechowuje metadane dokumentu oraz powiązania z użytkownikiem.
    """
    __tablename__ = "workspace_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("users.id_", ondelete="CASCADE"), nullable=False, index=True)
    category_id = Column(
        UUID(as_uuid=True),
        ForeignKey("file_categories.id", ondelete="SET NULL"),
        nullable=True
    )
    title = Column(Text, nullable=False)
    original_filename = Column(String(512), nullable=True)
    file_type = Column(String(50), nullable=True)  # 'pdf', 'txt', 'docx', etc.
    total_length = Column(Integer, default=0)  # Total character count
    total_sections = Column(Integer, default=0)  # Number of sections
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    category = relationship("FileCategory", back_populates="documents")
    sections = relationship(
        "DocumentSection",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentSection.section_index"
    )
    highlights = relationship(
        "UserHighlight",
        back_populates="document",
        cascade="all, delete-orphan"
    )
    images = relationship(
        "DocumentImage",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentImage.page_number, DocumentImage.image_index"
    )

    model_config = ConfigDict(from_attributes=True)


class DocumentSection(Base):
    """
    Sekcja dokumentu dla lazy loadingu.
    Każda sekcja to logiczny kawałek tekstu (akapit/strona).
    Dzięki temu pobieramy tylko widoczny fragment.
    """
    __tablename__ = "document_sections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workspace_documents.id", ondelete="CASCADE"),
        nullable=False
    )
    section_index = Column(Integer, nullable=False)  # Kolejność sekcji
    content_text = Column(Text, nullable=False)  # Czysty tekst sekcji

    # Style bazowe z PDF (pogrubienia, italic) jako offsety
    # Format: [{"start": 0, "end": 10, "style": "bold"}, {"start": 15, "end": 25, "style": "italic"}]
    base_styles = Column(JSONB, default=list)

    # Opcjonalne metadane sekcji (np. numer strony, typ nagłówka)
    section_metadata = Column(JSONB, default=dict)

    char_start = Column(Integer, default=0)  # Pozycja startowa w całym dokumencie
    char_end = Column(Integer, default=0)  # Pozycja końcowa w całym dokumencie

    # Relationships
    document = relationship("WorkspaceDocument", back_populates="sections")
    highlights = relationship(
        "UserHighlight",
        back_populates="section",
        cascade="all, delete-orphan"
    )

    # Indeks do szybkiego pobierania kolejnych partii przy scrollowaniu
    __table_args__ = (
        Index('idx_sections_order', 'document_id', 'section_index'),
    )

    model_config = ConfigDict(from_attributes=True)


class DocumentImage(Base):
    """
    Obrazy wyodrębnione z dokumentu PDF.
    Przechowuje metadane obrazu i lokalizację w dokumencie.
    """
    __tablename__ = "document_images"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workspace_documents.id", ondelete="CASCADE"),
        nullable=False
    )
    # Numer strony, z której pochodzi obraz (1-based)
    page_number = Column(Integer, nullable=False)
    # Indeks obrazu na stronie (0-based) dla porządku
    image_index = Column(Integer, default=0)

    # Ścieżka do pliku obrazu (relative path w storage)
    image_path = Column(String(512), nullable=False)
    # Typ obrazu (png, jpg, jpeg)
    image_type = Column(String(20), nullable=False)
    # Rozmiar w bajtach
    file_size = Column(Integer, default=0)

    # Wymiary obrazu
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)

    # Pozycja na stronie (do późniejszego użycia)
    x_position = Column(Float, nullable=True)
    y_position = Column(Float, nullable=True)

    # Opcjonalne metadane (np. alt text, caption)
    alt_text = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    document = relationship("WorkspaceDocument", back_populates="images")

    # Indeks dla szybkiego pobierania obrazów dokumentu
    __table_args__ = (
        Index('idx_document_images_doc_page', 'document_id', 'page_number'),
    )

    model_config = ConfigDict(from_attributes=True)


class UserHighlight(Base):
    """
    Zakreślenie użytkownika z kolorem.
    Kluczowa funkcja: filtrowanie fragmentów po kolorze dla kontekstu AI.
    """
    __tablename__ = "user_highlights"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workspace_documents.id", ondelete="CASCADE"),
        nullable=False
    )
    section_id = Column(
        UUID(as_uuid=True),
        ForeignKey("document_sections.id", ondelete="CASCADE"),
        nullable=False
    )

    # Offsety wewnątrz content_text sekcji
    start_offset = Column(Integer, nullable=False)
    end_offset = Column(Integer, nullable=False)

    # Kod koloru (np. 'red', 'green', 'yellow', 'blue', 'purple')
    color_code = Column(String(20), nullable=False)

    # Opcjonalna notatka/adnotacja
    annotation_text = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    document = relationship("WorkspaceDocument", back_populates="highlights")
    section = relationship("DocumentSection", back_populates="highlights")

    # Indeksy dla szybkiego wyszukiwania
    __table_args__ = (
        # Szybkie znajdowanie zakreśleń dla widocznego fragmentu
        Index('idx_highlights_lookup', 'section_id'),
        # Szybkie wyciąganie wszystkich fragmentów danego koloru (dla AI)
        Index('idx_highlights_color', 'document_id', 'color_code'),
    )

    model_config = ConfigDict(from_attributes=True)

