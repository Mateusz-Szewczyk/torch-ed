from typing import List
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)
from sqlalchemy import (
    ForeignKey,
    Integer,
    String,
    DateTime,
    Boolean,
    func,
)
from datetime import datetime, timezone


class Base(DeclarativeBase):
    pass


metadata = Base.metadata


class Conversation(Base):
    __tablename__ = 'conversations'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)  # Użytkownik, do którego należy rozmowa
    created_at: Mapped[DateTime] = mapped_column(DateTime, default=datetime.now(timezone.utc), nullable=False)  # Data i czas rozpoczęcia rozmowy
    title: Mapped[str] = mapped_column(String, nullable=True)

    # Relacja do wiadomości
    messages: Mapped[List['Message']] = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = 'messages'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    conversation_id: Mapped[int] = mapped_column(Integer, ForeignKey('conversations.id'))
    sender: Mapped[str] = mapped_column(String, nullable=False)
    text: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    conversation: Mapped[List['Conversation']] = relationship("Conversation", back_populates="messages")


# Pozostałe modele

class ORMFile(Base):
    __tablename__ = 'files'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(String, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, default=datetime.now(timezone.utc), nullable=False)


class Deck(Base):
    __tablename__ = 'decks'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)
    flashcards: Mapped[List['Flashcard']] = relationship("Flashcard", back_populates="deck", cascade="all, delete-orphan")


class Flashcard(Base):
    __tablename__ = 'flashcards'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    question: Mapped[str] = mapped_column(String, nullable=False)
    answer: Mapped[str] = mapped_column(String, nullable=False)
    deck_id: Mapped[int] = mapped_column(Integer, ForeignKey('decks.id'), nullable=False)
    deck: Mapped[List['Deck']] = relationship("Deck", back_populates="flashcards")


# Nowe modele związane z Egzaminami

class Exam(Base):
    __tablename__ = 'exams'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, default=datetime.now(timezone.utc), nullable=False)

    # Relacja do pytań w egzaminie
    questions: Mapped[List['ExamQuestion']] = relationship("ExamQuestion", back_populates="exam", cascade="all, delete-orphan")


class ExamQuestion(Base):
    __tablename__ = 'exam_questions'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    text: Mapped[str] = mapped_column(String, nullable=False)
    exam_id: Mapped[int] = mapped_column(Integer, ForeignKey('exams.id'), nullable=False)

    # Relacja do egzaminu
    exam: Mapped[List['Exam']] = relationship("Exam", back_populates="questions")

    # Relacja do odpowiedzi
    answers: Mapped[List['ExamAnswer']] = relationship("ExamAnswer", back_populates="question", cascade="all, delete-orphan")


class ExamAnswer(Base):
    __tablename__ = 'exam_answers'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    text: Mapped[str] = mapped_column(String, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    question_id: Mapped[int] = mapped_column(Integer, ForeignKey('exam_questions.id'), nullable=False)

    # Relacja do pytania
    question: Mapped[List['ExamQuestion']] = relationship("ExamQuestion", back_populates="answers")