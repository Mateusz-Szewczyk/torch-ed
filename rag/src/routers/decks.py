# src/routers/decks.py

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session, joinedload
from typing import List

from ..models import Deck, Flashcard
from ..schemas import DeckCreate, DeckRead
from ..dependencies import get_db

import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/", response_model=DeckRead, status_code=201)
async def create_deck(deck: DeckCreate, db: Session = Depends(get_db)):
    logger.info(f"Creating a new deck with name: {deck.name}")
    logger.info(f"Deck data: {deck.flashcards}")

    try:
        new_deck = Deck(
            name=deck.name,
            description=deck.description
        )

        # Dodawanie fiszek do decka
        for fc in deck.flashcards:
            new_flashcard = Flashcard(
                question=fc.question,
                answer=fc.answer
            )
            new_deck.flashcards.append(new_flashcard)
            logger.info(f"Added flashcard: {new_flashcard}")

        db.add(new_deck)
        db.commit()
        db.refresh(new_deck)

        logger.info(f"Created new deck with ID {new_deck.id}")
        logger.info(f"Deck flashcards: {new_deck.flashcards}")
        return new_deck

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating deck: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating deck: {str(e)}")

@router.get("/", response_model=List[DeckRead])
async def get_decks(db: Session = Depends(get_db)):
    """
    Get All Decks
    ------------
    Retrieves a list of all decks along with their flashcards.
    """
    logger.info("Fetching all decks.")
    try:
        decks = db.query(Deck).options(joinedload(Deck.flashcards)).all()
        return decks
    except Exception as e:
        logger.error(f"Error fetching decks: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching decks: {str(e)}")

@router.get("/{deck_id}/", response_model=DeckRead)
async def get_deck(deck_id: int, db: Session = Depends(get_db)):
    """
    Get a Deck by ID
    ----------------
    Retrieves a specific deck by its ID along with its flashcards.
    """
    logger.info(f"Fetching deck with ID: {deck_id}")
    try:
        deck = db.query(Deck).options(joinedload(Deck.flashcards)).filter(Deck.id == deck_id).first()
        if not deck:
            logger.error(f"Deck with ID {deck_id} not found.")
            raise HTTPException(status_code=404, detail="Deck not found.")
        return deck
    except Exception as e:
        logger.error(f"Error fetching deck: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching deck: {str(e)}")

@router.put("/{deck_id}/", response_model=DeckRead)
async def update_deck(deck_id: int, deck: DeckCreate, db: Session = Depends(get_db)):
    logger.info(f"Updating deck with ID: {deck_id}")
    try:
        # Pobierz istniejący deck z fiszkami
        existing_deck = db.query(Deck).options(joinedload(Deck.flashcards)).filter(Deck.id == deck_id).first()
        if not existing_deck:
            logger.error(f"Deck with ID {deck_id} not found.")
            raise HTTPException(status_code=404, detail="Deck not found.")

        logger.info(f"Existing deck name: {existing_deck.name}, description: {existing_deck.description}")
        logger.info(f"Existing flashcards: {existing_deck.flashcards}")

        # Aktualizacja danych decka
        existing_deck.name = deck.name
        existing_deck.description = deck.description

        # Przygotowanie listy ID istniejących fiszek
        existing_flashcard_ids = set(fc.id for fc in existing_deck.flashcards if fc.id)
        logger.info(f"Existing flashcard IDs: {existing_flashcard_ids}")

        # Przygotowanie listy ID edytowanych fiszek
        edited_flashcards_ids = set(fc.id for fc in deck.flashcards if fc.id is not None)
        logger.info(f"Edited flashcard IDs: {edited_flashcards_ids}")

        # Aktualizacja istniejących fiszek
        for fc in deck.flashcards:
            if fc.id:
                if fc.id in existing_flashcard_ids:
                    # Znalezienie istniejącej fiszki i jej aktualizacja
                    existing_fc = next((flash for flash in existing_deck.flashcards if flash.id == fc.id), None)
                    if existing_fc:
                        existing_fc.question = fc.question
                        existing_fc.answer = fc.answer
                        logger.info(f"Updated flashcard ID {fc.id}: {existing_fc}")
                else:
                    logger.warning(f"Flashcard ID {fc.id} not found in existing deck. Skipping update.")
            else:
                # Dodawanie nowych fiszek
                new_flashcard = Flashcard(
                    question=fc.question,
                    answer=fc.answer,
                    deck_id=deck_id,
                )
                db.add(new_flashcard)
                existing_deck.flashcards.append(new_flashcard)
                logger.info(f"Added new flashcard: {new_flashcard}")

        # Usunięcie fiszek, które nie są w przesłanych danych
        flashcards_to_remove = existing_flashcard_ids - edited_flashcards_ids
        logger.info(f"Flashcards to remove: {flashcards_to_remove}")

        for fc_id in flashcards_to_remove:
            logger.info(f"Deleting flashcard ID {fc_id}")
            fc_to_delete = db.query(Flashcard).filter(Flashcard.id == fc_id).first()
            if fc_to_delete:
                db.delete(fc_to_delete)

        db.commit()  # Commit zmian
        db.refresh(existing_deck)  # Odśwież istniejący deck
        logger.info(f"Updated deck with ID {deck_id}")

        return existing_deck  # Zwrócenie zaktualizowanego decka

    except Exception as e:
        db.rollback()
        logger.error(f"Error updating deck: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error updating deck: {str(e)}")

@router.delete("/{deck_id}/", response_model=DeckRead)
async def delete_deck(deck_id: int, db: Session = Depends(get_db)):
    """
    Delete a Deck
    ------------
    Deletes a deck and all its associated flashcards.
    """
    logger.info(f"Deleting deck with ID: {deck_id}")
    try:
        deck = db.query(Deck).filter(Deck.id == deck_id).first()
        if not deck:
            logger.error(f"Deck with ID {deck_id} not found.")
            raise HTTPException(status_code=404, detail="Deck not found.")

        db.delete(deck)
        db.commit()
        logger.info(f"Deleted deck with ID {deck_id}")
        return deck
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting deck: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting deck: {str(e)}")
