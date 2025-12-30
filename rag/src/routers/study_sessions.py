# src/routers/study_sessions.py
from decimal import Decimal
from math import ceil

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import List, Optional
import logging

from ..dependencies import get_db
from ..auth import get_current_user
from ..models import (
    StudySession, StudyRecord, UserFlashcard,
    Flashcard, Deck, User
)
from .dashboard import invalidate_user_dashboard_cache

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


def _update_sm2(user_flashcard: UserFlashcard, rating: int) -> None:
    """
    Implementation of the SM-2 algorithm with 'torch-ed' modifications for overdue handling.

    Logic:
    - Calculates actual days since last review to credit overdue time (making the next interval larger if you remembered it after a long delay).
    - If rating < 3: Resets repetitions and interval to 1 (canonical SM-2).
    - If rating >= 3: Updates EF and calculates next interval based on effective previous interval.
    - Sets 'needs_again_today' flag if rating < 4 for immediate re-learning queues.
    """
    # Configuration for overdue credit (embedded)
    BETA = Decimal("0.5")  # Controls how much credit is given for overdue time (0.5 is moderate)
    MAX_RATIO = Decimal("10.0")  # Cap on how much longer the actual gap can be vs scheduled

    if not (0 <= rating <= 5):
        raise ValueError(f"Rating must be between 0 and 5, got {rating}")

    # 1. Determine current time (UTC)
    now = datetime.now(timezone.utc)

    # 2. Calculate actual days passed since the last review
    # If last_review is missing, assume it was reviewed on schedule (no overdue credit)
    scheduled_days = max(1, int(user_flashcard.interval) if user_flashcard.interval else 1)

    if user_flashcard.last_review is None:
        actual_days = scheduled_days
    else:
        # Calculate diff based on calendar dates to avoid time-of-day issues
        # Ensure last_review is timezone-aware for subtraction if needed
        last_review_date = user_flashcard.last_review.date()
        actual_days = max(1, (now.date() - last_review_date).days)

    # 3. Calculate 'Effective Previous Interval' (Credits some overdue time)
    # If actual <= scheduled, no bonus. If actual > scheduled, we scale the interval base.
    if actual_days <= scheduled_days:
        effective_prev = Decimal(str(scheduled_days))
    else:
        ratio = min(Decimal(str(actual_days)) / Decimal(str(scheduled_days)), MAX_RATIO)
        # detailed logic: credit = ratio^(-beta). As ratio grows, credit multiplier shrinks.
        credit_factor = ratio ** (-BETA)
        effective_prev = Decimal(str(scheduled_days)) + (
                    Decimal(str(actual_days)) - Decimal(str(scheduled_days))) * credit_factor

    # 4. Update Card State
    # Session-level flag: if rated < 4, it should be reviewed again today (learning step)
    # Note: Assuming 'needs_again_today' is a field on your model. If not, remove this line.
    if hasattr(user_flashcard, 'needs_again_today'):
        user_flashcard.needs_again_today = (rating < 4)

    if rating < 3:
        # Canonical SM-2: Reset repetitions and interval, but keep EF (don't punish difficulty for forgetting)
        user_flashcard.repetitions = 0
        user_flashcard.interval = 1
    else:
        # Success (Rating 3-5)

        # Update Easiness Factor (EF)
        # EF' = EF + (0.1 - (5-q) * (0.08 + (5-q) * 0.02))
        rating_decimal = Decimal(str(rating))
        ef_change = Decimal("0.1") - (Decimal("5.0") - rating_decimal) * (
                    Decimal("0.08") + (Decimal("5.0") - rating_decimal) * Decimal("0.02"))

        # Ensure user_flashcard.ef is Decimal
        current_ef = Decimal(str(user_flashcard.ef)) if not isinstance(user_flashcard.ef,
                                                                       Decimal) else user_flashcard.ef
        user_flashcard.ef = max(Decimal("1.3"), round(current_ef + ef_change, 2))

        # Calculate New Interval
        user_flashcard.repetitions += 1

        if user_flashcard.repetitions == 1:
            user_flashcard.interval = 1
        elif user_flashcard.repetitions == 2:
            user_flashcard.interval = 6
        else:
            # For n > 2, use the effective previous interval * EF
            ef_decimal = Decimal(str(user_flashcard.ef)) if not isinstance(user_flashcard.ef,
                                                                           Decimal) else user_flashcard.ef
            new_interval = effective_prev * ef_decimal
            user_flashcard.interval = max(1, int(ceil(float(new_interval))))

    # 5. Set Next Review Date
    user_flashcard.last_review = now.date()
    user_flashcard.next_review = now.date() + timedelta(days=user_flashcard.interval)


@router.post("/bulk_record", response_model=dict, status_code=201)
async def bulk_record(
        data: BulkRecordData,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    """
    Bulk save ratings & update SM2 for the given session and deck.
    """
    logger.info(f"bulk_record session_id={data.session_id}, deck_id={data.deck_id}, user_id={current_user.id_}")

    # -- (1) Validate deck ownership
    try:
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
    except Exception as e:
        logger.error(f"Error fetching Deck: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    # -- (2) Validate session
    try:
        session = db.query(StudySession).filter(
            StudySession.id == data.session_id,
            StudySession.user_id == current_user.id_,
            StudySession.deck_id == data.deck_id
        ).first()
        if not session:
            logger.error(
                f"StudySession id={data.session_id} not found or does not belong to user_id={current_user.id_}")
            raise HTTPException(
                status_code=404,
                detail="Study session not found or doesn't belong to user."
            )
        logger.debug(f"StudySession found: {session}")
    except Exception as e:
        logger.error(f"Error fetching StudySession: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    # -- (3) Pobierz userFlashcards (mapowanie flashcard_id -> userFlashcard).
    try:
        user_flashcards = db.query(UserFlashcard).filter(
            UserFlashcard.user_id == current_user.id_,
            UserFlashcard.flashcard_id.in_([fc.id for fc in deck.flashcards])
        ).all()
        logger.debug(
            f"Found {len(user_flashcards)} UserFlashcard entries for user_id={current_user.id_} and deck_id={deck.id}")
    except Exception as e:
        logger.error(f"Error fetching UserFlashcards: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    # Mapowanie flashcard_id -> UserFlashcard
    uf_map = {uf.flashcard_id: uf for uf in user_flashcards}

    # -- (4) Inicjalizacja brakujących UserFlashcard
    missing_flashcard_ids = [fc.id for fc in deck.flashcards if fc.id not in uf_map]
    if missing_flashcard_ids:
        logger.info(
            f"Initializing {len(missing_flashcard_ids)} missing UserFlashcard entries for user_id={current_user.id_}")
        new_ufs = []
        for fc_id in missing_flashcard_ids:
            new_uf = UserFlashcard(
                user_id=current_user.id_,
                flashcard_id=fc_id,
                ef=Decimal("2.5"),
                interval=0,
                repetitions=0,
                next_review=datetime.now(timezone.utc)
            )
            db.add(new_uf)
            new_ufs.append(new_uf)
            logger.debug(f"Added new UserFlashcard: {new_uf}")
        try:
            db.flush()  # Persist new UserFlashcards
            # Aktualizuj mapę
            user_flashcards += new_ufs
            for uf in new_ufs:
                uf_map[uf.flashcard_id] = uf
            logger.info(f"Persisted {len(new_ufs)} new UserFlashcard entries.")
        except Exception as e:
            logger.error(f"Error initializing UserFlashcards: {e}")
            db.rollback()
            raise HTTPException(status_code=500, detail="Failed to initialize UserFlashcards.")

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

        # Invalidate dashboard cache in background
        background_tasks.add_task(invalidate_user_dashboard_cache, current_user.id_)
        logger.debug(f"Scheduled dashboard cache invalidation for user {current_user.id_}")

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error saving bulk record: {e}")
        raise HTTPException(status_code=500, detail="Failed to save bulk record.")

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


@router.get("/overdue_stats")
def get_overdue_stats(
        deck_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Returns statistics about overdue flashcards for a given deck:
    - total_cards: total number of flashcards in the deck
    - overdue_cards: number of cards that are overdue (before today)
    - due_today: number of cards due today (including past hours today)
    - overdue_breakdown: breakdown by severity (slightly, moderately, very overdue)
    """
    logger.info(f"Fetching overdue_stats for deck_id={deck_id}, user_id={current_user.id_}")

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
        return {
            "total_cards": len(deck.flashcards),
            "overdue_cards": 0,
            "due_today": 0,
            "overdue_breakdown": {
                "slightly_overdue": 0,  # 1-2 days
                "moderately_overdue": 0,  # 3-7 days
                "very_overdue": 0  # >7 days
            }
        }

    # FIX #1: Use timezone-aware datetime
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    overdue_count = 0
    due_today_count = 0
    slightly_overdue = 0
    moderately_overdue = 0
    very_overdue = 0

    for uf in user_flashcards:
        # Ensure next_review is timezone-aware for comparison
        next_review = uf.next_review
        if next_review.tzinfo is None:
            next_review = next_review.replace(tzinfo=timezone.utc)

        # FIX #2: Separate overdue (past days) from due_today (today's range)
        # Overdue = cards scheduled before today
        if next_review < today_start:
            overdue_count += 1
            days_overdue = (now.date() - next_review.date()).days

            if days_overdue <= 2:
                slightly_overdue += 1
            elif days_overdue <= 7:
                moderately_overdue += 1
            else:
                very_overdue += 1

        # Due today = cards scheduled for any time today (past or future)
        if today_start <= next_review < today_end:
            due_today_count += 1

    stats = {
        "total_cards": len(user_flashcards),
        "overdue_cards": overdue_count,
        "due_today": due_today_count,
        "overdue_breakdown": {
            "slightly_overdue": slightly_overdue,
            "moderately_overdue": moderately_overdue,
            "very_overdue": very_overdue
        }
    }

    logger.debug(f"Overdue stats: {stats}")
    return stats


class StartStudySessionRequest(BaseModel):
    """Request model for starting a study session."""
    deck_id: int


class FlashcardResponse(BaseModel):
    id: int
    question: str
    answer: str
    deck_id: int
    media_url: Optional[str] = None
    repetitions: Optional[int] = None

    class Config:
        from_attributes = True


class StudySessionResponse(BaseModel):
    """Response model for starting a study session."""
    study_session_id: Optional[int] = None  # Teraz może być int lub None
    available_cards: List[FlashcardResponse]
    next_session_date: Optional[str] = None  # Dodane dla informacji o następnej sesji

    class Config:
        from_attributes = True


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
    logger.debug(
        f"Found {len(user_flashcards)} UserFlashcard entries for user_id={current_user.id_} and deck_id={deck.id}")

    # Map flashcard_id -> UserFlashcard
    uf_map = {uf.flashcard_id: uf for uf in user_flashcards}

    # -- (3) Initialize missing UserFlashcards
    missing_flashcard_ids = [fc.id for fc in deck.flashcards if fc.id not in uf_map]
    if missing_flashcard_ids:
        logger.info(
            f"Initializing {len(missing_flashcard_ids)} missing UserFlashcard entries for user_id={current_user.id_}")
        new_ufs = []
        for fc_id in missing_flashcard_ids:
            new_uf = UserFlashcard(
                user_id=current_user.id_,
                flashcard_id=fc_id,
                ef=Decimal("2.5"),
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

    # Sort by how overdue they are (most overdue first) to help users catch up efficiently
    available_ufs.sort(key=lambda uf: uf.next_review)

    logger.debug(f"Found {len(available_ufs)} available UserFlashcards for study (sorted by overdue date).")

    # Log overdue statistics for monitoring
    if available_ufs:
        most_overdue_days = (now - available_ufs[0].next_review).days
        least_overdue_days = (now - available_ufs[-1].next_review).days
        logger.info(f"Overdue range: {most_overdue_days} to {least_overdue_days} days")

    if not available_ufs:
        # Find the earliest next_review date among UserFlashcards
        next_reviews = [uf.next_review for uf in user_flashcards if uf.next_review > now]
        next_session_date = min(next_reviews) if next_reviews else None

        logger.info("No available flashcards to study at this time.")
        return StudySessionResponse(
            study_session_id=None,
            available_cards=[],
            next_session_date=next_session_date.isoformat() if next_session_date else None
        )

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
    flashcard_to_repetitions = {uf.flashcard_id: uf.repetitions for uf in available_ufs}

    # -- (7) Build the response
    result = []
    for c in available_cards:
        card_dict = {
            "id": c.id,
            "question": c.question,
            "answer": c.answer,
            "deck_id": c.deck_id,
            "media_url": getattr(c, 'media_url', None),
            "repetitions": flashcard_to_repetitions.get(c.id, 0)
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

    return StudySessionResponse(
        study_session_id=new_session.id,
        available_cards=result,
        next_session_date=None
    )


@router.post("/reset_stale_cards")
def reset_stale_cards(
        deck_id: int,
        days_threshold: int = Query(30, description="Number of days to consider a card stale"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Reset flashcards that haven't been reviewed for a very long time (default: 30 days).
    These cards are likely forgotten and need to be re-learned from the beginning.

    This resets:
    - interval to 0
    - repetitions to 0
    - next_review to now (making them available immediately)
    - EF is reduced but not reset completely (to preserve some learning history)
    """
    logger.info(
        f"Resetting stale cards for deck_id={deck_id}, user_id={current_user.id_}, threshold={days_threshold} days")

    deck = db.query(Deck).filter(
        Deck.id == deck_id,
        Deck.user_id == current_user.id_
    ).first()
    if not deck:
        logger.error(f"Deck id={deck_id} not found for user_id={current_user.id_}")
        raise HTTPException(status_code=404, detail="Deck not found.")

    now = datetime.utcnow()
    stale_threshold = now - timedelta(days=days_threshold)

    user_flashcards = db.query(UserFlashcard).filter(
        UserFlashcard.user_id == current_user.id_,
        UserFlashcard.flashcard_id.in_([fc.id for fc in deck.flashcards]),
        UserFlashcard.next_review < stale_threshold
    ).all()

    if not user_flashcards:
        logger.info("No stale cards found.")
        return {"message": "No stale cards found", "reset_count": 0}

    reset_count = 0
    for uf in user_flashcards:
        days_stale = (now - uf.next_review).days
        logger.debug(f"Resetting UserFlashcard {uf.id} (flashcard_id={uf.flashcard_id}), {days_stale} days stale")

        # Reset to beginner state
        uf.interval = 0
        uf.repetitions = 0
        uf.next_review = now  # Available immediately

        # Reduce EF but don't reset completely - preserve some learning history
        current_ef = Decimal(str(uf.ef)) if not isinstance(uf.ef, Decimal) else uf.ef
        uf.ef = max(Decimal("1.3"), current_ef * Decimal("0.7"))  # Reduce by 30%

        db.add(uf)
        reset_count += 1

    try:
        db.commit()
        logger.info(f"Reset {reset_count} stale flashcards for deck_id={deck_id}")
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error resetting stale cards: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset stale cards.")

    return {
        "message": f"Successfully reset {reset_count} stale flashcards",
        "reset_count": reset_count
    }


@router.get("/retake_session")
def retake_session(
        deck_id: int = Query(..., description="ID of the deck to retake session from"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    """
    Retake flashcards from the latest session for the given deck and user.
    """
    logger.info(f"Fetching retake_session for deck_id={deck_id}, user_id={current_user.id_}")

    # Find the latest completed StudySession for the deck and user
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

    # Find two distinct lowest EF values
    distinct_efs = sorted({uf.ef for uf in user_flashcards})[:2]
    logger.debug(f"Lowest two distinct EF values: {distinct_efs}")

    # Select all UserFlashcards with EF in the lowest two EF values
    chosen_user_flashcards = [
        uf for uf in user_flashcards if uf.ef in distinct_efs
    ]

    logger.debug(f"Chosen {len(chosen_user_flashcards)} UserFlashcards with EF in {distinct_efs}")

    # Gather flashcards
    flashcard_to_repetitions = {uf.flashcard_id: uf.repetitions for uf in chosen_user_flashcards}
    flashcard_ids = [uf.flashcard_id for uf in chosen_user_flashcards]
    cards = db.query(Flashcard).filter(Flashcard.id.in_(flashcard_ids)).all()

    # Build JSON response
    result = []
    for c in cards:
        card_dict = {
            "id": c.id,
            "question": c.question,
            "answer": c.answer,
            "deck_id": c.deck_id,
            "media_url": getattr(c, 'media_url', None),
            "repetitions": flashcard_to_repetitions.get(c.id, 0)
        }
        result.append(card_dict)

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
    - Always create a new StudySession for retake tracking.
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

    now = datetime.utcnow()

    # Fetch hard UserFlashcards
    hard_user_flashcards = db.query(UserFlashcard).filter(
        UserFlashcard.user_id == current_user.id_,
        UserFlashcard.flashcard_id.in_([fc.id for fc in deck.flashcards]),
        UserFlashcard.ef <= Decimal("1.8"),
        UserFlashcard.next_review > now
    ).order_by(UserFlashcard.ef.asc()).all()

    if hard_user_flashcards:
        chosen_user_flashcards = hard_user_flashcards
        logger.debug(f"Selected {len(chosen_user_flashcards)} hard flashcards (EF <= 1.8)")
    else:
        user_flashcards = db.query(UserFlashcard).filter(
            UserFlashcard.user_id == current_user.id_,
            UserFlashcard.flashcard_id.in_([fc.id for fc in deck.flashcards]),
            UserFlashcard.next_review > now
        ).order_by(UserFlashcard.ef.asc()).all()

        if not user_flashcards:
            logger.info("No flashcards available for retake.")
            return []

        distinct_efs = sorted({uf.ef for uf in user_flashcards})
        if not distinct_efs:
            logger.info("No distinct EF values found.")
            return []

        lowest_two_efs = distinct_efs[:2] if len(distinct_efs) >= 2 else distinct_efs
        chosen_user_flashcards = [uf for uf in user_flashcards if uf.ef in lowest_two_efs]
        logger.debug(f"Selected {len(chosen_user_flashcards)} flashcards with EF in {lowest_two_efs}")

    # Map flashcard_id to repetitions
    flashcard_to_repetitions = {uf.flashcard_id: uf.repetitions for uf in chosen_user_flashcards}
    flashcard_ids = list(flashcard_to_repetitions.keys())

    cards = db.query(Flashcard).filter(Flashcard.id.in_(flashcard_ids)).all()

    # Tworzenie nowej sesji nauki
    new_session = StudySession(
        user_id=current_user.id_,
        deck_id=deck.id,
        started_at=now,
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    logger.info(
        f"Created new StudySession (retake): id={new_session.id}, user_id={current_user.id_}, deck_id={deck.id}")

    result = []
    for c in cards:
        result.append({
            "id": c.id,
            "question": c.question,
            "answer": c.answer,
            "deck_id": c.deck_id,
            "media_url": getattr(c, 'media_url', None),
            "repetitions": flashcard_to_repetitions.get(c.id, 0),
            "study_session_id": new_session.id
        })

    logger.debug(f"Retake cards returned: {result}")
    return result
