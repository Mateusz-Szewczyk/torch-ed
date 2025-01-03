from typing import List
from sqlalchemy import (
    Integer,
    String,
    DateTime,
    ForeignKey,
    Boolean,
)
from sqlalchemy.orm import (
    mapped_column,
    Mapped,
    relationship,
)
from datetime import datetime, timezone
from .base import Base


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