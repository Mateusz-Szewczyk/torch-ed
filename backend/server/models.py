# src/models.py

from typing import Optional
from datetime import datetime

from pydantic import ConfigDict
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Boolean,
    func, Float, UniqueConstraint
)
from sqlalchemy.orm import relationship, Mapped, mapped_column, scoped_session, declarative_base, backref

Base = declarative_base()


class Conversation(Base):
    __tablename__ = 'conversations'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id_'), index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    title = Column(String, nullable=True)

    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan"
    )


class Message(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey('conversations.id'))
    sender = Column(String, nullable=False)
    text = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    conversation = relationship(
        "Conversation",
        back_populates="messages"
    )

class ORMFile(Base):
    __tablename__ = 'files'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id_'), index=True, nullable=False)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Deck(Base):
    __tablename__ = 'decks'
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id_'), index=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    conversation_id = Column(Integer, ForeignKey('conversations.id'), nullable=True)

    flashcards = relationship("Flashcard", back_populates="deck", cascade="all, delete-orphan")
    study_sessions = relationship("StudySession", back_populates="deck", cascade="all, delete-orphan")



class Flashcard(Base):
    __tablename__ = 'flashcards'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    question = Column(String, nullable=False)
    answer = Column(String, nullable=False)
    deck_id = Column(Integer, ForeignKey('decks.id'), nullable=False)

    deck = relationship(
        "Deck",
        back_populates="flashcards"
    )
    user_flashcards = relationship(
        "UserFlashcard",
        back_populates="flashcard",
        cascade="all, delete-orphan"
    )


class UserFlashcard(Base):
    __tablename__ = 'user_flashcards'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id_'), index=True)
    flashcard_id = Column(Integer, ForeignKey('flashcards.id'))

    ef = Column(Float, default=2.5)
    interval = Column(Integer, default=0)
    repetitions = Column(Integer, default=0)
    next_review = Column(DateTime, default=datetime.utcnow)

    user = relationship(
        "User",
        back_populates="user_flashcards"
    )
    flashcard = relationship(
        "Flashcard",
        back_populates="user_flashcards"
    )
    study_records = relationship(
        "StudyRecord",
        back_populates="user_flashcard",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint('user_id', 'flashcard_id', name='uix_user_flashcard'),
    )

    model_config = ConfigDict(from_attributes=True)



class StudySession(Base):
    __tablename__ = 'study_sessions'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id_'), index=True)
    deck_id = Column(Integer, ForeignKey('decks.id'))
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    user = relationship(
        "User",
        back_populates="study_sessions"
    )
    deck = relationship(
        "Deck",
        back_populates="study_sessions"
    )
    study_records = relationship(
        "StudyRecord",
        back_populates="session",
        cascade="all, delete-orphan"
    )

    model_config = ConfigDict(from_attributes=True)



class StudyRecord(Base):
    __tablename__ = 'study_records'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey('study_sessions.id'))
    user_flashcard_id = Column(Integer, ForeignKey('user_flashcards.id'))
    rating = Column(Integer, nullable=True)  # Ocena użytkownika (0-5)
    reviewed_at = Column(DateTime, default=datetime.utcnow)

    session = relationship(
        "StudySession",
        back_populates="study_records"
    )
    user_flashcard = relationship(
        "UserFlashcard",
        back_populates="study_records"
    )

    model_config = ConfigDict(from_attributes=True)

class Exam(Base):
    __tablename__ = 'exams'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id_'), index=True, nullable=False)
    conversation_id = Column(Integer, nullable=True)  # Pole na conversation_id

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

    exam = relationship("Exam", back_populates="questions")
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

    question = relationship("ExamQuestion", back_populates="answers")

class ExamResult(Base):
    __tablename__ = 'exam_results'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    exam_id = Column(Integer, ForeignKey('exams.id', ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id_'), index=True, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    score = Column(Float, nullable=True)

    # Ustawienie cascade na backref powoduje, że przy usuwaniu egzaminu wyniki również zostaną usunięte.
    exam = relationship("Exam", backref=backref("results", cascade="all, delete-orphan"))
    answers = relationship(
        "ExamResultAnswer",
        back_populates="exam_result",
        cascade="all, delete-orphan"
    )

class ExamResultAnswer(Base):
    __tablename__ = 'exam_result_answers'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    exam_result_id = Column(Integer, ForeignKey('exam_results.id', ondelete="CASCADE"), nullable=False)
    question_id = Column(Integer, ForeignKey('exam_questions.id'), nullable=False)
    selected_answer_id = Column(Integer, ForeignKey('exam_answers.id'), nullable=False)
    is_correct = Column(Boolean, nullable=False)
    answer_time = Column(DateTime, default=datetime.utcnow, nullable=False)

    exam_result = relationship("ExamResult", back_populates="answers")
    question = relationship("ExamQuestion")
    selected_answer = relationship("ExamAnswer")


class User(Base):
    __tablename__ = 'users'

    id_: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    role: Mapped[str] = mapped_column(String, nullable=False, default='user')
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)

    user_flashcards = relationship(
        "UserFlashcard",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    study_sessions = relationship(
        "StudySession",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    @staticmethod
    def get_user(session: scoped_session, user_name: str) -> Optional['User'] | None:
        return session.query(User).filter_by(user_name=user_name).first()
