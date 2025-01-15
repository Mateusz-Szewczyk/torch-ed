from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import Dict, Any

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

@router.get("", response_model=Dict[str, Any])
@router.get("/", response_model=Dict[str, Any])
async def get_dashboard_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Fetches all dashboard data for the authenticated user.
    No filtering is applied on the backend.
    """
    user_id = current_user.id_

    try:
        # Pobierz wszystkie rekordy studiów użytkownika
        study_records = db.query(StudyRecordModel).join(
            StudySessionModel, StudyRecordModel.session_id == StudySessionModel.id
        ).filter(StudySessionModel.user_id == user_id).all()

        # Pobierz wszystkie fiszki użytkownika
        user_flashcards = db.query(UserFlashcardModel).filter(
            UserFlashcardModel.user_id == user_id
        ).all()

        # Pobierz wszystkie sesje studiów użytkownika
        study_sessions = db.query(StudySessionModel).filter(
            StudySessionModel.user_id == user_id
        ).all()

        # Pobierz wszystkie wyniki egzaminów użytkownika
        exam_results = db.query(ExamResultModel).filter(
            ExamResultModel.user_id == user_id
        ).all()

        # Pobierz wszystkie odpowiedzi na wyniki egzaminów użytkownika
        exam_result_ids = [exam.id for exam in exam_results]
        exam_result_answers = db.query(ExamResultAnswerModel).filter(
            ExamResultAnswerModel.exam_result_id.in_(exam_result_ids)
        ).all()

        # Oblicz dodatkowe metryki
        session_durations = [
            {
                "date": session.started_at.date().isoformat(),
                "duration_hours": (session.completed_at - session.started_at).total_seconds() / 3600 if session.completed_at else 0
            }
            for session in study_sessions
        ]

        # Zwróć dane jako słownik
        return {
            "study_records": study_records,
            "user_flashcards": user_flashcards,
            "study_sessions": study_sessions,
            "exam_result_answers": exam_result_answers,
            "exam_results": exam_results,
            "session_durations": session_durations,
        }

    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
