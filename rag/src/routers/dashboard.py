from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from ..dependencies import get_db
from ..auth import get_current_user
from ..models import (
    StudyRecord as StudyRecordModel,
    UserFlashcard as UserFlashcardModel,
    StudySession as StudySessionModel,
    ExamResultAnswer as ExamResultAnswerModel,
    ExamResult as ExamResultModel, User,
)

router = APIRouter()

@router.get("/")
async def get_dashboard_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Fetches dashboard data for the authenticated user as raw JSON.
    """
    user_id = current_user.id_
    try:
        # Query data
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

        # Serialize data into raw JSON
        def serialize(obj):
            """Convert ORM object to dictionary."""
            return {col.name: getattr(obj, col.name) for col in obj.__table__.columns}

        return {
            "study_records": [serialize(record) for record in study_records_result],
            "user_flashcards": [serialize(card) for card in user_flashcards_result],
            "study_sessions": [serialize(session) for session in study_sessions_result],
            "exam_result_answers": [serialize(answer) for answer in exam_result_answers_result],
            "exam_results": [serialize(result) for result in exam_results_result],
        }

    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
