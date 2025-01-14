# src/routers/query.py

import logging
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from ..schemas import DashboardData, StudyRecord, UserFlashcard, StudySession, ExamResultAnswer, ExamResult
from ..dependencies import get_db
from ..auth import get_current_user
from ..models import User, StudyRecord, UserFlashcard, StudySession, ExamResultAnswer, ExamResult

router = APIRouter()
logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)


@router.get("/", response_model=DashboardData)
async def get_dashboard_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Pobiera dane z różnych tabel dla dashboardu.
    """
    user_id = current_user.id_
    logger.info(f"Fetching dashboard data for user_id: {user_id}")

    try:
        # Wykonanie zapytań do wszystkich tabel
        study_records_result = db.query(StudyRecord).filter(StudyRecord.user_id == user_id).all()
        user_flashcards_result = db.query(UserFlashcard).filter(UserFlashcard.user_id == user_id).all()
        study_sessions_result = db.query(StudySession).filter(StudySession.user_id == user_id).all()
        exam_result_answers_result = db.query(ExamResultAnswer).join(ExamResult).filter(ExamResult.user_id == user_id).all()
        exam_results_result = db.query(ExamResult).filter(ExamResult.user_id == user_id).all()

        dashboard_data = DashboardData(
            study_records=study_records_result,
            user_flashcards=user_flashcards_result,
            study_sessions=study_sessions_result,
            exam_result_answers=exam_result_answers_result,
            exam_results=exam_results_result
        )

        logger.info(f"Successfully fetched dashboard data for user_id: {user_id}")
        return dashboard_data

    except Exception as e:
        logger.error(f"Error fetching dashboard data for user_id: {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching dashboard data")
