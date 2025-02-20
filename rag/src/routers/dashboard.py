from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, date
from sqlalchemy import func

from ..dependencies import get_db
from ..auth import get_current_user
from ..models import (
    StudyRecord as StudyRecordModel,
    UserFlashcard as UserFlashcardModel,
    StudySession as StudySessionModel,
    ExamResultAnswer as ExamResultAnswerModel,
    ExamResult as ExamResultModel,
    Deck,
    Exam,
    User,
)

router = APIRouter()


@router.get("/")
@router.get("")  # Obsługa zarówno z, jak i bez trailing slash
async def get_dashboard_data(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    """
    Pobiera dane dashboardu dla uwierzytelnionego użytkownika jako surowy JSON.
    Zwraca średnie wyniki dziennie oraz nazwy decków i egzaminów.
    """
    user_id = current_user.id_
    try:
        # Pobierz dane studiów
        study_records_result = (
            db.query(StudyRecordModel)
            .join(StudySessionModel, StudyRecordModel.session_id == StudySessionModel.id)
            .filter(StudySessionModel.user_id == user_id)
            .all()
        )

        # Pobierz fiszki użytkownika
        user_flashcards_result = (
            db.query(UserFlashcardModel)
            .filter(UserFlashcardModel.user_id == user_id)
            .all()
        )

        # Pobierz sesje studiów użytkownika
        study_sessions_result = (
            db.query(StudySessionModel)
            .filter(StudySessionModel.user_id == user_id)
            .all()
        )

        # Pobierz wyniki egzaminów użytkownika wraz z nazwami egzaminów
        exam_results_query = (
            db.query(
                ExamResultModel,
                Exam.name.label("exam_name")
            )
            .join(Exam, ExamResultModel.exam_id == Exam.id)
            .filter(ExamResultModel.user_id == user_id)
        )
        exam_results_result = exam_results_query.all()

        # Pobierz odpowiedzi na wyniki egzaminów użytkownika
        exam_result_ids = [result[0].id for result in exam_results_result]
        exam_result_answers_result = (
            db.query(ExamResultAnswerModel)
            .filter(ExamResultAnswerModel.exam_result_id.in_(exam_result_ids))
            .all()
        )

        # Pobierz nazwy decków
        deck_ids = {session.deck_id for session in study_sessions_result}
        decks = db.query(Deck).filter(Deck.id.in_(deck_ids)).all()
        deck_id_to_name = {deck.id: deck.name for deck in decks}

        # Oblicz średnie wyniki egzaminów dziennie
        exam_daily_average = (
            db.query(
                func.date(ExamResultModel.started_at).label("date"),
                func.avg(ExamResultModel.score).label("average_score")
            )
            .filter(ExamResultModel.user_id == user_id)
            .group_by(func.date(ExamResultModel.started_at))
            .all()
        )
        exam_daily_average_serialized = [
            {
                "date": record.date.isoformat(),
                "average_score": float(record.average_score)
            }
            for record in exam_daily_average
        ]

        # Oblicz średnie oceny fiszek dziennie
        flashcard_daily_average = (
            db.query(
                func.date(StudyRecordModel.reviewed_at).label("date"),
                func.avg(StudyRecordModel.rating).label("average_rating")
            )
            .join(StudySessionModel, StudyRecordModel.session_id == StudySessionModel.id)
            .filter(StudySessionModel.user_id == user_id)
            .group_by(func.date(StudyRecordModel.reviewed_at))
            .all()
        )
        flashcard_daily_average_serialized = [
            {
                "date": record.date.isoformat(),
                "average_rating": float(record.average_rating)
            }
            for record in flashcard_daily_average
        ]

        # Oblicz dodatkowe metryki (średnia czasów sesji)
        session_durations = [
            {
                "date": session.started_at.date().isoformat(),
                "duration_hours": (
                    (session.completed_at - session.started_at).total_seconds() / 3600
                    if session.completed_at else 0
                )
            }
            for session in study_sessions_result
        ]

        # Funkcja serializująca obiekt ORM do słownika
        def serialize(obj):
            """Konwertuje obiekt ORM na słownik, obsługując pola datetime."""
            result = {}
            for col in obj.__table__.columns:
                value = getattr(obj, col.name)
                if isinstance(value, (datetime, date)):
                    result[col.name] = value.isoformat()
                else:
                    result[col.name] = value
            return result

        # Serializacja wszystkich danych
        serialized_study_records = [serialize(record) for record in study_records_result]
        serialized_user_flashcards = [serialize(card) for card in user_flashcards_result]
        serialized_study_sessions = [serialize(session) for session in study_sessions_result]
        serialized_exam_result_answers = [serialize(answer) for answer in exam_result_answers_result]
        serialized_exam_results = [
            {
                **serialize(result[0]),
                "exam_name": result.exam_name
            }
            for result in exam_results_result
        ]

        return {
            "study_records": serialized_study_records,
            "user_flashcards": serialized_user_flashcards,
            "study_sessions": serialized_study_sessions,
            "exam_result_answers": serialized_exam_result_answers,
            "exam_results": serialized_exam_results,
            "session_durations": session_durations,
            "exam_daily_average": exam_daily_average_serialized,
            "flashcard_daily_average": flashcard_daily_average_serialized,
            "deck_names": deck_id_to_name
        }

    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
