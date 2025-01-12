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
    FlashcardRead
)
from ..dependencies import get_db
from ..auth import get_current_user
from ..models import User
from pydantic import BaseModel, Field
from datetime import timezone

router = APIRouter()
logger = logging.getLogger(__name__)

# Nowy schemat do hurtowego zapisu ocen
class BulkRatingItem(BaseModel):
    flashcardId: int
    rating: int
    answeredAt: datetime

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
    logger.info(
        f"Tworzenie sesji nauki dla deck_id={session_create.deck_id} "
        f"przez user_id={current_user.id_}"
    )

    # Zakładamy user_id = int w bazie
    deck = db.query(Deck).filter(
        Deck.id == session_create.deck_id,
        Deck.user_id == current_user.id_
    ).first()

    if not deck:
        logger.error(
            f"Deck z ID={session_create.deck_id} nie znaleziony dla user_id={current_user.id_}."
        )
        raise HTTPException(status_code=404, detail="Deck nie znaleziony.")

    # Inicjalizacja UserFlashcard, jeśli nie istnieje
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

    # Nowa sesja nauki
    new_session = StudySession(
        user_id=current_user.id_,
        deck_id=deck.id,
        started_at=datetime.utcnow()
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    logger.info(f"Utworzono sesję nauki z ID={new_session.id} dla user_id={current_user.id_}")
    return new_session


@router.get("/next_flashcard/{session_id}/", response_model=FlashcardRead)
def get_next_flashcard(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Pobiera następny flashcard do nauki zgodnie z algorytmem SM2 (opcja natychmiastowa).
    """
    logger.info(
        f"Pobieranie następnej fiszki dla sesji_id={session_id} "
        f"przez user_id={current_user.id_}"
    )

    session = db.query(StudySession).filter(
        StudySession.id == session_id,
        StudySession.user_id == current_user.id_
    ).first()

    if not session:
        logger.error(f"Sesja z ID={session_id} nie znaleziona dla user_id={current_user.id_}.")
        raise HTTPException(status_code=404, detail="Sesja nauki nie znaleziona.")

    deck = session.deck
    if not deck:
        logger.error(f"Deck powiązany z sesją ID={session.id} nie został znaleziony.")
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
        raise HTTPException(
            status_code=404,
            detail="Nie ma więcej fiszek do nauki na dziś."
        )

    flashcard = db.query(Flashcard).filter(Flashcard.id == user_flashcard.flashcard_id).first()
    if not flashcard:
        logger.error(f"Fiszka ID={user_flashcard.flashcard_id} nie istnieje w bazie.")
        raise HTTPException(status_code=404, detail="Fiszka nie znaleziona.")

    logger.debug(f"Pobrano fiszkę ID={flashcard.id} do nauki dla user_id={current_user.id_}")
    return flashcard


@router.post("/record_review/{session_id}/", response_model=StudyRecordRead, status_code=201)
def record_flashcard_review(
    session_id: int,
    record_create: StudyRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Rejestruje ocenę użytkownika dla danej fiszki i aktualizuje dane SM2 (opcja natychmiastowa).
    """
    logger.info(
        f"Rejestrowanie oceny dla sesji_id={session_id}, "
        f"user_flashcard_id={record_create.user_flashcard_id}, rating={record_create.rating} "
        f"przez user_id={current_user.id_}"
    )

    session = db.query(StudySession).filter(
        StudySession.id == session_id,
        StudySession.user_id == current_user.id_
    ).first()
    if not session:
        logger.error(
            f"Sesja ID={session_id} nie znaleziono dla user_id={current_user.id_}."
        )
        raise HTTPException(status_code=404, detail="Sesja nauki nie znaleziona.")

    deck = session.deck
    if not deck:
        logger.error(f"Deck powiązany z sesją ID={session_id} nie został znaleziony.")
        raise HTTPException(status_code=404, detail="Deck nie znaleziony.")

    user_flashcard = db.query(UserFlashcard).filter(
        UserFlashcard.id == record_create.user_flashcard_id,
        UserFlashcard.user_id == current_user.id_,
        UserFlashcard.flashcard_id.in_([fc.id for fc in deck.flashcards])
    ).first()
    if not user_flashcard:
        logger.error(
            f"UserFlashcard z ID={record_create.user_flashcard_id} nie znaleziony w decku ID={deck.id}."
        )
        raise HTTPException(status_code=404, detail="Fiszka nie znaleziona.")

    # Tworzenie rekordu
    study_record = StudyRecord(
        session_id=session.id,
        user_flashcard_id=user_flashcard.id,
        rating=record_create.rating,
        reviewed_at=datetime.utcnow()
    )
    db.add(study_record)

    # Aktualizacja SM2
    _update_sm2(user_flashcard, record_create.rating)
    db.commit()
    db.refresh(study_record)

    logger.info(f"Zaktualizowano SM2 dla user_flashcard ID={user_flashcard.id}, rating={record_create.rating}")
    return study_record


@router.post("/bulk_record", status_code=201)
def bulk_record(
    data: BulkRecordData,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Przyjmuje hurtowe oceny użytkownika (rating) i aktualizuje SM2 po zakończeniu sesji.
    Odpowiednik "record_review", ale zbiorczo dla wielu fiszek.
    """
    logger.info(f"Hurtowe zapisywanie fiszek w deck_id={data.deck_id} dla user_id={current_user.id_}")

    # 1. Sprawdź, czy deck istnieje i czy należy do usera
    deck = db.query(Deck).filter(
        Deck.id == data.deck_id,
        Deck.user_id == current_user.id_
    ).first()
    if not deck:
        logger.error(f"Deck ID={data.deck_id} nie znaleziony lub nie należy do user_id={current_user.id_}")
        raise HTTPException(status_code=404, detail="Deck nie znaleziony.")

    # 2. Dla każdej oceny z data.ratings, w pętli aktualizujemy userFlashcard + tworzymy StudyRecord
    #    Nie tworzymy nowej StudySession, bo użytkownik może korzystać z jednej (lub go nie potrzebuje).
    #    Jeśli chcesz, możesz dodać param session_id do BulkRecordData i przypisać te study_records do tej sesji.

    # Ewentualnie stwórzmy session do logów:
    new_session = StudySession(
        user_id=current_user.id_,
        deck_id=deck.id,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    db.add(new_session)
    db.flush()  # aby new_session miał ID

    # Mapa flashcard_id -> userFlashcard
    user_flashcards = db.query(UserFlashcard).filter(
        UserFlashcard.user_id == current_user.id_,
        UserFlashcard.flashcard_id.in_([fc.id for fc in deck.flashcards])
    ).all()
    uf_by_flashcard = {uf.flashcard_id: uf for uf in user_flashcards}

    records_created = []

    for item in data.ratings:
        uf = uf_by_flashcard.get(item.flashcardId)
        if not uf:
            # Nie istnieje userFlashcard, prawdopodobnie nie należała do decku
            logger.warning(f"Flashcard ID={item.flashcardId} nie należy do user_id={current_user.id_}, pomijam.")
            continue

        # Tworzymy study_record
        study_record = StudyRecord(
            session_id=new_session.id,
            user_flashcard_id=uf.id,
            rating=item.rating,
            reviewed_at=item.answeredAt  # user podał answeredAt
        )
        db.add(study_record)
        records_created.append(study_record)

        # SM2
        _update_sm2(uf, item.rating)

    db.commit()

    logger.info(f"Hurtowy zapis zakończony. Utworzono StudySession ID={new_session.id}, {len(records_created)} recordów.")
    return {"message": "Bulk record saved successfully", "study_session_id": new_session.id}


def _update_sm2(user_flashcard: UserFlashcard, rating: int):
    """
    Uniwersalna logika SM2 aktualizowana w pętli (dla pojedynczej oceny).
    rating < 3 => reset, rating >=3 => rośnie interval + EF.
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
    user_flashcard.ef += (
        0.1
        - (5 - rating) * (0.08 + (5 - rating) * 0.02)
    )
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
    logger.info(f"Pobieranie wszystkich sesji nauki dla user_id={current_user.id_}")
    sessions = db.query(StudySession).filter(
        StudySession.user_id == current_user.id_
    ).all()
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
    logger.info(
        f"Pobieranie rekordów przeglądu dla sesji_id={session_id} "
        f"przez user_id={current_user.id_}"
    )

    session = db.query(StudySession).filter(
        StudySession.id == session_id,
        StudySession.user_id == current_user.id_
    ).first()

    if not session:
        logger.error(
            f"Sesja z ID={session_id} nie znaleziona dla user_id={current_user.id_}."
        )
        raise HTTPException(status_code=404, detail="Sesja nauki nie znaleziona.")

    records = db.query(StudyRecord).filter(StudyRecord.session_id == session_id).all()
    return records
