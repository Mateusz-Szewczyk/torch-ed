from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, date, timedelta
from sqlalchemy import func, and_

from ..dependencies import get_db
from ..auth import get_current_user
from ..models import (
    StudyRecord as StudyRecordModel,
    UserFlashcard as UserFlashcardModel,
    StudySession as StudySessionModel,
    ExamResultAnswer as ExamResultAnswerModel,
    ExamResult as ExamResultModel,
    UserDeckAccess,
    UserExamAccess,
    Deck,
    Exam,
    User,
    Flashcard,
    ExamQuestion,
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
    Rozszerzone o udostępnione materiały zachowując wsteczną kompatybilność.
    """
    user_id = current_user.id_
    try:
        # === ORYGINALNE ZAPYTANIA (zachowane dla kompatybilności) ===

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
        ) if exam_result_ids else []

        # === ROZSZERZONE ZAPYTANIA (nowe dane) ===

        # Pobierz wszystkie decki użytkownika (własne + udostępnione)
        # Własne decki
        own_deck_ids = set()
        own_decks = db.query(Deck).filter(
            Deck.user_id == user_id,
            Deck.template_id.is_(None)  # Wyklucz kopie z udostępnionych
        ).all()
        own_deck_ids = {deck.id for deck in own_decks}

        # Udostępnione decki (kopie użytkownika)
        shared_deck_access = db.query(UserDeckAccess).filter(
            UserDeckAccess.user_id == user_id,
            UserDeckAccess.is_active == True
        ).all()

        shared_deck_ids = set()
        shared_decks_info = {}
        for access in shared_deck_access:
            shared_deck_ids.add(access.user_deck_id)
            shared_decks_info[access.user_deck_id] = {
                'original_deck_id': access.original_deck_id,
                'code_used': access.accessed_via_code,
                'added_at': access.added_at
            }

        # Pobierz wszystkie egzaminy użytkownika (własne + udostępnione)
        # Własne egzaminy
        own_exam_ids = set()
        own_exams = db.query(Exam).filter(
            Exam.user_id == user_id,
            Exam.template_id.is_(None)  # Wyklucz kopie z udostępnionych
        ).all()
        own_exam_ids = {exam.id for exam in own_exams}

        # Udostępnione egzaminy (kopie użytkownika)
        shared_exam_access = db.query(UserExamAccess).filter(
            UserExamAccess.user_id == user_id,
            UserExamAccess.is_active == True
        ).all()

        shared_exam_ids = set()
        shared_exams_info = {}
        for access in shared_exam_access:
            shared_exam_ids.add(access.user_exam_id)
            shared_exams_info[access.user_exam_id] = {
                'original_exam_id': access.original_exam_id,
                'code_used': access.accessed_via_code,
                'added_at': access.added_at
            }

        # Pobierz nazwy wszystkich decków (własne + udostępnione)
        all_deck_ids = own_deck_ids.union(shared_deck_ids)
        all_decks = db.query(Deck).filter(Deck.id.in_(all_deck_ids)).all() if all_deck_ids else []

        # Rozszerzone mapowanie nazw decków z informacją o typie dostępu
        deck_id_to_name = {}
        deck_id_to_info = {}

        for deck in all_decks:
            deck_id_to_name[deck.id] = deck.name  # Zachowane dla kompatybilności
            deck_id_to_info[deck.id] = {
                'name': deck.name,
                'access_type': 'shared' if deck.id in shared_deck_ids else 'own',
                'user_id': deck.user_id,
                'created_at': deck.created_at.isoformat() if deck.created_at else None
            }

            # Dodaj informacje o udostępnieniu jeśli to kopia
            if deck.id in shared_decks_info:
                deck_id_to_info[deck.id].update(shared_decks_info[deck.id])
                if 'added_at' in deck_id_to_info[deck.id] and deck_id_to_info[deck.id]['added_at']:
                    deck_id_to_info[deck.id]['added_at'] = deck_id_to_info[deck.id]['added_at'].isoformat()

        # Pobierz nazwy wszystkich egzaminów (własne + udostępnione)
        all_exam_ids = own_exam_ids.union(shared_exam_ids)
        all_exams = db.query(Exam).filter(Exam.id.in_(all_exam_ids)).all() if all_exam_ids else []

        # Mapowanie nazw egzaminów z informacją o typie dostępu
        exam_id_to_name = {}
        exam_id_to_info = {}

        for exam in all_exams:
            exam_id_to_name[exam.id] = exam.name
            exam_id_to_info[exam.id] = {
                'name': exam.name,
                'access_type': 'shared' if exam.id in shared_exam_ids else 'own',
                'user_id': exam.user_id,
                'created_at': exam.created_at.isoformat() if exam.created_at else None
            }

            # Dodaj informacje o udostępnieniu jeśli to kopia
            if exam.id in shared_exams_info:
                exam_id_to_info[exam.id].update(shared_exams_info[exam.id])
                if 'added_at' in exam_id_to_info[exam.id] and exam_id_to_info[exam.id]['added_at']:
                    exam_id_to_info[exam.id]['added_at'] = exam_id_to_info[exam.id]['added_at'].isoformat()

        # === ORYGINALNE OBLICZENIA (zachowane) ===

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

        # === FUNKCJA SERIALIZUJĄCA (oryginalna) ===

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

        # Serializacja wszystkich danych (oryginalna struktura)
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

        # === DODATKOWE STATYSTYKI (nowe, ale opcjonalne) ===

        # Liczniki materiałów
        material_counts = {
            'decks': {
                'total': len(all_deck_ids),
                'own': len(own_deck_ids),
                'shared': len(shared_deck_ids)
            },
            'exams': {
                'total': len(all_exam_ids),
                'own': len(own_exam_ids),
                'shared': len(shared_exam_ids)
            }
        }

        # Aktywność z ostatniego tygodnia
        week_ago = datetime.now() - timedelta(days=7)
        recent_activity = {
            'study_sessions_this_week': len([s for s in study_sessions_result if s.started_at >= week_ago]),
            'exam_attempts_this_week': len([r[0] for r in exam_results_result if r[0].started_at >= week_ago]),
            'total_study_sessions': len(study_sessions_result),
            'total_exam_attempts': len(exam_results_result),
            'total_cards_studied': len(serialized_study_records)
        }

        # === ODPOWIEDŹ (zachowana oryginalna struktura + rozszerzenia) ===

        response = {
            # ORYGINALNE POLA (zachowane dla kompatybilności wstecznej)
            "study_records": serialized_study_records,
            "user_flashcards": serialized_user_flashcards,
            "study_sessions": serialized_study_sessions,
            "exam_result_answers": serialized_exam_result_answers,
            "exam_results": serialized_exam_results,
            "session_durations": session_durations,
            "exam_daily_average": exam_daily_average_serialized,
            "flashcard_daily_average": flashcard_daily_average_serialized,
            "deck_names": deck_id_to_name,  # Zachowane dla kompatybilności

            # NOWE POLA (rozszerzenia, które nie wpływają na istniejący frontend)
            "deck_info": deck_id_to_info,
            "exam_info": exam_id_to_info,
            "exam_names": exam_id_to_name,
            "material_counts": material_counts,
            "recent_activity": recent_activity,

            # Dodatkowe mapowania pomocnicze
            "access_info": {
                "shared_decks": shared_decks_info,
                "shared_exams": shared_exams_info
            }
        }

        return response

    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
