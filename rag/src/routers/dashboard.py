import logging
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError

from ..schemas import DashboardData
from ..dependencies import get_db
from ..auth import get_current_user
from ..models import User, StudyRecord, UserFlashcard, StudySession, ExamResultAnswer, ExamResult

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/", response_model=DashboardData)
async def get_dashboard_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Fetches dashboard data for the authenticated user by joining related tables.
    """
    user_id = current_user.id_
    logger.info(f"Fetching dashboard data for user_id: {user_id}")

    try:
        # Fetch study records indirectly via study sessions
        study_records_result = (
            db.query(StudyRecord)
            .join(StudySession, StudyRecord.session_id == StudySession.id)
            .filter(StudySession.user_id == user_id)
            .all()
        )

        # Fetch user flashcards
        user_flashcards_result = (
            db.query(UserFlashcard)
            .filter(UserFlashcard.user_id == user_id)
            .all()
        )

        # Fetch study sessions
        study_sessions_result = (
            db.query(StudySession)
            .filter(StudySession.user_id == user_id)
            .all()
        )

        # Fetch exam result answers via exam results
        exam_result_answers_result = (
            db.query(ExamResultAnswer)
            .join(ExamResult, ExamResultAnswer.exam_result_id == ExamResult.id)
            .filter(ExamResult.user_id == user_id)
            .all()
        )

        # Fetch exam results
        exam_results_result = (
            db.query(ExamResult)
            .filter(ExamResult.user_id == user_id)
            .all()
        )

        # Prepare the dashboard data
        dashboard_data = DashboardData(
            study_records=study_records_result,
            user_flashcards=user_flashcards_result,
            study_sessions=study_sessions_result,
            exam_result_answers=exam_result_answers_result,
            exam_results=exam_results_result,
        )

        logger.info(f"Successfully fetched dashboard data for user_id: {user_id}")
        return dashboard_data

    except SQLAlchemyError as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Error fetching dashboard data")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Unexpected error occurred")
