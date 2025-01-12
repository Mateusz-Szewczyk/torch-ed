from sqlalchemy import (
    Integer,
    String,
    DateTime,
    ForeignKey,
    Boolean, Column,
)
from sqlalchemy.orm import (
    relationship,
)
from datetime import datetime
from .base import Base


class Exam(Base):
    __tablename__ = 'exams'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id_'), index=True, nullable=False)

    questions = relationship(
        "ExamQuestion",
        back_populates="exam",
        cascade="all, delete-orphan"
    )

class ExamQuestion(Base):
    __tablename__ = 'exam_questions'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    text = Column(String, nullable=False)
    exam_id = Column(Integer, ForeignKey('exams.id'), nullable=False)

    exam = relationship(
        "Exam",
        back_populates="questions"
    )
    answers = relationship(
        "ExamAnswer",
        back_populates="question",
        cascade="all, delete-orphan"
    )


class ExamAnswer(Base):
    __tablename__ = 'exam_answers'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    text = Column(String, nullable=False)
    is_correct = Column(Boolean, nullable=False, default=False)
    question_id = Column(Integer, ForeignKey('exam_questions.id'), nullable=False)

    question = relationship(
        "ExamQuestion",
        back_populates="answers"
    )
