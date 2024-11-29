from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class Deck(Base):
    __tablename__ = 'decks'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)

    flashcards = relationship('Flashcard', back_populates='deck', cascade='all, delete-orphan')


class Flashcard(Base):
    __tablename__ = 'flashcards'

    id = Column(Integer, primary_key=True, autoincrement=True)
    question = Column(String, nullable=False)
    answer = Column(String, nullable=False)
    deck_id = Column(Integer, ForeignKey('decks.id'), nullable=False)

    # Relacja do talii
    deck = relationship('Deck', back_populates='flashcards')
