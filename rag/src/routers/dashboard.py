from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional, List
from datetime import date, timedelta

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
async def get_dashboard_data(
    date_range: Optional[List[date]] = Query(None, description="Range of dates [start_date, end_date]"),
    exam_id: Optional[int] = Query(None, description="Filter by exam ID"),
    deck_id: Optional[int] = Query(None, description="Filter by deck ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Fetches filtered dashboard data for the authenticated user.
    """
    user_id = current_user.id_

    try:
        # Base queries
        study_records_query = db.query(StudyRecordModel).join(
            StudySessionModel, StudyRecordModel.session_id == StudySessionModel.id
        ).filter(StudySessionModel.user_id == user_id)

        user_flashcards_query = db.query(UserFlashcardModel).filter(
            UserFlashcardModel.user_id == user_id
        )

        study_sessions_query = db.query(StudySessionModel).filter(
            StudySessionModel.user_id == user_id
        )

        exam_results_query = db.query(ExamResultModel).filter(
            ExamResultModel.user_id == user_id
        )

        # Apply filters
        if date_range and len(date_range) == 2:
            start_date, end_date = date_range
            study_records_query = study_records_query.filter(
                StudyRecordModel.reviewed_at.between(start_date, end_date)
            )
            study_sessions_query = study_sessions_query.filter(
                StudySessionModel.started_at.between(start_date, end_date)
            )
            exam_results_query = exam_results_query.filter(
                ExamResultModel.started_at.between(start_date, end_date)
            )

        if exam_id:
            exam_results_query = exam_results_query.filter(
                ExamResultModel.exam_id == exam_id
            )

        if deck_id:
            study_sessions_query = study_sessions_query.filter(
                StudySessionModel.deck_id == deck_id
            )
            user_flashcards_query = user_flashcards_query.filter(
                UserFlashcardModel.flashcard_id.in_(
                    db.query(Deck.flashcards).filter(Deck.id == deck_id)
                )
            )

        # Execute queries
        study_records_result = study_records_query.all()
        user_flashcards_result = user_flashcards_query.all()
        study_sessions_result = study_sessions_query.all()
        exam_results_result = exam_results_query.all()

        # Calculate additional metrics
        session_durations = [
            {
                "date": session.started_at.date(),
                "duration": (session.completed_at - session.started_at).total_seconds() / 3600 if session.completed_at else 0
            }
            for session in study_sessions_result
        ]

        return {
            "study_records": study_records_result,
            "user_flashcards": user_flashcards_result,
            "study_sessions": study_sessions_result,
            "exam_results": exam_results_result,
            "session_durations": session_durations,
        }

    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
