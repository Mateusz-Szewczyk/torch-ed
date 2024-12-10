# src/routers/flashcards.py

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import List

from ..models import Flashcard, Deck
from ..schemas import FlashcardCreate, FlashcardRead, DeckRead
from ..dependencies import get_db

import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/decks/{deck_id}/flashcards/", response_model=List[FlashcardRead], status_code=status.HTTP_201_CREATED)
async def add_flashcards(deck_id: int, flashcards: List[FlashcardCreate], db: Session = Depends(get_db)):
    """
    Add Flashcards to a Deck
    ------------------------
    Adds one or more flashcards to a specific deck.
    """
    logger.info(f"Adding {len(flashcards)} flashcards to deck ID: {deck_id}")
    try:
        deck = db.query(Deck).filter(Deck.id == deck_id).first()
        if not deck:
            logger.error(f"Deck with ID {deck_id} not found.")
            raise HTTPException(status_code=404, detail="Deck not found.")

        new_flashcards = []
        for fc in flashcards:
            new_flashcard = Flashcard(question=fc.question, answer=fc.answer, deck_id=deck_id)
            db.add(new_flashcard)
            new_flashcards.append(new_flashcard)

        db.commit()

        # Odświeżenie fiszek, aby uzyskać ich ID
        for fc in new_flashcards:
            db.refresh(fc)

        logger.info(f"Added {len(new_flashcards)} flashcards to deck ID {deck_id}")
        return new_flashcards
    except Exception as e:
        db.rollback()
        logger.error(f"Error adding flashcards to deck: {e}")
        raise HTTPException(status_code=500, detail=f"Error adding flashcards: {str(e)}")

@router.get("/decks/{deck_id}/flashcards/", response_model=List[FlashcardRead])
async def get_flashcards(deck_id: int, db: Session = Depends(get_db)):
    """
    Get Flashcards from a Deck
    --------------------------
    Retrieves all flashcards associated with a specific deck.
    """
    logger.info(f"Fetching flashcards for deck ID: {deck_id}")
    try:
        deck = db.query(Deck).filter(Deck.id == deck_id).first()
        if not deck:
            logger.error(f"Deck with ID {deck_id} not found.")
            raise HTTPException(status_code=404, detail="Deck not found.")

        flashcards = db.query(Flashcard).filter(Flashcard.deck_id == deck_id).all()
        logger.info(f"Fetched {len(flashcards)} flashcards for deck ID {deck_id}")
        return flashcards
    except Exception as e:
        logger.error(f"Error fetching flashcards: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching flashcards: {str(e)}")

@router.delete("/flashcards/{flashcard_id}/", response_model=FlashcardRead)
async def delete_flashcard(flashcard_id: int, db: Session = Depends(get_db)):
    """
    Delete a Flashcard
    ------------------
    Deletes a specific flashcard by its ID.
    """
    logger.info(f"Deleting flashcard with ID: {flashcard_id}")
    try:
        flashcard = db.query(Flashcard).filter(Flashcard.id == flashcard_id).first()
        if not flashcard:
            logger.error(f"Flashcard with ID {flashcard_id} not found.")
            raise HTTPException(status_code=404, detail="Flashcard not found.")

        db.delete(flashcard)
        db.commit()
        logger.info(f"Deleted flashcard with ID {flashcard_id}")
        return flashcard
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting flashcard: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting flashcard: {str(e)}")

@router.put("/flashcards/{flashcard_id}/", response_model=FlashcardRead)
async def update_flashcard(flashcard_id: int, flashcard: FlashcardCreate, db: Session = Depends(get_db)):
    """
    Update a Flashcard
    ------------------
    Updates the question and/or answer of an existing flashcard.
    """
    logger.info(f"Updating flashcard with ID: {flashcard_id}")
    try:
        existing_flashcard = db.query(Flashcard).filter(Flashcard.id == flashcard_id).first()
        if not existing_flashcard:
            logger.error(f"Flashcard with ID {flashcard_id} not found.")
            raise HTTPException(status_code=404, detail="Flashcard not found.")

        existing_flashcard.question = flashcard.question
        existing_flashcard.answer = flashcard.answer
        db.commit()
        db.refresh(existing_flashcard)
        logger.info(f"Updated flashcard with ID {flashcard_id}")
        return existing_flashcard
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating flashcard: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating flashcard: {str(e)}")
