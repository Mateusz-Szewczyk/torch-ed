from typing import List
from sqlalchemy import (
    Integer,
    String,
    ForeignKey, Column,
)
from sqlalchemy.orm import(
    Mapped,
    mapped_column,
    relationship,
)
from .base import Base


class Deck(Base):
    __tablename__ = 'decks'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    # Zmieniamy na Integer + ForeignKey do users.id_
    user_id = Column(Integer, ForeignKey('users.id_'), index=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)

    flashcards = relationship("Flashcard", back_populates="deck", cascade="all, delete-orphan")
    # Jeżeli deck jest używany w StudySession, warto mieć relację odwrotną
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
