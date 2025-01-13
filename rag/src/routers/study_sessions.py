from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List
import logging

from ..dependencies import get_db
from ..auth import get_current_user
from ..models import (
    StudySession, StudyRecord, UserFlashcard,
    Flashcard, Deck, User
)
from ..schemas import (
    StudySessionCreate, StudySessionRead,
    StudyRecordCreate, StudyRecordRead, FlashcardRead
)
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)


class BulkRatingItem(BaseModel):
    """Single rating item for bulk SM2 update."""
    flashcard_id: int
    rating: int
    answered_at: datetime


class BulkRecordData(BaseModel):
    """The shape of the JSON for bulk_record."""
    deck_id: int
    ratings: List[BulkRatingItem]


@router.post("/", response_model=StudySessionRead, status_code=201)
def create_study_session(
    session_create: StudySessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Creates a new study session for the given deck (optional immediate SM2 usage).
    """
    logger.info(f"Creating study session for deck_id={session_create.deck_id}, user_id={current_user.id_}")

    # Ensure deck belongs to user. Watch out if deck.user_id is TEXT in DB
    deck = db.query(Deck).filter(
        Deck.id == session_create.deck_id,
        Deck.user_id == str(current_user.id_)
    ).first()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found or doesn't belong to user.")

    # Initialize userFlashcards if needed
    user_flashcards = db.query(UserFlashcard).filter(
        UserFlashcard.user_id == current_user.id_,
        UserFlashcard.flashcard_id.in_([fc.id for fc in deck.flashcards])
    ).all()
    existing_ids = {uf.flashcard_id for uf in user_flashcards}
    new_ufs = []
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
            new_ufs.append(new_uf)

    db.commit()  # to persist any new user_flashcards

    # Create new session
    new_session = StudySession(
        user_id=current_user.id_,
        deck_id=deck.id,
        started_at=datetime.utcnow()
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    logger.info(f"StudySession created, ID={new_session.id}")
    return new_session


@router.get("/next_flashcard/{session_id}/", response_model=FlashcardRead)
def get_next_flashcard(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Gets the next flashcard for immediate SM2 usage (optional endpoint).
    """
    logger.info(f"next_flashcard session={session_id}, user_id={current_user.id_}")

    session = db.query(StudySession).filter(
        StudySession.id == session_id,
        StudySession.user_id == current_user.id_
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    deck = session.deck
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found.")

    now = datetime.utcnow()
    uf = db.query(UserFlashcard).filter(
        UserFlashcard.user_id == current_user.id_,
        UserFlashcard.flashcard_id.in_([f.id for f in deck.flashcards]),
        UserFlashcard.next_review <= now
    ).order_by(UserFlashcard.next_review.asc()).first()

    if not uf:
        raise HTTPException(status_code=404, detail="No more cards to study today.")

    flashcard = db.query(Flashcard).filter(Flashcard.id == uf.flashcard_id).first()
    if not flashcard:
        raise HTTPException(status_code=404, detail="Flashcard not found.")

    return flashcard


@router.post("/record_review/{session_id}/", response_model=StudyRecordRead, status_code=201)
def record_flashcard_review(
    session_id: int,
    record_create: StudyRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Saves rating for a single flashcard in immediate mode.
    """
    logger.info(f"record_review session={session_id}, user_id={current_user.id_}, rating={record_create.rating}")

    session = db.query(StudySession).filter(
        StudySession.id == session_id,
        StudySession.user_id == current_user.id_
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    deck = session.deck
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")

    uf = db.query(UserFlashcard).filter(
        UserFlashcard.id == record_create.user_flashcard_id,
        UserFlashcard.user_id == current_user.id_,
        UserFlashcard.flashcard_id.in_([f.id for f in deck.flashcards])
    ).first()
    if not uf:
        raise HTTPException(status_code=404, detail="Flashcard not found for this user/deck")

    # Create StudyRecord
    study_record = StudyRecord(
        session_id=session.id,
        user_flashcard_id=uf.id,
        rating=record_create.rating,
        reviewed_at=datetime.utcnow()
    )
    db.add(study_record)

    # Update SM2
    _update_sm2(uf, record_create.rating)

    # Make sure SQLAlchemy sees the changes on user_flashcards
    db.add(uf)  # <--- ensure we re-attach if not recognized

    db.commit()
    db.refresh(study_record)

    logger.info(f"record_review saved. study_record_id={study_record.id}, updated user_flashcard_id={uf.id}")
    return study_record


def _update_sm2(user_flashcard: UserFlashcard, rating: int):
    """
    Simple SM2-like update:
      - if rating <3: reset to interval=1, repetitions=0
      - else repetitions++ and interval grows
      - EF adjusted
      - next_review = now + interval days
    """
    if rating < 3:
        # "Hard"
        user_flashcard.repetitions = 0
        user_flashcard.interval = 1
    else:
        # "Good" or "Easy"
        if user_flashcard.repetitions == 0:
            user_flashcard.interval = 1
        elif user_flashcard.repetitions == 1:
            user_flashcard.interval = 6
        else:
            user_flashcard.interval = int(user_flashcard.interval * user_flashcard.ef)
        user_flashcard.repetitions += 1

    # EF adjust
    user_flashcard.ef += (0.1 - (5 - rating) * (0.08 + (5 - rating) * 0.02))
    if user_flashcard.ef < 1.3:
        user_flashcard.ef = 1.3

    user_flashcard.next_review = datetime.utcnow() + timedelta(days=user_flashcard.interval)


@router.post("/bulk_record", status_code=201)
def bulk_record(
    data: BulkRecordData,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Bulk save ratings & update SM2 for the given deck.
    """
    logger.info(f"bulk_record deck_id={data.deck_id}, user_id={current_user.id_}")

    # -- (1) Validate deck ownership
    # Sprawdź, czy deck istnieje i należy do aktualnie zalogowanego usera.
    # Jeśli current_user.id_ jest już int, rzutowanie niepotrzebne.
    # Gdyby był string, zrób: int(current_user.id_)
    deck = db.query(Deck).filter(
        Deck.id == data.deck_id,
        Deck.user_id == str(current_user.id_)
    ).first()
    if not deck:
        raise HTTPException(
            status_code=404,
            detail="Deck not found or doesn't belong to user."
        )

    # -- (2) Create a new study session
    new_session = StudySession(
        user_id=current_user.id_,
        deck_id=deck.id,
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow()
    )
    db.add(new_session)
    db.flush()  # wypełni new_session.id

    # -- (3) Pobierz userFlashcards (mapowanie flashcard_id -> userFlashcard).
    # Klucz: porównanie user_id do current_user.id_
    user_flashcards = db.query(UserFlashcard).filter(
        UserFlashcard.user_id == current_user.id_,
        UserFlashcard.flashcard_id.in_([f.id for f in deck.flashcards])
    ).all()

    uf_map = {uf.flashcard_id: uf for uf in user_flashcards}

    # -- (4) Dla każdej oceny twórz StudyRecord & aktualizuj SM2
    for item in data.ratings:
        uf = uf_map.get(item.flashcard_id)
        if not uf:
            logger.warning(
                f"Flashcard {item.flashcard_id} does not belong to user_id={current_user.id_}, skipping..."
            )
            continue

        study_record = StudyRecord(
            session_id=new_session.id,
            user_flashcard_id=uf.id,
            rating=item.rating,
            reviewed_at=item.answered_at
        )
        db.add(study_record)

        # zaktualizuj EF, interval itd.
        _update_sm2(uf, item.rating)

        # Upewnij się, że SQLAlchemy widzi zmiany w uf
        db.add(uf)

    # flush + commit
    db.flush()
    db.commit()

    logger.info(f"Bulk record saved. session_id={new_session.id}")
    return {
        "message": "Bulk record saved",
        "study_session_id": new_session.id
    }


@router.get("/next_review_date")
def get_next_review_date(
    deck_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns the earliest next_review date among all userFlashcards in the deck.
    """
    deck = db.query(Deck).filter(
        Deck.id == deck_id,
        Deck.user_id == str(current_user.id_)
    ).first()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found.")

    user_flashcards = db.query(UserFlashcard).filter(
        UserFlashcard.user_id == current_user.id_,
        UserFlashcard.flashcard_id.in_([fc.id for fc in deck.flashcards])
    ).all()
    if not user_flashcards:
        return {"next_review": None}

    earliest = min(uf.next_review for uf in user_flashcards)
    return {"next_review": earliest.isoformat()}


@router.get("/retake_cards/{deck_id}")
def retake_cards(
    deck_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns all flashcards in that deck whose EF <= 'the second smallest EF' in the deck.
      e.g. if EFs are [1.5, 1.7, 1.8, 2.4], second smallest is 1.7 => we return EF <= 1.7
    """
    deck = db.query(Deck).filter(
        Deck.id == deck_id,
        Deck.user_id == str(current_user.id_)
    ).first()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found.")

    user_flashcards = db.query(UserFlashcard).filter(
        UserFlashcard.user_id == current_user.id_,
        UserFlashcard.flashcard_id.in_([fc.id for fc in deck.flashcards])
    ).all()
    if not user_flashcards:
        return []

    # sort by EF ascending
    sorted_uf = sorted(user_flashcards, key=lambda uf: uf.ef)
    if len(sorted_uf) == 1:
        # only one card => second smallest does not exist, fallback = that single EF
        threshold = sorted_uf[0].ef
    else:
        threshold = sorted_uf[1].ef  # second smallest EF

    # filter by EF <= threshold
    chosen = [uf for uf in user_flashcards if uf.ef <= threshold + 0.1]

    # gather flashcards
    flashcard_ids = [uf.flashcard_id for uf in chosen]
    cards = db.query(Flashcard).filter(Flashcard.id.in_(flashcard_ids)).all()

    # build JSON
    result = []
    for c in cards:
        result.append({
            "id": c.id,
            "question": c.question,
            "answer": c.answer,
            "deck_id": c.deck_id,
            # if your Flashcard model has a 'media_url', add it:
            "media_url": getattr(c, 'media_url', None)
        })
    return result
