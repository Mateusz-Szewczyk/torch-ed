from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import Dict, Any
from datetime import datetime, date

from ..dependencies import get_db
from ..auth import get_current_user
from ..models import (
    StudyRecord as StudyRecordModel,
    UserFlashcard as UserFlashcardModel,
    StudySession as StudySessionModel,
    ExamResultAnswer as ExamResultAnswerModel,
    ExamResult as ExamResultModel,
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
    """
    user_id = current_user.id_
    try:
        # Pobierz dane
        study_records_result = (
            db.query(StudyRecordModel)
            .join(StudySessionModel, StudyRecordModel.session_id == StudySessionModel.id)
            .filter(StudySessionModel.user_id == user_id)
            .all()
        )
        user_flashcards_result = (
            db.query(UserFlashcardModel)
            .filter(UserFlashcardModel.user_id == user_id)
            .all()
        )
        study_sessions_result = (
            db.query(StudySessionModel)
            .filter(StudySessionModel.user_id == user_id)
            .all()
        )
        exam_result_answers_result = (
            db.query(ExamResultAnswerModel)
            .join(ExamResultModel, ExamResultAnswerModel.exam_result_id == ExamResultModel.id)
            .filter(ExamResultModel.user_id == user_id)
            .all()
        )
        exam_results_result = (
            db.query(ExamResultModel)
            .filter(ExamResultModel.user_id == user_id)
            .all()
        )

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
        serialized_exam_results = [serialize(result) for result in exam_results_result]
        serialized_session_durations = [
            {
                "date": session.started_at.date().isoformat(),
                "duration_hours": (session.completed_at - session.started_at).total_seconds() / 3600 if session.completed_at else 0
            }
            for session in study_sessions_result
        ]

        return {
            "study_records": serialized_study_records,
            "user_flashcards": serialized_user_flashcards,
            "study_sessions": serialized_study_sessions,
            "exam_result_answers": serialized_exam_result_answers,
            "exam_results": serialized_exam_results,
            "session_durations": serialized_session_durations,
        }

    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
