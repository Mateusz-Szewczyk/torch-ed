# src/routers/study_sessions.py

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.exc import SQLAlchemyError
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

from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set logging level to DEBUG for detailed logs
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

class BulkRatingItem(BaseModel):
    """Single rating item for bulk SM2 update."""
    flashcard_id: int
    rating: int
    answered_at: datetime

class BulkRecordData(BaseModel):
    """The shape of the JSON for bulk_record."""
    session_id: int
    deck_id: int
    ratings: List[BulkRatingItem]

def _update_sm2(user_flashcard: UserFlashcard, rating: int):
    """
    Simple SM2-like update:
      - if rating <3: reset to interval=1, repetitions=0
      - else repetitions++ and interval grows
      - EF adjusted
      - next_review = now + interval days
    """
    logger.debug(f"Updating SM2 for UserFlashcard id={user_flashcard.id}, rating={rating}")
    if rating < 3:
        # "Hard"
        user_flashcard.repetitions = 0
        user_flashcard.interval = 1
        logger.debug("Rating < 3: Reset repetitions to 0 and interval to 1 day.")
    else:
        # "Good" or "Easy"
        if user_flashcard.repetitions == 0:
            user_flashcard.interval = 1
            logger.debug("Repetitions == 0: Set interval to 1 day.")
        elif user_flashcard.repetitions == 1:
            user_flashcard.interval = 6
            logger.debug("Repetitions == 1: Set interval to 6 days.")
        else:
            user_flashcard.interval = int(user_flashcard.interval * user_flashcard.ef)
            logger.debug(f"Repetitions > 1: Updated interval to {user_flashcard.interval} days based on EF.")
        user_flashcard.repetitions += 1
        logger.debug(f"Increased repetitions to {user_flashcard.repetitions}")

    # EF adjust
    user_flashcard.ef += (0.1 - (5 - rating) * (0.08 + (5 - rating) * 0.02))
    if user_flashcard.ef < 1.3:
        user_flashcard.ef = 1.3
        logger.debug("EF below 1.3: Reset to 1.3.")
    else:
        logger.debug(f"Adjusted EF to {user_flashcard.ef}")

    user_flashcard.next_review = datetime.utcnow() + timedelta(days=user_flashcard.interval)
    logger.debug(f"Next review scheduled for {user_flashcard.next_review}")

@router.post("/bulk_record", response_model=dict, status_code=201)
def bulk_record(
    data: BulkRecordData,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Bulk save ratings & update SM2 for the given session and deck.
    """
    logger.info(f"bulk_record session_id={data.session_id}, deck_id={data.deck_id}, user_id={current_user.id_}")

    # -- (1) Validate deck ownership
    deck = db.query(Deck).filter(
        Deck.id == data.deck_id,
        Deck.user_id == current_user.id_
    ).first()
    if not deck:
        logger.error(f"Deck id={data.deck_id} not found or does not belong to user_id={current_user.id_}")
        raise HTTPException(
            status_code=404,
            detail="Deck not found or doesn't belong to user."
        )
    logger.debug(f"Deck found: {deck}")

    # -- (2) Validate session
    session = db.query(StudySession).filter(
        StudySession.id == data.session_id,
        StudySession.user_id == current_user.id_,
        StudySession.deck_id == data.deck_id
    ).first()
    if not session:
        logger.error(f"StudySession id={data.session_id} not found or does not belong to user_id={current_user.id_}")
        raise HTTPException(
            status_code=404,
            detail="Study session not found or doesn't belong to user."
        )
    logger.debug(f"StudySession found: {session}")

    # -- (3) Pobierz userFlashcards (mapowanie flashcard_id -> userFlashcard).
    user_flashcards = db.query(UserFlashcard).filter(
        UserFlashcard.user_id == current_user.id_,
        UserFlashcard.flashcard_id.in_([f.id for f in deck.flashcards])
    ).all()
    logger.debug(f"Found {len(user_flashcards)} UserFlashcard entries for user_id={current_user.id_} and deck_id={deck.id}")

    # Mapowanie flashcard_id -> UserFlashcard
    uf_map = {uf.flashcard_id: uf for uf in user_flashcards}

    # -- (4) Inicjalizacja brakujących UserFlashcard
    missing_flashcard_ids = [fc.id for fc in deck.flashcards if fc.id not in uf_map]
    if missing_flashcard_ids:
        logger.info(f"Initializing {len(missing_flashcard_ids)} missing UserFlashcard entries for user_id={current_user.id_}")
        new_ufs = []
        for fc_id in missing_flashcard_ids:
            new_uf = UserFlashcard(
                user_id=current_user.id_,
                flashcard_id=fc_id,
                ef=2.5,
                interval=0,
                repetitions=0,
                next_review=datetime.utcnow()
            )
            db.add(new_uf)
            new_ufs.append(new_uf)
            logger.debug(f"Added new UserFlashcard: {new_uf}")
        db.flush()  # Persist new UserFlashcards
        # Aktualizuj mapę
        user_flashcards += new_ufs
        for uf in new_ufs:
            uf_map[uf.flashcard_id] = uf
        logger.info(f"Persisted {len(new_ufs)} new UserFlashcard entries.")

    # -- (5) Dla każdej oceny twórz StudyRecord & aktualizuj SM2
    for item in data.ratings:
        uf = uf_map.get(item.flashcard_id)
        if not uf:
            logger.warning(
                f"Flashcard {item.flashcard_id} does not belong to user_id={current_user.id_}, skipping..."
            )
            continue

        study_record = StudyRecord(
            session_id=session.id,
            user_flashcard_id=uf.id,
            rating=item.rating,
            reviewed_at=item.answered_at
        )
        db.add(study_record)
        logger.debug(f"Added StudyRecord: {study_record}")

        # Zaktualizuj EF, interval itd.
        _update_sm2(uf, item.rating)
        logger.debug(f"Updated UserFlashcard after SM2: {uf}")

        # Upewnij się, że SQLAlchemy widzi zmiany w uf
        db.add(uf)

    try:
        # Update session completed_at
        session.completed_at = datetime.utcnow()
        db.add(session)

        # Flush + commit
        db.flush()
        db.commit()
        logger.info(f"Bulk record saved. session_id={session.id}")
    except SQLAlchemyError as e:
        logger.error(f"Błąd podczas commitowania transakcji: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal Server Error")

    return {
        "message": "Bulk record saved",
        "study_session_id": session.id
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
    logger.info(f"Fetching next_review_date for deck_id={deck_id}, user_id={current_user.id_}")

    deck = db.query(Deck).filter(
        Deck.id == deck_id,
        Deck.user_id == current_user.id_
    ).first()
    if not deck:
        logger.error(f"Deck id={deck_id} not found for user_id={current_user.id_}")
        raise HTTPException(status_code=404, detail="Deck not found.")

    user_flashcards = db.query(UserFlashcard).filter(
        UserFlashcard.user_id == current_user.id_,
        UserFlashcard.flashcard_id.in_([fc.id for fc in deck.flashcards])
    ).all()
    if not user_flashcards:
        logger.info(f"No UserFlashcards found for deck_id={deck_id} and user_id={current_user.id_}")
        return {"next_review": None}

    earliest = min(uf.next_review for uf in user_flashcards)
    logger.debug(f"Earliest next_review date: {earliest}")
    return {"next_review": earliest.isoformat()}


class StartStudySessionRequest(BaseModel):
    """Request model for starting a study session."""
    deck_id: int


class StudySessionResponse(BaseModel):
    """Response model for starting a study session."""
    study_session_id: int
    available_cards: List[dict]


@router.post("/start", response_model=StudySessionResponse, status_code=201)
def start_study_session(
    request: StartStudySessionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Starts a new study session for the given deck if there are available flashcards to study.
    Returns the session_id and available cards to study.
    If no flashcards are available, returns the next scheduled session date.
    """
    deck_id = request.deck_id
    logger.info(f"Starting study session for deck_id={deck_id}, user_id={current_user.id_}")

    # -- (1) Validate deck ownership
    deck = db.query(Deck).filter(
        Deck.id == deck_id,
        Deck.user_id == current_user.id_
    ).first()
    if not deck:
        logger.error(f"Deck id={deck_id} not found or does not belong to user_id={current_user.id_}")
        raise HTTPException(status_code=404, detail="Deck not found or doesn't belong to user.")

    logger.debug(f"Deck found: {deck}")

    # -- (2) Initialize missing UserFlashcards
    user_flashcards = db.query(UserFlashcard).filter(
        UserFlashcard.user_id == current_user.id_,
        UserFlashcard.flashcard_id.in_([fc.id for fc in deck.flashcards])
    ).all()
    logger.debug(f"Found {len(user_flashcards)} UserFlashcard entries for user_id={current_user.id_} and deck_id={deck.id}")

    # Map flashcard_id -> UserFlashcard
    uf_map = {uf.flashcard_id: uf for uf in user_flashcards}

    # -- (3) Initialize missing UserFlashcards
    missing_flashcard_ids = [fc.id for fc in deck.flashcards if fc.id not in uf_map]
    if missing_flashcard_ids:
        logger.info(f"Initializing {len(missing_flashcard_ids)} missing UserFlashcard entries for user_id={current_user.id_}")
        new_ufs = []
        for fc_id in missing_flashcard_ids:
            new_uf = UserFlashcard(
                user_id=current_user.id_,
                flashcard_id=fc_id,
                ef=2.5,
                interval=0,
                repetitions=0,
                next_review=datetime.utcnow()
            )
            db.add(new_uf)
            new_ufs.append(new_uf)
            logger.debug(f"Added new UserFlashcard: {new_uf}")
        db.flush()  # Persist new UserFlashcards
        # Update map
        user_flashcards += new_ufs
        for uf in new_ufs:
            uf_map[uf.flashcard_id] = uf
        logger.info(f"Persisted {len(new_ufs)} new UserFlashcard entries.")

    # -- (4) Fetch available flashcards: next_review <= now()
    now = datetime.utcnow()
    available_ufs = [uf for uf in user_flashcards if uf.next_review <= now]
    logger.debug(f"Found {len(available_ufs)} available UserFlashcards for study.")

    if not available_ufs:
        # Find the earliest next_review date among UserFlashcards
        next_reviews = [uf.next_review for uf in user_flashcards if uf.next_review > now]
        next_session_date = min(next_reviews) if next_reviews else None

        logger.info("No available flashcards to study at this time.")
        return {
            "study_session_id": None,
            "available_cards": [],
            "next_session_date": next_session_date.isoformat() if next_session_date else None
        }

    # -- (5) Create a new StudySession
    new_session = StudySession(
        user_id=current_user.id_,
        deck_id=deck.id,
        started_at=now,
        completed_at=None
    )

    db.add(new_session)
    db.flush()  # Flush to get new_session.id
    logger.debug(f"Created StudySession with id={new_session.id}")

    # -- (6) Convert available UserFlashcards to Flashcards
    flashcard_ids = [uf.flashcard_id for uf in available_ufs]
    available_cards = db.query(Flashcard).filter(Flashcard.id.in_(flashcard_ids)).all()

    # -- (7) Build the response
    result = []
    for c in available_cards:
        card_dict = {
            "id": c.id,
            "question": c.question,
            "answer": c.answer,
            "deck_id": c.deck_id,
            "media_url": getattr(c, 'media_url', None)
        }
        result.append(card_dict)
    logger.debug(f"Available cards for study session {new_session.id}: {result}")

    # **Commit the transaction to save StudySession**
    try:
        db.commit()
        logger.info(f"StudySession id={new_session.id} committed to the database.")
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error committing StudySession: {e}")
        raise HTTPException(status_code=500, detail="Failed to start study session.")

    return {
        "study_session_id": new_session.id,
        "available_cards": result,
        "next_session_date": None
    }


@router.get("/retake_session", response_model=List[dict], status_code=200)
def retake_session(
    deck_id: int = Query(..., description="ID of the deck to retake session from"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retake flashcards from the latest session for the given deck and user.
    """
    logger.info(f"Fetching retake_session for deck_id={deck_id}, user_id={current_user.id_}")

    # Find the latest StudySession for the deck and user
    session = db.query(StudySession).filter(
        StudySession.deck_id == deck_id,
        StudySession.user_id == current_user.id_,
        StudySession.completed_at.isnot(None)  # Only completed sessions
    ).order_by(StudySession.started_at.desc()).first()

    if not session:
        logger.error(f"No completed StudySession found for deck_id={deck_id}, user_id={current_user.id_}")
        raise HTTPException(status_code=404, detail="No completed study session found for this deck.")

    # Fetch study records for this session
    study_records = db.query(StudyRecord).filter(
        StudyRecord.session_id == session.id
    ).all()

    if not study_records:
        logger.info(f"No StudyRecords found for session_id={session.id}")
        return []

    # Get UserFlashcard IDs
    user_flashcard_ids = {sr.user_flashcard_id for sr in study_records}

    # Fetch UserFlashcards
    user_flashcards = db.query(UserFlashcard).filter(
        UserFlashcard.id.in_(user_flashcard_ids),
        UserFlashcard.user_id == current_user.id_
    ).all()

    if not user_flashcards:
        return []

    # Sort by EF ascending
    sorted_uf = sorted(user_flashcards, key=lambda uf: uf.ef)
    if len(sorted_uf) == 1:
        threshold = sorted_uf[0].ef
        logger.debug(f"Only one UserFlashcard found. Using EF threshold={threshold}")
    else:
        threshold = sorted_uf[1].ef  # second smallest EF
        logger.debug(f"Second smallest EF={threshold}")

    # Filter by EF <= threshold + 0.1
    chosen = [uf for uf in user_flashcards if uf.ef <= threshold + 0.1]
    logger.debug(f"Chosen {len(chosen)} UserFlashcards with EF <= {threshold + 0.1}")

    # Gather flashcards
    flashcard_ids = [uf.flashcard_id for uf in chosen]
    cards = db.query(Flashcard).filter(Flashcard.id.in_(flashcard_ids)).all()

    # Build JSON
    result = []
    for c in cards:
        result.append({
            "id": c.id,
            "question": c.question,
            "answer": c.answer,
            "deck_id": c.deck_id,
            "media_url": getattr(c, 'media_url', None)
        })
    logger.debug(f"Retake cards for session {session.id}: {result}")
    return result


@router.get("/retake_hard_cards", response_model=List[dict], status_code=200)
def retake_hard_cards(
    deck_id: int = Query(..., description="ID of the deck to retake hard cards from"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retake hard flashcards from the given deck:
    - Prefer flashcards with EF <= 1.8.
    - If none, select all flashcards with the two lowest distinct EF values.
    - Allows retake even if no hard flashcards are found.
    """
    logger.info(f"Fetching retake_hard_cards for deck_id={deck_id}, user_id={current_user.id_}")

    # Validate deck ownership
    deck = db.query(Deck).filter(
        Deck.id == deck_id,
        Deck.user_id == current_user.id_
    ).first()
    if not deck:
        logger.error(f"Deck id={deck_id} not found or does not belong to user_id={current_user.id_}")
        raise HTTPException(status_code=404, detail="Deck not found or doesn't belong to user.")

    # Current time
    now = datetime.utcnow()

    # Fetch UserFlashcards with EF <= 1.8 and next_review > now()
    hard_user_flashcards = db.query(UserFlashcard).filter(
        UserFlashcard.user_id == current_user.id_,
        UserFlashcard.flashcard_id.in_([fc.id for fc in deck.flashcards]),
        UserFlashcard.ef <= 1.8,
        UserFlashcard.next_review > now
    ).order_by(UserFlashcard.ef.asc()).all()

    logger.debug(f"Found {len(hard_user_flashcards)} hard UserFlashcards with EF <= 1.8.")

    if hard_user_flashcards:
        # Gather flashcards
        flashcard_ids = [uf.flashcard_id for uf in hard_user_flashcards]
        cards = db.query(Flashcard).filter(Flashcard.id.in_(flashcard_ids)).all()

        # Build JSON response
        result = [{
            "id": c.id,
            "question": c.question,
            "answer": c.answer,
            "deck_id": c.deck_id,
            "media_url": getattr(c, 'media_url', None)
        } for c in cards]

        logger.debug(f"Retake hard cards (EF <= 1.8): {result}")
        return result
    else:
        # If no hard flashcards, select all flashcards with the two lowest distinct EF values
        # Fetch all UserFlashcards with next_review > now()
        user_flashcards = db.query(UserFlashcard).filter(
            UserFlashcard.user_id == current_user.id_,
            UserFlashcard.flashcard_id.in_([fc.id for fc in deck.flashcards]),
            UserFlashcard.next_review > now
        ).order_by(UserFlashcard.ef.asc()).all()

        if not user_flashcards:
            # No flashcards available for retake
            logger.info("No flashcards available for retake.")
            return []

        # Extract distinct EF values, sorted ascending
        distinct_efs = sorted({uf.ef for uf in user_flashcards})

        if not distinct_efs:
            logger.info("No distinct EF values found.")
            return []

        # Take the two lowest distinct EF values
        lowest_two_efs = distinct_efs[:2] if len(distinct_efs) >= 2 else distinct_efs

        logger.debug(f"Lowest two distinct EF values: {lowest_two_efs}")

        # Select all UserFlashcards with EF in the lowest two EF values
        chosen_user_flashcards = [
            uf for uf in user_flashcards if uf.ef in lowest_two_efs
        ]

        logger.debug(f"Chosen {len(chosen_user_flashcards)} UserFlashcards with EF in {lowest_two_efs}")

        # Gather flashcards
        flashcard_ids = [uf.flashcard_id for uf in chosen_user_flashcards]
        cards = db.query(Flashcard).filter(Flashcard.id.in_(flashcard_ids)).all()

        # Build JSON response
        result = [{
            "id": c.id,
            "question": c.question,
            "answer": c.answer,
            "deck_id": c.deck_id,
            "media_url": getattr(c, 'media_url', None)
        } for c in cards]

        logger.debug(f"Retake hard cards (two lowest EF values): {result}")
        return result
