# src/models.py

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, func
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime


class Conversation(Base):
    __tablename__ = 'conversations'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String, index=True, nullable=False)  # Użytkownik, do którego należy rozmowa
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)  # Data i czas rozpoczęcia rozmowy
    title = Column(String, nullable=True)

    # Relacja do wiadomości
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey('conversations.id'))
    sender = Column(String, nullable=False)
    text = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    conversation = relationship("Conversation", back_populates="messages")


# Pozostałe modele

class ORMFile(Base):
    __tablename__ = 'files'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Deck(Base):
    __tablename__ = 'decks'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    flashcards = relationship("Flashcard", back_populates="deck", cascade="all, delete-orphan")


class Flashcard(Base):
    __tablename__ = 'flashcards'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    question = Column(String, nullable=False)
    answer = Column(String, nullable=False)
    deck_id = Column(Integer, ForeignKey('decks.id'), nullable=False)
    media_url = Column(String, nullable=True)
    deck = relationship("Deck", back_populates="flashcards")


# Nowe modele związane z Egzaminami

class Exam(Base):
    __tablename__ = 'exams'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relacja do pytań w egzaminie
    questions = relationship("ExamQuestion", back_populates="exam", cascade="all, delete-orphan")


class ExamQuestion(Base):
    __tablename__ = 'exam_questions'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    text = Column(String, nullable=False)
    exam_id = Column(Integer, ForeignKey('exams.id'), nullable=False)

    # Relacja do egzaminu
    exam = relationship("Exam", back_populates="questions")

    # Relacja do odpowiedzi
    answers = relationship("ExamAnswer", back_populates="question", cascade="all, delete-orphan")


class ExamAnswer(Base):
    __tablename__ = 'exam_answers'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    text = Column(String, nullable=False)
    is_correct = Column(Boolean, nullable=False, default=False)
    question_id = Column(Integer, ForeignKey('exam_questions.id'), nullable=False)

    # Relacja do pytania
    question = relationship("ExamQuestion", back_populates="answers")
