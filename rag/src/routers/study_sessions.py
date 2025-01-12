# src/routers/study_sessions.py

import logging
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session

from ..models import StudySession, StudyRecord, UserFlashcard, Flashcard, Deck
from ..schemas import (
    StudySessionCreate, StudySessionRead,
    StudyRecordCreate, StudyRecordRead,
    FlashcardRead  # <-- DODAJ import FlashcardRead
)
from ..dependencies import get_db
from ..auth import get_current_user
from ..models import User

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", response_model=StudySessionRead, status_code=201)
def create_study_session(
    session_create: StudySessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Tworzy nową sesję nauki dla użytkownika i wybranego decka.
    """
    logger.info(f"Tworzenie sesji nauki dla deck_id={session_create.deck_id} przez user_id={current_user.id_}")

    deck = db.query(Deck).filter(
        Deck.id == session_create.deck_id,
        Deck.user_id == current_user.id_  # Usunięto konwersję do str
    ).first()
    if not deck:
        logger.error(f"Deck z ID={session_create.deck_id} nie znaleziony dla użytkownika.")
        raise HTTPException(status_code=404, detail="Deck nie znaleziony.")

    # Inicjalizacja UserFlashcard dla użytkownika, jeśli jeszcze nie istnieje
    user_flashcards = db.query(UserFlashcard).filter(
        UserFlashcard.user_id == current_user.id_,
        UserFlashcard.flashcard_id.in_([fc.id for fc in deck.flashcards])
    ).all()

    existing_flashcard_ids = {uf.flashcard_id for uf in user_flashcards}
    new_flashcards = []
    for flashcard in deck.flashcards:
        if flashcard.id not in existing_flashcard_ids:
            new_uf = UserFlashcard(
                user_id=current_user.id_,
                flashcard_id=flashcard.id,
                ef=2.5,
                interval=0,
                repetitions=0,
                next_review=datetime.utcnow()
            )
            db.add(new_uf)
            new_flashcards.append(new_uf)

    db.commit()

    # Tworzenie nowej sesji
    new_session = StudySession(
        user_id=current_user.id_,
        deck_id=int(deck.id),
        started_at=datetime.utcnow()
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    logger.info(f"Utworzono sesję nauki z ID={new_session.id}")
    return new_session


@router.get("/next_flashcard/{session_id}/", response_model=FlashcardRead)
def get_next_flashcard(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Pobiera następny flashcard do nauki zgodnie z algorytmem SM2.
    """
    logger.info(f"Pobieranie następnej fiszki dla sesji_id={session_id} przez user_id={current_user.id_}")

    session = db.query(StudySession).filter(
        StudySession.id == session_id,
        StudySession.user_id == current_user.id_
    ).first()
    if not session:
        logger.error(f"Sesja z ID={session_id} nie znaleziono dla użytkownika.")
        raise HTTPException(status_code=404, detail="Sesja nauki nie znaleziona.")

    # Pobierz UserFlashcards, które są do przeglądu
    today = datetime.utcnow()
    user_flashcard = (
        db.query(UserFlashcard)
        .filter(
            UserFlashcard.user_id == current_user.id_,
            UserFlashcard.flashcard_id.in_([fc.id for fc in session.deck.flashcards]),
            UserFlashcard.next_review <= today
        )
        .order_by(UserFlashcard.next_review.asc())
        .first()
    )

    if not user_flashcard:
        logger.info("Nie ma więcej fiszek do nauki na dziś.")
        raise HTTPException(status_code=404, detail="Nie ma więcej fiszek do nauki na dziś.")

    flashcard = db.query(Flashcard).filter(Flashcard.id == user_flashcard.flashcard_id).first()

    if not flashcard:
        logger.error(f"Fiszka z ID={user_flashcard.flashcard_id} nie istnieje.")
        raise HTTPException(status_code=404, detail="Fiszka nie znaleziona.")

    logger.debug(f"Pobrano fiszkę ID={flashcard.id} do nauki.")
    return flashcard  # FastAPI automatycznie zrzutuje to do FlashcardRead (dzięki orm_mode).


@router.post("/record_review/{session_id}/", response_model=StudyRecordRead, status_code=201)
def record_flashcard_review(
    session_id: int,
    record_create: StudyRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Rejestruje ocenę użytkownika dla danej fiszki i aktualizuje dane SM2.
    """
    logger.info(
        f"Rejestrowanie oceny dla sesji_id={session_id}, user_flashcard_id={record_create.user_flashcard_id}, "
        f"rating={record_create.rating} przez user_id={current_user.id_}"
    )

    session = db.query(StudySession).filter(
        StudySession.id == session_id,
        StudySession.user_id == current_user.id_
    ).first()
    if not session:
        logger.error(f"Sesja z ID={session_id} nie znaleziono dla użytkownika.")
        raise HTTPException(status_code=404, detail="Sesja nauki nie znaleziona.")

    user_flashcard = db.query(UserFlashcard).filter(
        UserFlashcard.id == record_create.user_flashcard_id,
        UserFlashcard.user_id == current_user.id_,
        UserFlashcard.flashcard_id.in_([fc.id for fc in session.deck.flashcards])
    ).first()
    if not user_flashcard:
        logger.error(
            f"UserFlashcard z ID={record_create.user_flashcard_id} nie znaleziony w decku ID={session.deck_id}."
        )
        raise HTTPException(status_code=404, detail="Fiszka nie znaleziona.")

    # Tworzenie rekordu przeglądu
    study_record = StudyRecord(
        session_id=session.id,
        user_flashcard_id=int(user_flashcard.id),
        rating=record_create.rating,
        reviewed_at=datetime.utcnow()
    )
    db.add(study_record)

    # Aktualizacja danych SM2
    if record_create.rating < 3:
        user_flashcard.repetitions = 0
        user_flashcard.interval = 1
    else:
        if user_flashcard.repetitions == 0:
            user_flashcard.interval = 1
        elif user_flashcard.repetitions == 1:
            user_flashcard.interval = 6
        else:
            user_flashcard.interval = int(user_flashcard.interval * user_flashcard.ef)
        user_flashcard.repetitions += 1

    # Aktualizacja Easiness Factor (EF)
    user_flashcard.ef = user_flashcard.ef + (
        0.1 - (5 - record_create.rating) * (0.08 + (5 - record_create.rating) * 0.02)
    )
    if user_flashcard.ef < 1.3:
        user_flashcard.ef = 1.3

    # Ustawienie daty następnej powtórki
    user_flashcard.next_review = datetime.utcnow() + timedelta(days=user_flashcard.interval)

    db.commit()
    db.refresh(study_record)

    logger.info(f"Zaktualizowano dane SM2 dla UserFlashcard ID={user_flashcard.id}")
    return study_record


@router.get("/sessions/", response_model=List[StudySessionRead])
def get_study_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Pobiera wszystkie sesje nauki użytkownika.
    """
    logger.info(f"Pobieranie wszystkich sesji nauki dla user_id={current_user.id_}")
    sessions = db.query(StudySession).filter(StudySession.user_id == current_user.id_).all()
    return sessions


@router.get("/session/{session_id}/records/", response_model=List[StudyRecordRead])
def get_study_records(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Pobiera wszystkie rekordy przeglądu dla danej sesji nauki.
    """
    logger.info(f"Pobieranie rekordów przeglądu dla sesji_id={session_id} przez user_id={current_user.id_}")
    session = db.query(StudySession).filter(
        StudySession.id == session_id,
        StudySession.user_id == current_user.id_
    ).first()
    if not session:
        logger.error(f"Sesja z ID={session_id} nie znaleziono dla użytkownika.")
        raise HTTPException(status_code=404, detail="Sesja nauki nie znaleziona.")

    records = db.query(StudyRecord).filter(StudyRecord.session_id == session_id).all()
    return records
