from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlalchemy.orm import Session, joinedload
from typing import List
import logging

from ..models import (
    Exam, ExamQuestion, ExamAnswer, User, ExamResult, ExamResultAnswer,
    ShareableContent, UserExamAccess, ExamQuestion
)
from ..schemas import (
    ExamCreate,
    ExamRead,
    ExamUpdate,
    ExamResultRead,
    ExamResultCreate,
)
from ..dependencies import get_db
from ..auth import get_current_user
from ..utils import (
    create_shareable_exam, add_exam_by_code, get_user_shared_exams,
    get_shareable_content_info, deactivate_share_code,
    get_user_created_share_codes, get_sharing_statistics
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ===========================================
# STATYCZNE ENDPOINTY (bez parametrów path)
# ===========================================

@router.get("/", response_model=List[dict])
async def get_exams(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        include_shared: bool = Query(default=False, description="Include shared exams")
):
    """Pobiera wszystkie egzaminy użytkownika"""
    user_id = current_user.id_
    logger.info(f"Fetching all exams for user_id={user_id}, include_shared={include_shared}")

    try:
        # Funkcja do serializacji pytań
        def serialize_questions(questions):
            """Serializuje pytania SQLAlchemy do dict"""
            return [
                {
                    'id': q.id,
                    'text': q.text,
                    'answers': [
                        {
                            'id': a.id,
                            'text': a.text,
                            'is_correct': a.is_correct
                        }
                        for a in q.answers
                    ]
                }
                for q in questions
            ]

        # Pobierz własne egzaminy użytkownika (tylko oryginalne, nie kopie)
        own_exams = (
            db.query(Exam)
            .options(joinedload(Exam.questions).joinedload(ExamQuestion.answers))
            .filter(
                Exam.user_id == user_id,
                Exam.template_id.is_(None)  # Tylko oryginalne egzaminy
            )
            .all()
        )

        result = []

        # Dodaj własne egzaminy - ZAWSZE z pytaniami
        for exam in own_exams:
            question_count = len(exam.questions) if exam.questions else 0
            result.append({
                'id': exam.id,
                'name': exam.name,
                'description': exam.description,
                'created_at': exam.created_at.isoformat() if exam.created_at else None,
                'question_count': question_count,
                'is_shared': exam.is_template,
                'is_own': True,
                'access_type': 'owner',
                'conversation_id': exam.conversation_id,
                'questions': serialize_questions(exam.questions) if exam.questions else []  # ZAWSZE
            })

        # Jeśli requested, dodaj AKTYWNE udostępnione egzaminy - TAKŻE z pytaniami
        if include_shared:
            active_shared_access = db.query(UserExamAccess).filter(
                UserExamAccess.user_id == user_id,
                UserExamAccess.is_active == True
            ).all()

            for access in active_shared_access:
                # Załaduj pełne pytania dla udostępnionych egzaminów
                exam = db.query(Exam).options(
                    joinedload(Exam.questions).joinedload(ExamQuestion.answers)
                ).filter(Exam.id == access.user_exam_id).first()

                if exam:
                    question_count = len(exam.questions) if exam.questions else 0
                    result.append({
                        'id': exam.id,
                        'name': exam.name,
                        'description': exam.description,
                        'created_at': exam.created_at.isoformat() if exam.created_at else None,
                        'question_count': question_count,
                        'is_shared': False,
                        'is_own': False,
                        'access_type': 'shared',
                        'original_exam_id': access.original_exam_id,
                        'added_at': access.added_at.isoformat(),
                        'code_used': access.accessed_via_code,
                        'conversation_id': exam.conversation_id,
                        'questions': serialize_questions(exam.questions) if exam.questions else []  # ZAWSZE
                    })

        logger.info(f"Returning {len(result)} exams, all with questions loaded")
        return result

    except Exception as e:
        logger.error(f"Error fetching exams: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch exams")


@router.post("/", response_model=ExamRead, status_code=status.HTTP_201_CREATED)
async def create_exam(
        exam: ExamCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    """Tworzy nowy egzamin przypisany do zalogowanego użytkownika"""
    logger.info(f"Creating a new exam with name: {exam.name}")
    logger.debug(f"Exam data: {exam}")
    user_id = current_user.id_
    try:
        new_exam = Exam(
            name=exam.name,
            description=exam.description,
            user_id=user_id,
            conversation_id=0,  # Default to 0; will be updated later if needed.
            is_template=False,
            template_id=None
        )

        # Add exam questions
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


@router.post("/add-by-code")
async def add_exam_by_share_code(
        share_data: dict,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    """Dodaje egzamin do biblioteki użytkownika na podstawie kodu"""
    try:
        if not share_data.get('code'):
            raise HTTPException(status_code=400, detail="Share code is required")

        share_code = share_data.get('code').strip().upper()

        # Walidacja formatu kodu
        if len(share_code) != 12:
            raise HTTPException(status_code=400, detail="Invalid share code format")

        # Dodaj egzamin przez kod - przekaż sesję DB
        result = add_exam_by_code(current_user.id_, share_code, db)

        if result['success']:
            logger.info(f"Exam added successfully for user {current_user.id_} with code {share_code}")
            return result
        else:
            raise HTTPException(status_code=400, detail=result['message'])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding exam by code: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to add exam")


@router.get("/shared")
async def get_user_shared_exams_endpoint(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    """Pobiera listę udostępnionych egzaminów użytkownika"""
    try:
        shared_exams = get_user_shared_exams(current_user.id_, db)
        return shared_exams

    except Exception as e:
        logger.error(f"Error getting user shared exams: {e}")
        raise HTTPException(status_code=500, detail="Failed to get shared exams")


@router.get("/my-shared-codes")
async def get_my_shared_codes(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    """Pobiera listę kodów udostępniania utworzonych przez użytkownika"""
    try:
        shared_codes = get_user_created_share_codes(current_user.id_, 'exam', db)
        return shared_codes

    except Exception as e:
        logger.error(f"Error getting my shared codes: {e}")
        raise HTTPException(status_code=500, detail="Failed to get shared codes")


@router.get("/share-statistics")
async def get_exam_share_statistics(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    """Pobiera statystyki udostępniania egzaminów dla użytkownika"""
    try:
        statistics = get_sharing_statistics(current_user.id_, db)

        # Zwróć tylko statystyki związane z egzaminami
        exam_stats = {
            'created_share_codes': statistics.get('created_exam_codes', 0),
            'added_shared_exams': statistics.get('added_shared_exams', 0),
            'total_exam_accesses': statistics.get('total_exam_accesses', 0)
        }

        return exam_stats

    except Exception as e:
        logger.error(f"Error getting exam share statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get statistics")


@router.post("/submit/", response_model=ExamResultRead)
async def submit_exam_result(
        result: ExamResultCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    """Zapisuje wynik egzaminu dla użytkownika"""
    user_id = current_user.id_
    logger.info(f"Submitting exam result for user_id={user_id}, exam_id={result.exam_id}")
    try:
        # Check if exam exists and user has access (own or shared)
        exam = db.query(Exam).filter(Exam.id == result.exam_id).first()
        if not exam:
            raise HTTPException(status_code=404, detail="Exam not found")

        # Sprawdź dostęp do egzaminu
        has_access = False
        if exam.user_id == user_id:
            has_access = True
        else:
            access = db.query(UserExamAccess).filter(
                UserExamAccess.user_id == user_id,
                UserExamAccess.user_exam_id == result.exam_id,
                UserExamAccess.is_active == True
            ).first()
            if access:
                has_access = True

        if not has_access:
            raise HTTPException(status_code=403, detail="Access denied")

        # Load exam with questions and answers for scoring
        exam_with_questions = (
            db.query(Exam)
            .options(joinedload(Exam.questions).joinedload(ExamQuestion.answers))
            .filter(Exam.id == result.exam_id)
            .first()
        )

        # Create a new exam result
        exam_result = ExamResult(
            exam_id=result.exam_id,
            user_id=user_id,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        db.add(exam_result)
        db.flush()  # To obtain exam_result.id

        # Save answers and compute score
        correct_answers = 0
        total_questions = len(result.answers)

        for answer_data in result.answers:
            correct_answer = (
                db.query(ExamAnswer)
                .filter(
                    ExamAnswer.question_id == answer_data.question_id,
                    ExamAnswer.id == answer_data.selected_answer_id,
                    ExamAnswer.is_correct == True
                )
                .first()
            )
            exam_result_answer = ExamResultAnswer(
                exam_result_id=exam_result.id,
                question_id=answer_data.question_id,
                selected_answer_id=answer_data.selected_answer_id,
                is_correct=bool(correct_answer),
                answer_time=answer_data.answer_time
            )
            if correct_answer:
                correct_answers += 1
            db.add(exam_result_answer)

        exam_result.score = (correct_answers / total_questions) * 100 if total_questions > 0 else 0

        db.commit()
        db.refresh(exam_result)
        return exam_result

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error submitting exam result: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error submitting exam result: {str(e)}")


@router.get("/results/", response_model=List[ExamResultRead])
async def get_user_results(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    """Pobiera wszystkie wyniki egzaminów dla zalogowanego użytkownika"""
    user_id = current_user.id_
    logger.info(f"Fetching exam results for user_id={user_id}")
    try:
        results = (
            db.query(ExamResult)
            .options(joinedload(ExamResult.answers))
            .filter(ExamResult.user_id == user_id)
            .all()
        )
        return results
    except Exception as e:
        logger.error(f"Error fetching exam results: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching exam results: {str(e)}")


# ===========================================
# ENDPOINTY Z PREFIKSAMI (share-info, shared, shared-code)
# ===========================================

@router.get("/share-info/{share_code}")
async def get_exam_share_info(
        share_code: str,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    """Pobiera informacje o udostępnianym egzaminie przed dodaniem"""
    try:
        share_code = share_code.strip().upper()

        info = get_shareable_content_info(share_code, 'exam', db)
        if not info:
            raise HTTPException(status_code=404, detail="Invalid or expired share code")

        # Sprawdź czy użytkownik już ma ten egzamin
        existing_access = db.query(UserExamAccess).filter(
            UserExamAccess.user_id == current_user.id_,
            UserExamAccess.original_exam_id == info['content_id'],
            UserExamAccess.is_active == True
        ).first()

        info['already_added'] = existing_access is not None

        # Sprawdź czy to własny egzamin użytkownika
        own_exam = db.query(Exam).filter(
            Exam.id == info['content_id'],
            Exam.user_id == current_user.id_
        ).first()
        info['is_own_exam'] = own_exam is not None

        return info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting exam share info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get share info")


@router.delete("/shared/{exam_id}")
async def remove_shared_exam(
        exam_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    """Usuwa udostępniony egzamin z biblioteki użytkownika (tylko dezaktywacja dostępu)"""
    try:
        logger.info(f"Removing shared exam {exam_id} from user {current_user.id_} library")

        # Sprawdź czy użytkownik ma dostęp do tego egzaminu jako udostępniony
        access = db.query(UserExamAccess).filter(
            UserExamAccess.user_id == current_user.id_,
            UserExamAccess.user_exam_id == exam_id,
            UserExamAccess.is_active == True
        ).first()

        if not access:
            logger.warning(f"Shared exam access {exam_id} not found for user {current_user.id_}")
            raise HTTPException(status_code=404, detail="Shared exam not found in your library")

        # Sprawdź czy to rzeczywiście udostępniony egzamin (ma template_id)
        user_exam = db.query(Exam).filter(
            Exam.id == exam_id,
            Exam.template_id.isnot(None)  # Upewnij się, że to kopia
        ).first()

        if not user_exam:
            logger.warning(f"Exam {exam_id} is not a shared exam copy")
            raise HTTPException(status_code=400, detail="This is not a shared exam")

        # TYLKO DEZAKTYWUJ DOSTĘP - nie usuwaj fizycznie
        access.is_active = False

        db.commit()

        logger.info(f"Successfully removed shared exam {exam_id} from user {current_user.id_} library")

        return {
            'success': True,
            'message': f'Exam "{user_exam.name}" removed from your library. The original exam remains available to its owner.'
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing shared exam from library: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to remove exam from library")


@router.post("/shared-code/{share_code}/deactivate")
async def deactivate_exam_share_code(
        share_code: str,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    """Dezaktywuje kod udostępniania egzaminu"""
    try:
        shared_content = db.query(ShareableContent).filter(
            ShareableContent.share_code == share_code.upper(),
            ShareableContent.creator_id == current_user.id_,
            ShareableContent.content_type == 'exam',
            ShareableContent.is_public == True
        ).first()

        if not shared_content:
            raise HTTPException(status_code=404, detail="Share code not found")

        # Dezaktywuj kod
        shared_content.is_public = False
        db.commit()

        logger.info(f"Share code {share_code} deactivated by user {current_user.id_}")

        return {
            'success': True,
            'message': 'Share code has been deactivated successfully'
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating share code: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to deactivate share code")


# ===========================================
# DYNAMICZNE ENDPOINTY (z parametrem exam_id)
# ===========================================

@router.get("/{exam_id}/", response_model=ExamRead)
async def get_exam(
        exam_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    """Pobiera szczegóły konkretnego egzaminu"""
    user_id = current_user.id_
    logger.info(f"Fetching exam with ID={exam_id} for user_id={user_id}")
    try:
        # Sprawdź czy egzamin należy do użytkownika lub czy ma do niego dostęp
        exam = (
            db.query(Exam)
            .options(joinedload(Exam.questions).joinedload(ExamQuestion.answers))
            .filter(Exam.id == exam_id)
            .first()
        )

        if not exam:
            raise HTTPException(status_code=404, detail="Exam not found")

        # Sprawdź uprawnienia
        has_access = False
        if exam.user_id == user_id:
            has_access = True
        else:
            # Sprawdź czy użytkownik ma dostęp przez udostępnienie
            access = db.query(UserExamAccess).filter(
                UserExamAccess.user_id == user_id,
                UserExamAccess.user_exam_id == exam_id,
                UserExamAccess.is_active == True
            ).first()
            if access:
                has_access = True

        if not has_access:
            raise HTTPException(status_code=403, detail="Access denied")

        logger.debug(f"Fetched exam: {exam}")
        return exam

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching exam: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch exam")


@router.put("/{exam_id}/", response_model=ExamRead)
async def update_exam(
        exam_id: int,
        exam_update: ExamUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    """Aktualizuje egzamin o podanym ID jeśli należy do zalogowanego użytkownika"""
    user_id = current_user.id_
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
            raise HTTPException(status_code=404, detail="Exam not found or access denied")

        # Nie pozwalaj na edycję szablonów jeśli są udostępnione
        if existing_exam.is_template:
            shared_content = db.query(ShareableContent).filter(
                ShareableContent.content_type == 'exam',
                ShareableContent.content_id == exam_id,
                ShareableContent.is_public == True
            ).first()
            if shared_content and shared_content.access_count > 0:
                raise HTTPException(
                    status_code=403,
                    detail="Cannot edit exam that has been shared and accessed by others"
                )

        # Update basic fields, including conversation_id if provided
        if exam_update.name is not None:
            existing_exam.name = exam_update.name
            logger.debug(f"Updated exam name to: {existing_exam.name}")
        if exam_update.description is not None:
            existing_exam.description = exam_update.description
            logger.debug(f"Updated exam description to: {existing_exam.description}")
        if exam_update.conversation_id is not None:
            existing_exam.conversation_id = exam_update.conversation_id
            logger.debug(f"Updated exam conversation_id to: {existing_exam.conversation_id}")

        # Update exam questions and answers
        if exam_update.questions is not None:
            existing_questions = {q.id: q for q in existing_exam.questions if q.id is not None}
            updated_question_ids = set()

            for q in exam_update.questions:
                if q.id and q.id in existing_questions:
                    existing_question = existing_questions[q.id]
                    existing_question.text = q.text
                    logger.debug(f"Updated question ID {q.id} to text: {q.text}")

                    existing_answers = {a.id: a for a in existing_question.answers if a.id is not None}
                    updated_answer_ids = set()

                    for a in q.answers:
                        if a.id and a.id in existing_answers:
                            existing_answer = existing_answers[a.id]
                            existing_answer.text = a.text
                            existing_answer.is_correct = a.is_correct
                            logger.debug(f"Updated answer ID {a.id} -> text: {a.text}, is_correct: {a.is_correct}")
                            updated_answer_ids.add(a.id)
                        elif not a.id:
                            new_answer = ExamAnswer(
                                text=a.text,
                                is_correct=a.is_correct
                            )
                            existing_question.answers.append(new_answer)
                            logger.debug(f"Added new answer: {new_answer.text}, is_correct: {new_answer.is_correct}")
                    answers_to_remove = set(existing_answers.keys()) - updated_answer_ids
                    for answer_id in answers_to_remove:
                        answer_to_delete = db.query(ExamAnswer).filter(ExamAnswer.id == answer_id).first()
                        if answer_to_delete:
                            db.delete(answer_to_delete)
                            logger.debug(f"Deleted answer ID {answer_id}")
                    updated_question_ids.add(q.id)
                elif not q.id:
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
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating exam: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update exam")


@router.delete("/{exam_id}/")
async def delete_owned_exam(
        exam_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    """Usuwa egzamin należący do użytkownika (tylko właściciel)"""
    user_id = current_user.id_
    logger.info(f"Deleting exam with ID={exam_id} for user_id={user_id}")
    try:
        exam = db.query(Exam).filter(
            Exam.id == exam_id,
            Exam.user_id == user_id,
            Exam.template_id.is_(None)  # Tylko oryginalne egzaminy, nie kopie
        ).first()

        if not exam:
            logger.error(f"Exam with ID {exam_id} not found or not owned by user_id={user_id}.")
            raise HTTPException(
                status_code=404,
                detail="Exam not found or you don't have permission to delete it"
            )

        # Sprawdź czy egzamin jest udostępniony i ma aktywne kopie
        if exam.is_template:
            active_shares = db.query(UserExamAccess).filter(
                UserExamAccess.original_exam_id == exam_id,
                UserExamAccess.is_active == True
            ).count()

            if active_shares > 0:
                logger.warning(f"Cannot delete exam {exam_id} - has {active_shares} active shares")
                raise HTTPException(
                    status_code=403,
                    detail=f"Cannot delete exam that is currently shared with {active_shares} user(s). "
                           f"First deactivate all share codes or wait for users to remove it from their libraries."
                )

        # Dezaktywuj kod udostępniania jeśli istnieje
        shareable_content = db.query(ShareableContent).filter(
            ShareableContent.content_type == 'exam',
            ShareableContent.content_id == exam_id,
            ShareableContent.is_public == True
        ).first()

        if shareable_content:
            shareable_content.is_public = False
            logger.info(f"Deactivated share code for exam {exam_id}")

        # Usuń pytania i odpowiedzi
        questions = db.query(ExamQuestion).filter(ExamQuestion.exam_id == exam_id).all()
        for question in questions:
            db.query(ExamAnswer).filter(ExamAnswer.question_id == question.id).delete()
            db.delete(question)

        # Usuń egzamin
        db.delete(exam)
        db.commit()

        logger.info(f"Successfully deleted owned exam {exam_id} by user {user_id}")

        return {
            'success': True,
            'message': 'Exam deleted successfully'
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting exam: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete exam")


@router.post("/{exam_id}/share")
async def create_exam_share_code(
        exam_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    """Generuje kod udostępniania dla egzaminu"""
    try:
        logger.info(f"Creating share code for exam {exam_id} by user {current_user.id_}")

        # Sprawdź czy użytkownik jest właścicielem egzaminu
        exam = db.query(Exam).filter(
            Exam.id == exam_id,
            Exam.user_id == current_user.id_
        ).first()

        if not exam:
            logger.warning(f"Exam {exam_id} not found or access denied for user {current_user.id_}")
            raise HTTPException(status_code=404, detail="Exam not found or access denied")

        # Sprawdź czy egzamin ma pytania
        question_count = db.query(ExamQuestion).filter(ExamQuestion.exam_id == exam_id).count()
        if question_count == 0:
            logger.warning(f"Cannot share empty exam {exam_id}")
            raise HTTPException(status_code=400, detail="Cannot share empty exam")

        # Utwórz udostępnialny egzamin - przekaż sesję DB
        share_code = create_shareable_exam(exam_id, current_user.id_, db)

        logger.info(f"Share code created successfully: {share_code} for exam {exam_id}")

        return {
            'success': True,
            'share_code': share_code,
            'exam_name': exam.name,
            'message': 'Share code generated successfully'
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating exam share code: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create share code")
