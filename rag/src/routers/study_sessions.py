# src/routers/study_sessions.py

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from ..models import StudySession, StudyRecord, UserFlashcard, Flashcard, Deck
from ..schemas import (
    StudySessionCreate, StudySessionRead,
    StudyRecordCreate, StudyRecordRead,
    FlashcardRead
)
from ..dependencies import get_db
from ..auth import get_current_user
from ..models import User
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)

# Modele do hurtowego zapisu
class BulkRatingItem(BaseModel):
    flashcard_id: int
    rating: int
    answered_at: datetime

class BulkRecordData(BaseModel):
    deck_id: int
    ratings: List[BulkRatingItem]


@router.post("/", response_model=StudySessionRead, status_code=201)
def create_study_session(
    session_create: StudySessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Tworzy nową sesję nauki dla użytkownika i wybranego decka.
    (Opcjonalne, jeśli ktoś chce natychmiastowy tryb SM2)
    """
    logger.info(f"Tworzenie sesji nauki deck_id={session_create.deck_id}, user_id={current_user.id_}")

    deck = db.query(Deck).filter(
        Deck.id == session_create.deck_id,
        Deck.user_id == str(current_user.id_)
    ).first()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck nie znaleziony")

    # Inicjalizacja userFlashcards
    user_flashcards = db.query(UserFlashcard).filter(
        UserFlashcard.user_id == current_user.id_,
        UserFlashcard.flashcard_id.in_([fc.id for fc in deck.flashcards])
    ).all()
    existing_ids = {uf.flashcard_id for uf in user_flashcards}
    for fc in deck.flashcards:
        if fc.id not in existing_ids:
            new_uf = UserFlashcard(
                user_id=current_user.id_,
                flashcard_id=fc.id,
                ef=2.5,
                interval=0,
                repetitions=0,
                next_review=datetime.utcnow()
            )
            db.add(new_uf)
    db.commit()

    new_session = StudySession(
        user_id=current_user.id_,
        deck_id=deck.id,
        started_at=datetime.utcnow()
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session


@router.get("/next_flashcard/{session_id}/", response_model=FlashcardRead)
def get_next_flashcard(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Pobiera następną fiszkę do nauki w trybie natychmiastowym.
    """
    logger.info(f"next_flashcard session={session_id}, user_id={current_user.id_}")

    session = db.query(StudySession).filter(
        StudySession.id == session_id,
        StudySession.user_id == current_user.id_
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sesja nie znaleziona")

    deck = session.deck
    if not deck:
        raise HTTPException(status_code=404, detail="Deck nie znaleziony")

    now = datetime.utcnow()
    uf = db.query(UserFlashcard).filter(
        UserFlashcard.user_id == current_user.id_,
        UserFlashcard.flashcard_id.in_([f.id for f in deck.flashcards]),
        UserFlashcard.next_review <= now
    ).order_by(UserFlashcard.next_review.asc()).first()

    if not uf:
        raise HTTPException(status_code=404, detail="Nie ma więcej fiszek do nauki na dziś.")

    flashcard = db.query(Flashcard).filter(Flashcard.id == uf.flashcard_id).first()
    if not flashcard:
        raise HTTPException(status_code=404, detail="Fiszka nie znaleziona")
    return flashcard


@router.post("/record_review/{session_id}/", response_model=StudyRecordRead, status_code=201)
def record_flashcard_review(
    session_id: int,
    record_create: StudyRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Natychmiastowy zapis oceny jednej fiszki
    """
    logger.info(f"record_review session={session_id}, user_id={current_user.id_}, rating={record_create.rating}")

    session = db.query(StudySession).filter(
        StudySession.id == session_id,
        StudySession.user_id == current_user.id_
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sesja nie znaleziona")

    deck = session.deck
    if not deck:
        raise HTTPException(status_code=404, detail="Deck nie znaleziony")

    uf = db.query(UserFlashcard).filter(
        UserFlashcard.id == record_create.user_flashcard_id,
        UserFlashcard.user_id == current_user.id_,
        UserFlashcard.flashcard_id.in_([f.id for f in deck.flashcards])
    ).first()
    if not uf:
        raise HTTPException(status_code=404, detail="Fiszka nie znaleziona")

    study_record = StudyRecord(
        session_id=session.id,
        user_flashcard_id=uf.id,
        rating=record_create.rating,
        reviewed_at=datetime.utcnow()
    )
    db.add(study_record)

    _update_sm2(uf, record_create.rating)
    db.commit()
    db.refresh(study_record)
    return study_record


@router.post("/bulk_record", status_code=201)
def bulk_record(
    data: BulkRecordData,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Hurtowy zapis ocen i aktualizacja SM2
    """
    logger.info(f"bulk_record deck_id={data.deck_id}, user_id={current_user.id_}")

    deck = db.query(Deck).filter(
        Deck.id == data.deck_id,
        Deck.user_id == str(current_user.id_)
    ).first()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck nie znaleziony")

    new_session = StudySession(
        user_id=current_user.id_,
        deck_id=deck.id,
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow()
    )
    db.add(new_session)
    db.flush()

    # Mapa flashcard_id -> userFlashcard
    user_flashcards = db.query(UserFlashcard).filter(
        UserFlashcard.user_id == current_user.id_,
        UserFlashcard.flashcard_id.in_([f.id for f in deck.flashcards])
    ).all()
    uf_map = {uf.flashcard_id: uf for uf in user_flashcards}

    for item in data.ratings:
        uf = uf_map.get(item.flashcard_id)
        if not uf:
            logger.warning(f"Fiszka {item.flashcard_id} nie należy do user_id={current_user.id_}")
            continue

        study_record = StudyRecord(
            session_id=new_session.id,
            user_flashcard_id=uf.id,
            rating=item.rating,
            reviewed_at=item.answered_at
        )
        db.add(study_record)
        _update_sm2(uf, item.rating)

    db.commit()
    logger.info(f"Hurtowy zapis zakończony, session_id={new_session.id}")
    return {"message": "Bulk record saved", "study_session_id": new_session.id}


def _update_sm2(user_flashcard: UserFlashcard, rating: int):
    """
    Prosty SM2: rating<3 reset, >=3 => interval rośnie, EF rośnie/spada
    """
    if rating < 3:
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

    user_flashcard.ef += (0.1 - (5 - rating)*(0.08 + (5 - rating)*0.02))
    if user_flashcard.ef < 1.3:
        user_flashcard.ef = 1.3

    user_flashcard.next_review = datetime.utcnow() + timedelta(days=user_flashcard.interval)


@router.get("/next_review_date")
def get_next_review_date(
    deck_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Zwraca najwcześniejszy next_review w danym decku
    """
    deck = db.query(Deck).filter(
        Deck.id == deck_id,
        Deck.user_id == str(current_user.id_)
    ).first()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")

    user_flashcards = db.query(UserFlashcard).filter(
        UserFlashcard.user_id == current_user.id_,
        UserFlashcard.flashcard_id.in_([fc.id for fc in deck.flashcards])
    ).all()
    if not user_flashcards:
        return {"next_review": None}

    earliest = min(uf.next_review for uf in user_flashcards)
    return {"next_review": earliest.isoformat()}


@router.get("/retake_cards")
def retake_cards(
    deck_id: int,
    max_ef: float,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Zwraca listę fiszek (Flashcard) z EF <= max_ef,
    by user mógł je przećwiczyć dobrowolnie
    """
    deck = db.query(Deck).filter(
        Deck.id == deck_id,
        Deck.user_id == str(current_user.id_)
    ).first()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")

    # Znajdź userFlashcards z EF <= max_ef
    user_flashcards = db.query(UserFlashcard).filter(
        UserFlashcard.user_id == current_user.id_,
        UserFlashcard.flashcard_id.in_([f.id for f in deck.flashcards]),
        UserFlashcard.ef <= max_ef
    ).all()
    if not user_flashcards:
        return []

    flashcard_ids = [uf.flashcard_id for uf in user_flashcards]
    cards = db.query(Flashcard).filter(Flashcard.id.in_(flashcard_ids)).all()

    result = []
    for c in cards:
        result.append({
            "id": c.id,
            "question": c.question,
            "answer": c.answer,
            "deck_id": c.deck_id,
            "media_url": c.media_url  # jeśli w modelu jest media_url
        })
    return result
