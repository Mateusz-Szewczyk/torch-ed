from typing import List
from sqlalchemy import(
    Integer,
    String,
    ForeignKey,
)
from sqlalchemy.orm import(
    Mapped,
    mapped_column,
    relationship,
)
from .base import Base


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
