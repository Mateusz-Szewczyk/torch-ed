from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from ..schemas import DashboardData, StudyRecord, UserFlashcard, StudySession, ExamResultAnswer, ExamResult
from ..dependencies import get_db
from ..auth import get_current_user
from ..models import User, StudyRecord as StudyRecordModel, UserFlashcard as UserFlashcardModel, StudySession as StudySessionModel, ExamResultAnswer as ExamResultAnswerModel, ExamResult as ExamResultModel

router = APIRouter()


@router.get("/", response_model=DashboardData)
async def get_dashboard_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardData:
    """
    Fetches dashboard data for the authenticated user.
    """
    user_id = current_user.id_
    try:
        # Query and serialize the data
        study_records_result = db.query(StudyRecordModel).join(
            StudySessionModel, StudyRecordModel.session_id == StudySessionModel.id
        ).filter(StudySessionModel.user_id == user_id).all()

        user_flashcards_result = db.query(UserFlashcardModel).filter(
            UserFlashcardModel.user_id == user_id
        ).all()

        study_sessions_result = db.query(StudySessionModel).filter(
            StudySessionModel.user_id == user_id
        ).all()

        exam_result_answers_result = db.query(ExamResultAnswerModel).join(
            ExamResultModel, ExamResultAnswerModel.exam_result_id == ExamResultModel.id
        ).filter(ExamResultModel.user_id == user_id).all()

        exam_results_result = db.query(ExamResultModel).filter(
            ExamResultModel.user_id == user_id
        ).all()

        # Convert ORM results to Pydantic models
        dashboard_data = DashboardData(
            study_records=[StudyRecord.model_validate(record) for record in study_records_result],
            user_flashcards=[UserFlashcard.model_validate(card) for card in user_flashcards_result],
            study_sessions=[StudySession.model_validate(session) for session in study_sessions_result],
            exam_result_answers=[ExamResultAnswer.model_validate(answer) for answer in exam_result_answers_result],
            exam_results=[ExamResult.model_validate(result) for result in exam_results_result],
        )

        return dashboard_data

    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
