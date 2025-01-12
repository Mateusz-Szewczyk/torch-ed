# src/routers/user_flashcards.py

import logging

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session

from ..models import UserFlashcard, Flashcard, Deck
from ..schemas import UserFlashcardRead
from ..dependencies import get_db
from ..auth import get_current_user
from ..models import User

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/by_flashcard/{flashcard_id}/", response_model=UserFlashcardRead)
def get_user_flashcard_by_flashcard(
    flashcard_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Pobiera UserFlashcard dla danego użytkownika i fiszki.
    """
    logger.info(f"Pobieranie UserFlashcard dla flashcard_id={flashcard_id} przez user_id={current_user.id_}")
    user_flashcard = db.query(UserFlashcard).filter(
        UserFlashcard.user_id == str(current_user.id_),
        UserFlashcard.flashcard_id == flashcard_id
    ).first()

    if not user_flashcard:
        logger.error(f"UserFlashcard dla flashcard_id={flashcard_id} nie znaleziony dla użytkownika.")
        raise HTTPException(status_code=404, detail="UserFlashcard nie znaleziony.")

    return user_flashcard
