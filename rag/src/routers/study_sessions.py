# src/routers/study_sessions.py

import logging
from datetime import timedelta, timezone
from typing import List

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
from datetime import datetime

router = APIRouter()
logger = logging.getLogger(__name__)


# Nowe modele do hurtowego zapisu
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
    """
    logger.info(f"Tworzenie sesji nauki dla deck_id={session_create.deck_id} przez user_id={current_user.id_}")

    # Szukamy Deck należącego do user_id (Integer!)
    deck = db.query(Deck).filter(
        Deck.id == session_create.deck_id,
        Deck.user_id == str(current_user.id_)
    ).first()
    if not deck:
        logger.error(f"Deck z ID={session_create.deck_id} nie znaleziony dla user_id={current_user.id_}.")
        raise HTTPException(status_code=404, detail="Deck nie znaleziony.")

    # Inicjalizacja UserFlashcard, jeśli nie istnieje
    user_flashcards = db.query(UserFlashcard).filter(
        UserFlashcard.user_id == current_user.id_,
        UserFlashcard.flashcard_id.in_([fc.id for fc in deck.flashcards])
    ).all()
    existing_flashcard_ids = {uf.flashcard_id for uf in user_flashcards}

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

    db.commit()

    # Tworzymy sesję
    new_session = StudySession(
        user_id=current_user.id_,
        deck_id=deck.id,
        started_at=datetime.utcnow()
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    logger.info(f"Utworzono sesję nauki ID={new_session.id} dla user_id={current_user.id_}")
    return new_session


@router.get("/next_flashcard/{session_id}/", response_model=FlashcardRead)
def get_next_flashcard(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Pobiera następną fiszkę do nauki (tryb natychmiastowy SM2).
    """
    logger.info(f"Pobieranie następnej fiszki dla sesji_id={session_id}, user_id={current_user.id_}")

    session = db.query(StudySession).filter(
        StudySession.id == session_id,
        StudySession.user_id == current_user.id_
    ).first()
    if not session:
        logger.error(f"Sesja ID={session_id} nie znaleziono dla user_id={current_user.id_}.")
        raise HTTPException(status_code=404, detail="Sesja nauki nie znaleziona.")

    deck = session.deck
    if not deck:
        logger.error(f"Deck powiązany z sesją ID={session_id} nie został znaleziony.")
        raise HTTPException(status_code=404, detail="Deck nie znaleziony.")

    today = datetime.utcnow()
    user_flashcard = (
        db.query(UserFlashcard)
        .filter(
            UserFlashcard.user_id == current_user.id_,
            UserFlashcard.flashcard_id.in_([fc.id for fc in deck.flashcards]),
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
        logger.error(f"Fiszka ID={user_flashcard.flashcard_id} nie istnieje w bazie.")
        raise HTTPException(status_code=404, detail="Fiszka nie znaleziona.")

    return flashcard


@router.post("/record_review/{session_id}/", response_model=StudyRecordRead, status_code=201)
def record_flashcard_review(
    session_id: int,
    record_create: StudyRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Rejestruje ocenę pojedynczej fiszki (natychmiastowy SM2).
    """
    logger.info(
        f"Rejestrowanie oceny fiszki user_flashcard_id={record_create.user_flashcard_id}, rating={record_create.rating}, "
        f"sesja={session_id}, user_id={current_user.id_}"
    )

    session = db.query(StudySession).filter(
        StudySession.id == session_id,
        StudySession.user_id == current_user.id_
    ).first()
    if not session:
        logger.error(f"Sesja ID={session_id} nie znaleziona dla user_id={current_user.id_}.")
        raise HTTPException(status_code=404, detail="Sesja nauki nie znaleziona.")

    deck = session.deck
    if not deck:
        logger.error(f"Deck powiązany z sesją ID={session_id} nie został znaleziony.")
        raise HTTPException(status_code=404, detail="Deck nie znaleziony.")

    # Znajdź userFlashcard
    user_flashcard = db.query(UserFlashcard).filter(
        UserFlashcard.id == record_create.user_flashcard_id,
        UserFlashcard.user_id == current_user.id_,
        UserFlashcard.flashcard_id.in_([fc.id for fc in deck.flashcards])
    ).first()
    if not user_flashcard:
        logger.error(f"UserFlashcard ID={record_create.user_flashcard_id} nie pasuje do decku ID={deck.id}.")
        raise HTTPException(status_code=404, detail="Fiszka nie znaleziona.")

    # Tworzymy record
    study_record = StudyRecord(
        session_id=session.id,
        user_flashcard_id=user_flashcard.id,
        rating=record_create.rating,
        reviewed_at=datetime.utcnow()
    )
    db.add(study_record)

    # SM2
    _update_sm2(user_flashcard, record_create.rating)
    db.commit()
    db.refresh(study_record)

    logger.info(f"Zaktualizowano SM2 dla user_flashcard ID={user_flashcard.id}")
    return study_record


@router.post("/bulk_record", status_code=201)
def bulk_record(
    data: BulkRecordData,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Przyjmuje hurtowe oceny (rating) i aktualizuje SM2 dla każdej fiszki na końcu sesji.
    """
    logger.info(f"Hurtowe zapisywanie fiszek deck_id={data.deck_id}, user_id={current_user.id_}")

    # Sprawdź deck
    deck = db.query(Deck).filter(
        Deck.id == data.deck_id,
        Deck.user_id == current_user.id_
    ).first()
    if not deck:
        logger.error(f"Deck ID={data.deck_id} nie znaleziony dla user_id={current_user.id_}")
        raise HTTPException(status_code=404, detail="Deck nie znaleziony.")

    # Stwórz nową StudySession na potrzeby logów
    new_session = StudySession(
        user_id=current_user.id_,
        deck_id=deck.id,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    db.add(new_session)
    db.flush()  # uzyskujemy ID nowej sesji

    # Mapujemy flashcard_id -> userFlashcard
    user_flashcards = db.query(UserFlashcard).filter(
        UserFlashcard.user_id == current_user.id_,
        UserFlashcard.flashcard_id.in_([fc.id for fc in deck.flashcards])
    ).all()
    uf_map = {uf.flashcard_id: uf for uf in user_flashcards}

    records_created = []

    for item in data.ratings:
        uf = uf_map.get(item.flashcard_id)
        if not uf:
            logger.warning(f"Flashcard ID={item.flashcard_id} nie należy do user_id={current_user.id_} - pomijam.")
            continue

        # Tworzymy StudyRecord
        study_record = StudyRecord(
            session_id=new_session.id,
            user_flashcard_id=uf.id,
            rating=item.rating,
            reviewed_at=item.answered_at
        )
        db.add(study_record)
        records_created.append(study_record)

        # SM2
        _update_sm2(uf, item.rating)

    db.commit()
    logger.info(f"Hurtowy zapis zakończony. Utworzono StudySession ID={new_session.id}, "
                f"{len(records_created)} recordów dodano.")

    return {"message": "Bulk record saved successfully", "study_session_id": new_session.id}


def _update_sm2(user_flashcard: UserFlashcard, rating: int):
    """
    Logika SM2: rating <3 => reset, rating>=3 => rośnie interval, EF, next_review.
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

    # EF
    user_flashcard.ef += (0.1 - (5 - rating) * (0.08 + (5 - rating) * 0.02))
    if user_flashcard.ef < 1.3:
        user_flashcard.ef = 1.3

    # next_review
    user_flashcard.next_review = datetime.utcnow() + timedelta(days=user_flashcard.interval)


@router.get("/sessions/", response_model=List[StudySessionRead])
def get_study_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Pobiera wszystkie sesje nauki użytkownika.
    """
    logger.info(f"Pobieranie wszystkich sesji dla user_id={current_user.id_}")
    sessions = db.query(StudySession).filter(StudySession.user_id == current_user.id_).all()
    return sessions


@router.get("/session/{session_id}/records/", response_model=List[StudyRecordRead])
def get_study_records(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Pobiera wszystkie rekordy danej sesji.
    """
    logger.info(f"Pobieranie rekordów sesji_id={session_id} przez user_id={current_user.id_}")

    session = db.query(StudySession).filter(
        StudySession.id == session_id,
        StudySession.user_id == current_user.id_
    ).first()
    if not session:
        logger.error(f"Sesja ID={session_id} nie znaleziono dla user_id={current_user.id_}.")
        raise HTTPException(status_code=404, detail="Sesja nauki nie znaleziona.")

    records = db.query(StudyRecord).filter(StudyRecord.session_id == session_id).all()
    return records
