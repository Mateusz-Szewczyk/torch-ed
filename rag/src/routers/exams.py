# src/routers/exams.py

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session, joinedload
from typing import List

from ..models import Exam, ExamQuestion, ExamAnswer, User
from ..schemas import ExamCreate, ExamRead, ExamUpdate
from ..dependencies import get_db
from ..auth import get_current_user

import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/", response_model=ExamRead, status_code=status.HTTP_201_CREATED)
async def create_exam(
    exam: ExamCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Tworzy nowy egzamin przypisany do aktualnie zalogowanego użytkownika.
    """
    logger.info(f"Creating a new exam with name: {exam.name}")
    logger.debug(f"Exam data: {exam}")
    user_id = str(current_user.id_)
    try:
        new_exam = Exam(
            name=exam.name,
            description=exam.description,
            user_id=user_id
        )

        # Dodawanie pytań do egzaminu
        for q in exam.questions:
            new_question = ExamQuestion(text=q.text)

            for a in q.answers:
                new_answer = ExamAnswer(
                    text=a.text,
                    is_correct=a.is_correct
                )
                new_question.answers.append(new_answer)
                logger.debug(f"Added answer: {new_answer.text}, is_correct: {new_answer.is_correct}")

            new_exam.questions.append(new_question)
            logger.debug(f"Added question: {new_question.text}")

        db.add(new_exam)
        db.commit()
        db.refresh(new_exam)

        logger.info(f"Created new exam with ID {new_exam.id} for user_id={user_id}")
        return new_exam

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating exam: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating exam: {str(e)}")


@router.get("/", response_model=List[ExamRead])
async def get_exams(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Pobiera wszystkie egzaminy zalogowanego użytkownika.
    """
    user_id = str(current_user.id_)
    logger.info(f"Fetching all exams for user_id={user_id}.")
    try:
        exams = (
            db.query(Exam)
            .options(joinedload(Exam.questions).joinedload(ExamQuestion.answers))
            .filter(Exam.user_id == user_id)
            .all()
        )
        logger.debug(f"Fetched exams: {exams}")
        return exams
    except Exception as e:
        logger.error(f"Error fetching exams: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching exams: {str(e)}")


@router.get("/{exam_id}/", response_model=ExamRead)
async def get_exam(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Pobiera konkretny egzamin (wraz z pytaniami i odpowiedziami) po ID,
    jeśli należy do zalogowanego użytkownika.
    """
    user_id = str(current_user.id_)
    logger.info(f"Fetching exam with ID={exam_id} for user_id={user_id}")
    try:
        exam = (
            db.query(Exam)
            .options(joinedload(Exam.questions).joinedload(ExamQuestion.answers))
            .filter(Exam.id == exam_id, Exam.user_id == user_id)
            .first()
        )
        if not exam:
            logger.error(f"Exam with ID {exam_id} not found for user_id={user_id}.")
            raise HTTPException(status_code=404, detail="Exam not found.")
        logger.debug(f"Fetched exam: {exam}")
        return exam
    except Exception as e:
        logger.error(f"Error fetching exam: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching exam: {str(e)}")


@router.put("/{exam_id}/", response_model=ExamRead)
async def update_exam(
    exam_id: int,
    exam_update: ExamUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Aktualizuje egzamin o podanym ID, jeśli należy do zalogowanego użytkownika.
    """
    user_id = str(current_user.id_)
    logger.info(f"Updating exam with ID={exam_id} for user_id={user_id}")
    logger.debug(f"Exam update data: {exam_update}")
    try:
        existing_exam = (
            db.query(Exam)
            .options(joinedload(Exam.questions).joinedload(ExamQuestion.answers))
            .filter(Exam.id == exam_id, Exam.user_id == user_id)
            .first()
        )
        if not existing_exam:
            logger.error(f"Exam with ID={exam_id} not found or not owned by user_id={user_id}.")
            raise HTTPException(status_code=404, detail="Exam not found.")

        # Aktualizacja podstawowych pól egzaminu
        if exam_update.name is not None:
            existing_exam.name = exam_update.name
            logger.debug(f"Updated exam name to: {existing_exam.name}")
        if exam_update.description is not None:
            existing_exam.description = exam_update.description
            logger.debug(f"Updated exam description to: {existing_exam.description}")

        # Aktualizacja pytań
        if exam_update.questions is not None:
            # Słownik istniejących pytań
            existing_questions = {q.id: q for q in existing_exam.questions if q.id is not None}
            updated_question_ids = set()

            for q in exam_update.questions:
                if q.id and q.id in existing_questions:
                    # Aktualizacja istniejącego pytania
                    existing_question = existing_questions[q.id]
                    existing_question.text = q.text
                    logger.debug(f"Updated question ID {q.id} to text: {q.text}")

                    # Aktualizacja odpowiedzi
                    existing_answers = {a.id: a for a in existing_question.answers if a.id is not None}
                    updated_answer_ids = set()

                    for a in q.answers:
                        if a.id and a.id in existing_answers:
                            # Aktualizacja istniejącej odpowiedzi
                            existing_answer = existing_answers[a.id]
                            existing_answer.text = a.text
                            existing_answer.is_correct = a.is_correct
                            logger.debug(f"Updated answer ID {a.id} -> text: {a.text}, is_correct: {a.is_correct}")
                            updated_answer_ids.add(a.id)
                        elif not a.id:
                            # Dodawanie nowej odpowiedzi
                            new_answer = ExamAnswer(
                                text=a.text,
                                is_correct=a.is_correct
                            )
                            existing_question.answers.append(new_answer)
                            logger.debug(f"Added new answer: {new_answer.text}, is_correct: {new_answer.is_correct}")

                    # Usuwanie odpowiedzi nieobecnych w aktualizacji
                    answers_to_remove = set(existing_answers.keys()) - updated_answer_ids
                    for answer_id in answers_to_remove:
                        answer_to_delete = db.query(ExamAnswer).filter(ExamAnswer.id == answer_id).first()
                        if answer_to_delete:
                            db.delete(answer_to_delete)
                            logger.debug(f"Deleted answer ID {answer_id}")

                    updated_question_ids.add(q.id)

                elif not q.id:
                    # Dodawanie nowego pytania
                    new_question = ExamQuestion(text=q.text)
                    for a in q.answers:
                        new_answer = ExamAnswer(
                            text=a.text,
                            is_correct=a.is_correct
                        )
                        new_question.answers.append(new_answer)
                        logger.debug(f"Added answer: {new_answer.text}, is_correct: {new_answer.is_correct}")
                    existing_exam.questions.append(new_question)
                    logger.debug(f"Added new question: {new_question.text}")

            # Usuwanie pytań nieobecnych w aktualizacji
            existing_question_ids = set(existing_questions.keys())
            questions_to_remove = existing_question_ids - updated_question_ids
            for question_id in questions_to_remove:
                question_to_delete = db.query(ExamQuestion).filter(ExamQuestion.id == question_id).first()
                if question_to_delete:
                    db.delete(question_to_delete)
                    logger.debug(f"Deleted question ID {question_id}")

        db.commit()
        db.refresh(existing_exam)
        logger.info(f"Updated exam with ID={exam_id} for user_id={user_id}")
        return existing_exam
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating exam: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error updating exam: {str(e)}")


@router.delete("/{exam_id}/", response_model=ExamRead)
async def delete_exam(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Usuwa egzamin o podanym ID, jeśli należy do zalogowanego użytkownika.
    """
    user_id = str(current_user.id_)
    logger.info(f"Deleting exam with ID={exam_id} for user_id={user_id}")
    try:
        exam = db.query(Exam).filter(Exam.id == exam_id, Exam.user_id == user_id).first()
        if not exam:
            logger.error(f"Exam with ID {exam_id} not found or not owned by user_id={user_id}.")
            raise HTTPException(status_code=404, detail="Exam not found.")

        db.delete(exam)
        db.commit()
        logger.info(f"Deleted exam with ID={exam_id} for user_id={user_id}")
        return exam
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting exam: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting exam: {str(e)}")
