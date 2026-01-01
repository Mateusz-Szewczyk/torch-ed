from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, date, timedelta
import datetime
from sqlalchemy import func, and_, or_, case
from typing import Optional, List, Dict, Any
from fastapi_cache.decorator import cache
from fastapi_cache import FastAPICache
import logging

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
logger = logging.getLogger(__name__)


async def invalidate_user_dashboard_cache(user_id: int):
    """
    Invaliduje cache dashboardu dla konkretnego użytkownika.
    Wywołuj po zakończeniu sesji nauki, zapisaniu bulk_record, lub zakończeniu egzaminu.
    """
    try:
        backend = FastAPICache.get_backend()
        # Usuń cache dla wszystkich endpointów dashboardu dla tego użytkownika
        # FastAPI-cache używa prefiksu i klucza opartego na parametrach
        cache_keys_patterns = [
            f"fastapi-cache:get_dashboard_data*user_id={user_id}*",
            f"fastapi-cache:get_calendar_heatmap*user_id={user_id}*",
            f"fastapi-cache:get_deck_stats*user_id={user_id}*",
            f"fastapi-cache:get_daily_goal*user_id={user_id}*",
            f"fastapi-cache:get_goals*user_id={user_id}*",
        ]

        # Dla Redis backend możemy użyć scan i delete
        if hasattr(backend, '_redis'):
            redis_client = backend._redis
            for pattern in cache_keys_patterns:
                try:
                    # Używamy scan_iter zamiast keys dla bezpieczeństwa
                    async for key in redis_client.scan_iter(match=pattern):
                        await redis_client.delete(key)
                        logger.debug(f"Deleted cache key: {key}")
                except Exception as e:
                    logger.warning(f"Failed to delete cache for pattern {pattern}: {e}")
        else:
            # Dla InMemory backend - nie ma natywnej inwalidacji per-user
            # Cache wygaśnie naturalnie po TTL
            logger.debug(f"InMemory backend - cache will expire naturally for user {user_id}")

        logger.info(f"Dashboard cache invalidated for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to invalidate dashboard cache for user {user_id}: {e}")
        return False


# =============================================
# HELPER FUNCTIONS
# =============================================

def calculate_study_streak(study_sessions: List[StudySessionModel], exam_results: List) -> Dict[str, Any]:
    """
    Oblicza study streak - liczbę kolejnych dni nauki.
    Uwzględnia zarówno sesje fiszek jak i egzaminy.
    Zwraca current streak, longest streak i informację czy aktywny dzisiaj.
    """
    if not study_sessions and not exam_results:
        return {'current': 0, 'longest': 0, 'is_active_today': False}

    # Zbierz wszystkie daty aktywności
    study_dates = set()

    for session in study_sessions:
        try:
            started = getattr(session, 'started_at', None)
            if started:
                study_dates.add(started.date())
        except Exception as e:
            logger.warning(f"Error accessing session.started_at: {e}")
            continue

    for result in exam_results:
        try:
            exam_result = result[0] if isinstance(result, tuple) else result
            started = getattr(exam_result, 'started_at', None)
            if started:
                study_dates.add(started.date())
        except Exception as e:
            logger.warning(f"Error accessing exam_result.started_at: {e}")
            continue

    if not study_dates:
        return {'current': 0, 'longest': 0, 'is_active_today': False}

    today = date.today()
    yesterday = today - timedelta(days=1)
    is_active_today = today in study_dates

    # Sortuj daty malejąco
    sorted_dates = sorted(study_dates, reverse=True)

    # Oblicz current streak
    current_streak = 0
    if sorted_dates[0] == today or sorted_dates[0] == yesterday:
        current_date = sorted_dates[0]
        for study_date in sorted_dates:
            if study_date == current_date:
                current_streak += 1
                current_date = current_date - timedelta(days=1)
            else:
                break

    # Oblicz longest streak
    longest_streak = 0
    if sorted_dates:
        sorted_asc = sorted(study_dates)
        current_run = 1
        for i in range(1, len(sorted_asc)):
            if (sorted_asc[i] - sorted_asc[i-1]).days == 1:
                current_run += 1
            else:
                longest_streak = max(longest_streak, current_run)
                current_run = 1
        longest_streak = max(longest_streak, current_run)

    return {
        'current': current_streak,
        'longest': longest_streak,
        'is_active_today': is_active_today
    }


def get_period_stats(
    study_records: List[StudyRecordModel],
    study_sessions: List[StudySessionModel],
    exam_results: List,
    start_date: datetime,
    end_date: datetime
) -> Dict[str, Any]:
    """
    Oblicza statystyki dla określonego przedziału czasowego.
    """
    # Filtruj rekordy studiów
    period_records = [
        r for r in study_records
        if r.reviewed_at and start_date <= r.reviewed_at <= end_date
    ]

    # Filtruj sesje studiów
    period_sessions = []
    for s in study_sessions:
        try:
            started = getattr(s, 'started_at', None)
            if started and start_date <= started <= end_date:
                period_sessions.append(s)
        except Exception:
            continue

    # Filtruj wyniki egzaminów
    period_exams = []
    for r in exam_results:
        try:
            exam_result = r[0] if isinstance(r, tuple) else r
            started = getattr(exam_result, 'started_at', None)
            if started and start_date <= started <= end_date:
                period_exams.append(r)
        except Exception:
            continue

    # Oblicz statystyki
    total_flashcards = len(period_records)
    total_sessions = len(period_sessions)
    total_exams = len(period_exams)

    # Średni rating fiszek
    avg_rating = 0.0
    if period_records:
        valid_ratings = [r.rating for r in period_records if r.rating is not None]
        if valid_ratings:
            avg_rating = sum(valid_ratings) / len(valid_ratings)

    # Średni wynik egzaminów
    avg_exam_score = 0.0
    if period_exams:
        exam_scores = []
        for r in period_exams:
            exam_result = r[0] if isinstance(r, tuple) else r
            if exam_result.score is not None:
                exam_scores.append(exam_result.score)
        if exam_scores:
            avg_exam_score = sum(exam_scores) / len(exam_scores)

    # Łączny czas nauki (w godzinach)
    total_study_hours = 0.0
    for session in period_sessions:
        try:
            completed = getattr(session, 'completed_at', None)
            started = getattr(session, 'started_at', None)
            if completed and started:
                duration = (completed - started).total_seconds() / 3600
                if 0 <= duration <= 24:  # Sanity check
                    total_study_hours += duration
        except Exception:
            continue

    # Unikalne dni nauki
    study_days = set()
    for session in period_sessions:
        try:
            started = getattr(session, 'started_at', None)
            if started:
                study_days.add(started.date())
        except Exception:
            continue
    for exam in period_exams:
        try:
            exam_result = exam[0] if isinstance(exam, tuple) else exam
            started = getattr(exam_result, 'started_at', None)
            if started:
                study_days.add(started.date())
        except Exception:
            continue

    return {
        'flashcards_studied': total_flashcards,
        'study_sessions': total_sessions,
        'exams_completed': total_exams,
        'average_flashcard_rating': round(avg_rating, 2),
        'average_exam_score': round(avg_exam_score, 2),
        'total_study_hours': round(total_study_hours, 2),
        'active_days': len(study_days)
    }


def get_deck_statistics(
    deck: Deck,
    user_flashcards: List[UserFlashcardModel],
    study_records: List[StudyRecordModel],
    study_sessions: List[StudySessionModel],
    user_id: int
) -> Dict[str, Any]:
    """
    Oblicza szczegółowe statystyki dla konkretnego decka.
    """
    # Fiszki należące do tego decka
    deck_flashcard_ids = {f.id for f in deck.flashcards} if deck.flashcards else set()

    # UserFlashcards dla tego decka
    deck_user_flashcards = [
        uf for uf in user_flashcards
        if uf.flashcard_id in deck_flashcard_ids
    ]

    total_cards = len(deck_flashcard_ids)
    studied_cards = len(deck_user_flashcards)

    # Mastery levels
    mastered = len([uf for uf in deck_user_flashcards if uf.ef > 2.5])
    learning = len([uf for uf in deck_user_flashcards if 1.8 < uf.ef <= 2.5])
    difficult = len([uf for uf in deck_user_flashcards if uf.ef <= 1.8])
    not_started = total_cards - studied_cards

    # Sesje dla tego decka
    deck_sessions = [s for s in study_sessions if s.deck_id == deck.id]

    # Oblicz łączny czas nauki
    total_study_hours = 0.0
    for session in deck_sessions:
        try:
            completed = getattr(session, 'completed_at', None)
            started = getattr(session, 'started_at', None)
            if completed and started:
                duration = (completed - started).total_seconds() / 3600
                if 0 <= duration <= 24:
                    total_study_hours += duration
        except Exception:
            continue

    # Średni EF
    avg_ef = 2.5  # default
    if deck_user_flashcards:
        avg_ef = sum(uf.ef for uf in deck_user_flashcards) / len(deck_user_flashcards)

    # Następna sesja (najbliższa data next_review)
    now = datetime.utcnow()
    next_review = None
    if deck_user_flashcards:
        upcoming_reviews = [uf.next_review for uf in deck_user_flashcards if uf.next_review]
        if upcoming_reviews:
            next_review = min(upcoming_reviews)

    # Karty do przeglądu dziś
    cards_due_today = len([
        uf for uf in deck_user_flashcards
        if uf.next_review and uf.next_review <= now
    ])

    # Ostatnia sesja
    last_session = None
    if deck_sessions:
        valid_sessions = []
        for s in deck_sessions:
            try:
                started = getattr(s, 'started_at', None)
                if started:
                    valid_sessions.append(started)
            except Exception:
                continue
        if valid_sessions:
            last_session = max(valid_sessions)

    # Completion percentage
    completion = 0.0
    if total_cards > 0:
        completion = round((mastered / total_cards) * 100, 1)

    return {
        'deck_id': deck.id,
        'deck_name': deck.name,
        'total_cards': total_cards,
        'studied_cards': studied_cards,
        'mastered_cards': mastered,
        'learning_cards': learning,
        'difficult_cards': difficult,
        'not_started_cards': not_started,
        'completion_percentage': completion,
        'average_ef': round(avg_ef, 2),
        'total_study_hours': round(total_study_hours, 2),
        'total_sessions': len(deck_sessions),
        'cards_due_today': cards_due_today,
        'next_review_date': next_review.isoformat() if next_review else None,
        'last_session_date': last_session.isoformat() if last_session else None
    }


def serialize(obj):
    """Konwertuje obiekt ORM na słownik, obsługując pola datetime."""
    result = {}
    try:
        for col in obj.__table__.columns:
            try:
                value = getattr(obj, col.name, None)
                if value is None:
                    result[col.name] = None
                elif isinstance(value, (datetime, date)):
                    result[col.name] = value.isoformat()
                else:
                    result[col.name] = value
            except Exception as e:
                logger.warning(f"Error serializing column {col.name}: {e}")
                result[col.name] = None
    except Exception as e:
        logger.error(f"Error serializing object: {e}")
        return {}
    return result


def calculate_change(current: float, previous: float) -> Dict[str, Any]:
    """Oblicza zmianę procentową między okresami."""
    import math

    # Handle NaN and Infinity cases
    if math.isnan(current) or math.isnan(previous):
        return {'value': 0, 'percentage': 0, 'trend': 'neutral'}
    if math.isinf(current) or math.isinf(previous):
        return {'value': 0, 'percentage': 0, 'trend': 'neutral'}

    if previous == 0:
        if current == 0:
            return {'value': 0, 'percentage': 0, 'trend': 'neutral'}
        return {'value': current, 'percentage': 100, 'trend': 'up'}

    change = current - previous
    percentage = round((change / previous) * 100, 1)

    # Cap percentage to avoid extreme values
    percentage = max(-1000, min(1000, percentage))

    trend = 'up' if change > 0 else ('down' if change < 0 else 'neutral')

    return {'value': round(change, 2), 'percentage': percentage, 'trend': trend}


@router.get("/")
@router.get("")  # Obsługa zarówno z, jak i bez trailing slash
@cache(expire=60)  # Cache na 60 sekund
async def get_dashboard_data(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    """
    Pobiera kompletne dane dashboardu dla uwierzytelnionego użytkownika.
    Zawiera rozszerzone statystyki, porównania czasowe i szczegółowe metryki.

    Cache: 60 sekund (invalidowany po zmianach danych)
    """
    user_id = current_user.id_
    now = datetime.utcnow()
    today = now.date()

    try:
        # === PODSTAWOWE ZAPYTANIA ===

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

        # === DECKI I EGZAMINY ===

        # Własne decki
        own_decks = db.query(Deck).options(joinedload(Deck.flashcards)).filter(
            Deck.user_id == user_id,
            Deck.template_id.is_(None)
        ).all()
        own_deck_ids = {deck.id for deck in own_decks}

        # Udostępnione decki
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
                'added_at': access.added_at.isoformat() if access.added_at else None
            }

        # Własne egzaminy
        own_exams = db.query(Exam).filter(
            Exam.user_id == user_id,
            Exam.template_id.is_(None)
        ).all()
        own_exam_ids = {exam.id for exam in own_exams}

        # Udostępnione egzaminy
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
                'added_at': access.added_at.isoformat() if access.added_at else None
            }

        # Pobierz wszystkie decki z fiszkami
        all_deck_ids = own_deck_ids.union(shared_deck_ids)
        all_decks = db.query(Deck).options(joinedload(Deck.flashcards)).filter(
            Deck.id.in_(all_deck_ids)
        ).all() if all_deck_ids else []

        # Mapowania
        deck_id_to_name = {deck.id: deck.name for deck in all_decks}
        deck_id_to_info = {}
        for deck in all_decks:
            deck_id_to_info[deck.id] = {
                'name': deck.name,
                'access_type': 'shared' if deck.id in shared_deck_ids else 'own',
                'user_id': deck.user_id,
                'created_at': deck.created_at.isoformat() if deck.created_at else None,
                'flashcard_count': len(deck.flashcards) if deck.flashcards else 0
            }
            if deck.id in shared_decks_info:
                deck_id_to_info[deck.id].update(shared_decks_info[deck.id])

        all_exam_ids = own_exam_ids.union(shared_exam_ids)
        all_exams = db.query(Exam).filter(Exam.id.in_(all_exam_ids)).all() if all_exam_ids else []

        exam_id_to_name = {exam.id: exam.name for exam in all_exams}
        exam_id_to_info = {}
        for exam in all_exams:
            exam_id_to_info[exam.id] = {
                'name': exam.name,
                'access_type': 'shared' if exam.id in shared_exam_ids else 'own',
                'user_id': exam.user_id,
                'created_at': exam.created_at.isoformat() if exam.created_at else None
            }
            if exam.id in shared_exams_info:
                exam_id_to_info[exam.id].update(shared_exams_info[exam.id])

        # === OBLICZENIA CZASOWE ===

        # Definicje przedziałów czasowych
        today_start = today
        today_end = today

        week_start = datetime.combine(today - timedelta(days=today.weekday()), datetime.min.time())
        week_end = today_end

        last_week_start = week_start - timedelta(days=7)
        last_week_end = week_start - timedelta(seconds=1)

        month_start = datetime.combine(today.replace(day=1), datetime.min.time())
        month_end = today_end

        # Poprzedni miesiąc
        if today.month == 1:
            last_month_start = datetime.combine(date(today.year - 1, 12, 1), datetime.min.time())
        else:
            last_month_start = datetime.combine(date(today.year, today.month - 1, 1), datetime.min.time())
        last_month_end = month_start - timedelta(seconds=1)

        year_start = datetime.combine(date(today.year, 1, 1), datetime.min.time())
        year_end = today_end

        # Oblicz statystyki dla każdego okresu
        stats_today = get_period_stats(
            study_records_result, study_sessions_result, exam_results_result,
            today_start, today_end
        )

        stats_this_week = get_period_stats(
            study_records_result, study_sessions_result, exam_results_result,
            week_start, week_end
        )

        stats_last_week = get_period_stats(
            study_records_result, study_sessions_result, exam_results_result,
            last_week_start, last_week_end
        )

        stats_this_month = get_period_stats(
            study_records_result, study_sessions_result, exam_results_result,
            month_start, month_end
        )

        stats_last_month = get_period_stats(
            study_records_result, study_sessions_result, exam_results_result,
            last_month_start, last_month_end
        )

        stats_this_year = get_period_stats(
            study_records_result, study_sessions_result, exam_results_result,
            year_start, year_end
        )

        # === PORÓWNANIA ===

        week_comparison = {
            'flashcards': calculate_change(
                stats_this_week['flashcards_studied'],
                stats_last_week['flashcards_studied']
            ),
            'study_hours': calculate_change(
                stats_this_week['total_study_hours'],
                stats_last_week['total_study_hours']
            ),
            'exams': calculate_change(
                stats_this_week['exams_completed'],
                stats_last_week['exams_completed']
            ),
            'avg_rating': calculate_change(
                stats_this_week['average_flashcard_rating'],
                stats_last_week['average_flashcard_rating']
            ),
            'avg_exam_score': calculate_change(
                stats_this_week['average_exam_score'],
                stats_last_week['average_exam_score']
            )
        }

        month_comparison = {
            'flashcards': calculate_change(
                stats_this_month['flashcards_studied'],
                stats_last_month['flashcards_studied']
            ),
            'study_hours': calculate_change(
                stats_this_month['total_study_hours'],
                stats_last_month['total_study_hours']
            ),
            'exams': calculate_change(
                stats_this_month['exams_completed'],
                stats_last_month['exams_completed']
            ),
            'avg_rating': calculate_change(
                stats_this_month['average_flashcard_rating'],
                stats_last_month['average_flashcard_rating']
            ),
            'avg_exam_score': calculate_change(
                stats_this_month['average_exam_score'],
                stats_last_month['average_exam_score']
            )
        }

        # === STUDY STREAK ===
        study_streak = calculate_study_streak(study_sessions_result, exam_results_result)

        # === FLASHCARD MASTERY STATISTICS ===
        total_user_flashcards = len(user_flashcards_result)
        mastered_flashcards = len([uf for uf in user_flashcards_result if uf.ef > 2.5])
        learning_flashcards = len([uf for uf in user_flashcards_result if 1.8 < uf.ef <= 2.5])
        difficult_flashcards = len([uf for uf in user_flashcards_result if uf.ef <= 1.8])

        # Karty do przeglądu dziś
        cards_due_today = len([
            uf for uf in user_flashcards_result
            if uf.next_review and uf.next_review <= now
        ])

        # Najbliższa sesja nauki
        upcoming_reviews = [uf.next_review for uf in user_flashcards_result if uf.next_review and uf.next_review > now]
        next_study_session = min(upcoming_reviews).isoformat() if upcoming_reviews else None

        flashcard_mastery = {
            'total': total_user_flashcards,
            'mastered': mastered_flashcards,
            'learning': learning_flashcards,
            'difficult': difficult_flashcards,
            'mastery_percentage': round((mastered_flashcards / total_user_flashcards * 100) if total_user_flashcards > 0 else 0, 1),
            'cards_due_today': cards_due_today,
            'next_study_session': next_study_session
        }

        # === DAILY AVERAGES ===

        # Średnie wyniki egzaminów dziennie (z filtrowaniem NULL)
        exam_daily_average = (
            db.query(
                func.date(ExamResultModel.started_at).label("date"),
                func.avg(ExamResultModel.score).label("average_score"),
                func.count(ExamResultModel.id).label("count")
            )
            .filter(
                ExamResultModel.user_id == user_id,
                ExamResultModel.score.isnot(None),
                ExamResultModel.started_at.isnot(None)  # Dodane filtrowanie
            )
            .group_by(func.date(ExamResultModel.started_at))
            .all()
        )
        exam_daily_average_serialized = [
            {
                "date": record.date.isoformat() if record.date else None,
                "average_score": round(float(record.average_score), 2) if record.average_score else 0,
                "count": record.count or 0
            }
            for record in exam_daily_average
            if record.date is not None
        ]

        # Średnie oceny fiszek dziennie (z filtrowaniem NULL)
        flashcard_daily_average = (
            db.query(
                func.date(StudyRecordModel.reviewed_at).label("date"),
                func.avg(StudyRecordModel.rating).label("average_rating"),
                func.count(StudyRecordModel.id).label("count")
            )
            .join(StudySessionModel, StudyRecordModel.session_id == StudySessionModel.id)
            .filter(
                StudySessionModel.user_id == user_id,
                StudyRecordModel.rating.isnot(None),
                StudyRecordModel.reviewed_at.isnot(None)  # Dodane filtrowanie
            )
            .group_by(func.date(StudyRecordModel.reviewed_at))
            .all()
        )
        flashcard_daily_average_serialized = [
            {
                "date": record.date.isoformat() if record.date else None,
                "average_rating": round(float(record.average_rating), 2) if record.average_rating else 0,
                "count": record.count or 0
            }
            for record in flashcard_daily_average
            if record.date is not None
        ]

        # === SESSION DURATIONS ===
        session_durations = []
        for session in study_sessions_result:
            try:
                started = getattr(session, 'started_at', None)
                if started:
                    duration = 0.0
                    completed = getattr(session, 'completed_at', None)
                    if completed:
                        duration = (completed - started).total_seconds() / 3600
                        if duration < 0 or duration > 24:  # Sanity check
                            duration = 0.0
                    session_durations.append({
                        "date": started.date().isoformat(),
                        "duration_hours": round(duration, 2),
                        "deck_id": getattr(session, 'deck_id', None)
                    })
            except Exception as e:
                logger.warning(f"Error processing session duration: {e}")
                continue

        # === SERIALIZACJA ===
        def safe_serialize(obj):
            try:
                return serialize(obj)
            except Exception as e:
                logger.warning(f"Error serializing object: {e}")
                return {}

        serialized_study_records = [safe_serialize(record) for record in study_records_result]
        serialized_user_flashcards = [safe_serialize(card) for card in user_flashcards_result]
        serialized_study_sessions = [safe_serialize(session) for session in study_sessions_result]
        serialized_exam_result_answers = [safe_serialize(answer) for answer in exam_result_answers_result]

        serialized_exam_results = []
        for result in exam_results_result:
            try:
                exam_data = safe_serialize(result[0])
                exam_data["exam_name"] = result.exam_name if hasattr(result, 'exam_name') else result[1] if len(result) > 1 else "Unknown"
                serialized_exam_results.append(exam_data)
            except Exception as e:
                logger.warning(f"Error serializing exam result: {e}")
                continue

        # === MATERIAL COUNTS ===
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
            },
            'flashcards': {
                'total': sum(len(d.flashcards) if d.flashcards else 0 for d in all_decks),
                'studied': total_user_flashcards
            }
        }

        # === RESPONSE ===
        response = {
            # ORYGINALNE POLA (kompatybilność wsteczna)
            "study_records": serialized_study_records,
            "user_flashcards": serialized_user_flashcards,
            "study_sessions": serialized_study_sessions,
            "exam_result_answers": serialized_exam_result_answers,
            "exam_results": serialized_exam_results,
            "session_durations": session_durations,
            "exam_daily_average": exam_daily_average_serialized,
            "flashcard_daily_average": flashcard_daily_average_serialized,
            "deck_names": deck_id_to_name,

            # ROZSZERZENIA
            "deck_info": deck_id_to_info,
            "exam_info": exam_id_to_info,
            "exam_names": exam_id_to_name,
            "material_counts": material_counts,

            # NOWE STATYSTYKI CZASOWE
            "time_period_stats": {
                "today": stats_today,
                "this_week": stats_this_week,
                "last_week": stats_last_week,
                "this_month": stats_this_month,
                "last_month": stats_last_month,
                "this_year": stats_this_year
            },

            # PORÓWNANIA
            "comparisons": {
                "week_over_week": week_comparison,
                "month_over_month": month_comparison
            },

            # STUDY STREAK
            "study_streak": study_streak,

            # FLASHCARD MASTERY
            "flashcard_mastery": flashcard_mastery,

            # QUICK STATS (dla szybkiego podglądu)
            "quick_stats": {
                "flashcards_today": stats_today['flashcards_studied'],
                "flashcards_this_week": stats_this_week['flashcards_studied'],
                "flashcards_this_month": stats_this_month['flashcards_studied'],
                "flashcards_this_year": stats_this_year['flashcards_studied'],
                "exams_today": stats_today['exams_completed'],
                "exams_this_week": stats_this_week['exams_completed'],
                "exams_this_month": stats_this_month['exams_completed'],
                "study_hours_today": stats_today['total_study_hours'],
                "study_hours_this_week": stats_this_week['total_study_hours'],
                "study_hours_this_month": stats_this_month['total_study_hours'],
                "cards_due_today": cards_due_today,
                "streak_days": study_streak['current']
            },

            # METADATA
            "generated_at": now.isoformat(),
            "cache_ttl_seconds": 60
        }

        return response

    except SQLAlchemyError as e:
        logger.error(f"Database error in dashboard: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        import traceback
        logger.error(f"Unexpected error in dashboard: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.get("/deck/{deck_id}")
@cache(expire=60)
async def get_deck_statistics_endpoint(
    deck_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Pobiera szczegółowe statystyki dla konkretnego decka.

    Zwraca:
    - Mastery levels (mastered, learning, difficult, not_started)
    - Completion percentage
    - Session history
    - Rating distribution
    - Time stats
    """
    user_id = current_user.id_
    now = datetime.utcnow()

    try:
        # Sprawdź dostęp do decka
        deck = db.query(Deck).options(joinedload(Deck.flashcards)).filter(Deck.id == deck_id).first()

        if not deck:
            raise HTTPException(status_code=404, detail="Deck not found")

        # Sprawdź czy użytkownik ma dostęp (własny lub udostępniony)
        is_owner = deck.user_id == user_id
        has_access = db.query(UserDeckAccess).filter(
            UserDeckAccess.user_id == user_id,
            UserDeckAccess.user_deck_id == deck_id,
            UserDeckAccess.is_active == True
        ).first() is not None

        if not is_owner and not has_access:
            raise HTTPException(status_code=403, detail="Access denied to this deck")

        # Pobierz dane
        user_flashcards = db.query(UserFlashcardModel).filter(
            UserFlashcardModel.user_id == user_id
        ).all()

        study_sessions = db.query(StudySessionModel).filter(
            StudySessionModel.user_id == user_id,
            StudySessionModel.deck_id == deck_id
        ).all()

        study_records = (
            db.query(StudyRecordModel)
            .join(StudySessionModel, StudyRecordModel.session_id == StudySessionModel.id)
            .filter(
                StudySessionModel.user_id == user_id,
                StudySessionModel.deck_id == deck_id
            )
            .all()
        )

        # Podstawowe statystyki
        basic_stats = get_deck_statistics(deck, user_flashcards, study_records, study_sessions, user_id)

        # Rating distribution
        rating_counts = {0: 0, 3: 0, 5: 0}
        for record in study_records:
            if record.rating is not None and record.rating in rating_counts:
                rating_counts[record.rating] += 1

        total_reviews = sum(rating_counts.values())
        rating_distribution = {
            'hard': rating_counts[0],
            'good': rating_counts[3],
            'easy': rating_counts[5],
            'hard_percentage': round((rating_counts[0] / total_reviews * 100) if total_reviews > 0 else 0, 1),
            'good_percentage': round((rating_counts[3] / total_reviews * 100) if total_reviews > 0 else 0, 1),
            'easy_percentage': round((rating_counts[5] / total_reviews * 100) if total_reviews > 0 else 0, 1),
            'total_reviews': total_reviews
        }

        # Session history (ostatnie 10 sesji)
        session_history = []

        # Bezpieczne sortowanie sesji
        def get_session_start(s):
            try:
                started = getattr(s, 'started_at', None)
                return started if started else datetime.min
            except Exception:
                return datetime.min

        sorted_sessions = sorted(study_sessions, key=get_session_start, reverse=True)[:10]

        for session in sorted_sessions:
            try:
                started = getattr(session, 'started_at', None)
                completed = getattr(session, 'completed_at', None)

                duration = 0.0
                if completed and started:
                    duration = (completed - started).total_seconds() / 3600
                    if duration < 0 or duration > 24:
                        duration = 0.0

                session_records = [r for r in study_records if r.session_id == session.id]
                session_history.append({
                    'id': session.id,
                    'started_at': started.isoformat() if started else None,
                    'completed_at': completed.isoformat() if completed else None,
                    'duration_hours': round(duration, 2),
                    'cards_reviewed': len(session_records),
                    'avg_rating': round(sum(r.rating for r in session_records if r.rating is not None) / len(session_records), 2) if session_records else 0
                })
            except Exception as e:
                logger.warning(f"Error processing session history: {e}")
                continue

        # Daily progress (ostatnie 30 dni)
        thirty_days_ago = now - timedelta(days=30)
        daily_progress = (
            db.query(
                func.date(StudyRecordModel.reviewed_at).label("date"),
                func.count(StudyRecordModel.id).label("cards_reviewed"),
                func.avg(StudyRecordModel.rating).label("avg_rating")
            )
            .join(StudySessionModel, StudyRecordModel.session_id == StudySessionModel.id)
            .filter(
                StudySessionModel.user_id == user_id,
                StudySessionModel.deck_id == deck_id,
                StudyRecordModel.reviewed_at >= thirty_days_ago
            )
            .group_by(func.date(StudyRecordModel.reviewed_at))
            .all()
        )

        daily_progress_serialized = [
            {
                "date": record.date.isoformat(),
                "cards_reviewed": record.cards_reviewed,
                "avg_rating": round(float(record.avg_rating), 2) if record.avg_rating else 0
            }
            for record in daily_progress
        ]

        return {
            **basic_stats,
            "rating_distribution": rating_distribution,
            "session_history": session_history,
            "daily_progress": daily_progress_serialized,
            "is_owner": is_owner,
            "generated_at": now.isoformat()
        }

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error in deck statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in deck statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.get("/decks/all")
@cache(expire=60)
async def get_all_decks_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Pobiera przegląd statystyk wszystkich decków użytkownika.
    """
    user_id = current_user.id_
    now = datetime.utcnow()

    try:
        # Własne decki
        own_decks = db.query(Deck).options(joinedload(Deck.flashcards)).filter(
            Deck.user_id == user_id,
            Deck.template_id.is_(None)
        ).all()

        # Udostępnione decki
        shared_access = db.query(UserDeckAccess).filter(
            UserDeckAccess.user_id == user_id,
            UserDeckAccess.is_active == True
        ).all()
        shared_deck_ids = {a.user_deck_id for a in shared_access}

        shared_decks = db.query(Deck).options(joinedload(Deck.flashcards)).filter(
            Deck.id.in_(shared_deck_ids)
        ).all() if shared_deck_ids else []

        all_decks = own_decks + shared_decks

        # Pobierz dane użytkownika
        user_flashcards = db.query(UserFlashcardModel).filter(
            UserFlashcardModel.user_id == user_id
        ).all()

        study_sessions = db.query(StudySessionModel).filter(
            StudySessionModel.user_id == user_id
        ).all()

        study_records = (
            db.query(StudyRecordModel)
            .join(StudySessionModel, StudyRecordModel.session_id == StudySessionModel.id)
            .filter(StudySessionModel.user_id == user_id)
            .all()
        )

        # Oblicz statystyki dla każdego decka
        deck_stats = []
        for deck in all_decks:
            stats = get_deck_statistics(deck, user_flashcards, study_records, study_sessions, user_id)
            stats['is_own'] = deck.id in {d.id for d in own_decks}
            deck_stats.append(stats)

        # Sortuj po cards_due_today (najpilniejsze na górze)
        deck_stats.sort(key=lambda x: (-x['cards_due_today'], -x['completion_percentage']))

        # Summary
        total_cards_due = sum(d['cards_due_today'] for d in deck_stats)
        total_mastered = sum(d['mastered_cards'] for d in deck_stats)
        total_learning = sum(d['learning_cards'] for d in deck_stats)
        total_difficult = sum(d['difficult_cards'] for d in deck_stats)
        total_cards = sum(d['total_cards'] for d in deck_stats)

        return {
            "decks": deck_stats,
            "summary": {
                "total_decks": len(deck_stats),
                "own_decks": len(own_decks),
                "shared_decks": len(shared_decks),
                "total_cards": total_cards,
                "total_cards_due_today": total_cards_due,
                "total_mastered": total_mastered,
                "total_learning": total_learning,
                "total_difficult": total_difficult,
                "overall_mastery_percentage": round((total_mastered / total_cards * 100) if total_cards > 0 else 0, 1)
            },
            "generated_at": now.isoformat()
        }

    except SQLAlchemyError as e:
        logger.error(f"Database error in all decks statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in all decks statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.get("/calendar")
@cache(expire=10)  # Cache na 10 sekund - krótszy czas żeby pokazać aktualne dane
async def get_learning_calendar(
    months_back: int = Query(default=3, ge=1, le=12, description="Months of history to fetch"),
    months_forward: int = Query(default=1, ge=1, le=3, description="Months of scheduled sessions to fetch"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Pobiera dane kalendarza nauki w stylu GitHub contribution graph.

    Returns:
        - history: Dict[date_string, {count, decks}] - przeszłe dni z liczbą fiszek
        - scheduled: Dict[date_string, {count, decks}] - zaplanowane sesje nauki
        - stats: {max_count, total_days_studied, current_streak}
    """
    user_id = current_user.id_
    now = datetime.utcnow()
    today = now.date()

    # Use end of today to ensure all of today's records are included
    end_of_today = datetime.combine(today, datetime.max.time())

    logger.info(f"[Calendar] Fetching calendar for user_id={user_id}, today={today}, now={now}")

    # Oblicz zakres dat
    start_date = today - timedelta(days=months_back * 30)
    end_date = today + timedelta(days=months_forward * 30)

    try:
        # =============================================
        # HISTORIA - ile UNIKALNYCH fiszek przerobiono każdego dnia
        # Używamy logiki z zapytania SQL:
        # SELECT uf.user_id, sr.reviewed_at::date AS review_date,
        #        COUNT(DISTINCT sr.user_flashcard_id) AS individual_flashcards_studied
        # FROM study_records sr
        # JOIN user_flashcards uf ON sr.user_flashcard_id = uf.id
        # GROUP BY uf.user_id, review_date
        # =============================================

        # Pobierz wszystkie study_records dla użytkownika przez JOIN z user_flashcards
        study_records = (
            db.query(
                StudyRecordModel.reviewed_at,
                StudyRecordModel.user_flashcard_id,
                UserFlashcardModel.user_id,
                Flashcard.deck_id,
                Deck.name.label('deck_name')
            )
            .join(UserFlashcardModel, StudyRecordModel.user_flashcard_id == UserFlashcardModel.id)
            .join(Flashcard, UserFlashcardModel.flashcard_id == Flashcard.id)
            .join(Deck, Flashcard.deck_id == Deck.id)
            .filter(
                UserFlashcardModel.user_id == user_id,
                StudyRecordModel.reviewed_at >= start_date,
                StudyRecordModel.reviewed_at <= end_of_today  # Use end of today to include all today's records
            )
            .all()
        )

        logger.info(f"[Calendar] Query returned {len(study_records)} study_records for user {user_id}")

        # Agreguj po dniach - licząc UNIKALNE fiszki (user_flashcard_id) per dzień per deck
        history_data: Dict[str, Dict[str, Any]] = {}
        # Struktura pomocnicza: day_str -> deck_name -> set of user_flashcard_ids
        day_deck_flashcards: Dict[str, Dict[str, set]] = {}

        for record in study_records:
            if record.reviewed_at and record.user_flashcard_id:
                day_str = record.reviewed_at.date().isoformat()
                deck_name = record.deck_name or f"Deck {record.deck_id}"

                if day_str not in day_deck_flashcards:
                    day_deck_flashcards[day_str] = {}

                if deck_name not in day_deck_flashcards[day_str]:
                    day_deck_flashcards[day_str][deck_name] = set()

                day_deck_flashcards[day_str][deck_name].add(record.user_flashcard_id)

        # Konwertuj na history_data z liczbami
        for day_str, decks_data in day_deck_flashcards.items():
            total_unique = sum(len(flashcard_ids) for flashcard_ids in decks_data.values())
            history_data[day_str] = {
                'count': total_unique,
                'decks': [
                    {'name': deck_name, 'count': len(flashcard_ids)}
                    for deck_name, flashcard_ids in decks_data.items()
                ]
            }

        logger.info(f"[Calendar] Found {len(study_records)} study records, {len(history_data)} unique study days")
        if today.isoformat() in history_data:
            logger.info(f"[Calendar] Today ({today.isoformat()}) has {history_data[today.isoformat()]['count']} unique flashcards")

        # =============================================
        # ZAPLANOWANE SESJE - na podstawie next_review
        # =============================================

        # Use start of today to include cards due today
        today_start = datetime.combine(today, datetime.min.time())

        scheduled_cards = (
            db.query(
                UserFlashcardModel.next_review,
                Deck.id.label('deck_id'),
                Deck.name.label('deck_name')
            )
            .join(Flashcard, UserFlashcardModel.flashcard_id == Flashcard.id)
            .join(Deck, Flashcard.deck_id == Deck.id)
            .filter(
                UserFlashcardModel.user_id == user_id,
                UserFlashcardModel.next_review >= today_start,  # Include today's cards
                UserFlashcardModel.next_review <= end_date
            )
            .all()
        )

        # Agreguj po dniach
        scheduled_data: Dict[str, Dict[str, Any]] = {}

        for card in scheduled_cards:
            if card.next_review:
                day_str = card.next_review.date().isoformat()

                if day_str not in scheduled_data:
                    scheduled_data[day_str] = {
                        'count': 0,
                        'decks': {}
                    }

                scheduled_data[day_str]['count'] += 1

                deck_name = card.deck_name or f"Deck {card.deck_id}"
                if deck_name not in scheduled_data[day_str]['decks']:
                    scheduled_data[day_str]['decks'][deck_name] = 0
                scheduled_data[day_str]['decks'][deck_name] += 1

        # Konwertuj decks dict na listę dla JSON
        for day_str in scheduled_data:
            scheduled_data[day_str]['decks'] = [
                {'name': name, 'count': count}
                for name, count in scheduled_data[day_str]['decks'].items()
            ]

        # =============================================
        # STATYSTYKI ROCZNE I DZIENNE
        # Liczymy UNIKALNE fiszki per dzień w roku i sumujemy.
        # Używamy tego samego wzorca JOIN co w historii kalendarza.
        # =============================================

        year_start = datetime(today.year, 1, 1)

        # Pobierz wszystkie study records z tego roku przez JOIN z user_flashcards
        year_study_records = (
            db.query(
                StudyRecordModel.reviewed_at,
                StudyRecordModel.user_flashcard_id,
            )
            .join(UserFlashcardModel, StudyRecordModel.user_flashcard_id == UserFlashcardModel.id)
            .filter(
                UserFlashcardModel.user_id == user_id,
                StudyRecordModel.reviewed_at >= year_start,
                StudyRecordModel.reviewed_at <= end_of_today  # Use end of today to include all today's records
            )
            .all()
        )

        logger.info(f"[Calendar] Year query returned {len(year_study_records)} study_records for user {user_id} from {year_start} to {end_of_today}")

        # Zlicz unikalne fiszki per dzień i zsumuj
        year_day_flashcards: Dict[str, set] = {}
        for record in year_study_records:
            if record.reviewed_at and record.user_flashcard_id:
                day_str = record.reviewed_at.date().isoformat()
                if day_str not in year_day_flashcards:
                    year_day_flashcards[day_str] = set()
                year_day_flashcards[day_str].add(record.user_flashcard_id)

        # Suma unikalnych fiszek per dzień
        total_flashcards_year = sum(len(flashcard_ids) for flashcard_ids in year_day_flashcards.values())

        logger.info(f"[Calendar] Year stats: {len(year_study_records)} records, {len(year_day_flashcards)} days, {total_flashcards_year} unique flashcards this year")

        # Sprawdź czy użytkownik uczył się dzisiaj (fiszki lub egzaminy)
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())

        has_studied_today = False

        # Sprawdź fiszki
        if today.isoformat() in history_data:
            has_studied_today = True
        else:
            # Sprawdź egzaminy (jeśli nie ma w history_data, bo history_data jest z study_records)
            # Warto sprawdzić czy exam results są uwzględniane w kalendarzu?
            # Obecna implementacja kalendarza patrzy tylko na StudyRecordModel (fiszki).
            # Dodajmy sprawdzenie egzaminów dla flagi has_studied_today
            exams_today = db.query(ExamResultModel).filter(
                ExamResultModel.user_id == user_id,
                ExamResultModel.started_at >= today_start,
                ExamResultModel.started_at <= today_end
            ).first()
            if exams_today:
                has_studied_today = True

        # =============================================
        # STATYSTYKI
        # =============================================

        max_count = max([d['count'] for d in history_data.values()]) if history_data else 0
        total_days_studied = len(history_data)

        study_sessions = db.query(StudySessionModel).filter(
            StudySessionModel.user_id == user_id
        ).all()
        exam_results = db.query(ExamResultModel).filter(
            ExamResultModel.user_id == user_id
        ).all()
        streak_data = calculate_study_streak(study_sessions, [(e,) for e in exam_results])

        cards_due_today = db.query(UserFlashcardModel).filter(
            UserFlashcardModel.user_id == user_id,
            UserFlashcardModel.next_review <= end_of_today  # Use end of today
        ).count()

        # Get decks scheduled for today
        today_str = today.isoformat()
        decks_due_today = []
        if today_str in scheduled_data:
            decks_due_today = scheduled_data[today_str].get('decks', [])

        logger.info(f"[Calendar] Final stats: total_flashcards_year={total_flashcards_year}, cards_due_today={cards_due_today}, has_studied_today={has_studied_today}")

        overdue_cards_per_deck = db.query(
            Deck.name.label('deck_name'),
            func.count(UserFlashcardModel.id).label('count')
        ).join(
            Flashcard, UserFlashcardModel.flashcard_id == Flashcard.id
        ).join(
            Deck, Flashcard.deck_id == Deck.id
        ).filter(
            UserFlashcardModel.user_id == user_id,
            UserFlashcardModel.next_review < today  # Strictly less than today = overdue
        ).group_by(
            Deck.name
        ).all()

        total_overdue_count = 0
        decks_list = []

        for deck_name, count in overdue_cards_per_deck:
            total_overdue_count += count
            decks_list.append({
                "name": deck_name,
                "count": count
            })

        # 4. Construct the final dictionary
        overdue_data = {
            today_str: {
                "count": total_overdue_count,
                "decks": decks_list
            }
        }

        return {
            "history": history_data,
            "scheduled": scheduled_data,
            "overdue": overdue_data,
            "stats": {
                "max_count": max_count,
                "total_days_studied": total_days_studied,
                "current_streak": streak_data['current'],
                "longest_streak": streak_data['longest'],
                "is_active_today": streak_data['is_active_today'],
                "cards_due_today": cards_due_today,
                "total_flashcards_year": total_flashcards_year,
                "has_studied_today": has_studied_today,
                "decks_due_today": decks_due_today
            },
            "range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "generated_at": now.isoformat()
        }

    except SQLAlchemyError as e:
        logger.error(f"Database error in calendar: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in calendar: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.get("/goals")
@cache(expire=60)
async def get_goals_and_achievements(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Pobiera cele, osiągnięcia i sugestie dla użytkownika.
    """
    user_id = current_user.id_
    now = datetime.utcnow()
    today = now.date()

    try:
        # Pobierz podstawowe dane
        study_sessions = db.query(StudySessionModel).filter(
            StudySessionModel.user_id == user_id
        ).all()

        exam_results_query = (
            db.query(ExamResultModel)
            .filter(ExamResultModel.user_id == user_id)
        )
        exam_results = exam_results_query.all()

        user_flashcards = db.query(UserFlashcardModel).filter(
            UserFlashcardModel.user_id == user_id
        ).all()

        study_records = (
            db.query(StudyRecordModel)
            .join(StudySessionModel, StudyRecordModel.session_id == StudySessionModel.id)
            .filter(StudySessionModel.user_id == user_id)
            .all()
        )

        # Streak info
        streak_data = calculate_study_streak(study_sessions, [(e,) for e in exam_results])

        # Achievements (odznaki)
        achievements = []

        # Streak achievements
        if streak_data['current'] >= 7:
            achievements.append({
                'id': 'streak_week',
                'name': 'Week Warrior',
                'description': '7 day study streak',
                'icon': 'fire',
                'earned': True,
                'earned_at': today.isoformat()
            })
        if streak_data['current'] >= 30:
            achievements.append({
                'id': 'streak_month',
                'name': 'Monthly Master',
                'description': '30 day study streak',
                'icon': 'trophy',
                'earned': True,
                'earned_at': today.isoformat()
            })
        if streak_data['longest'] >= 100:
            achievements.append({
                'id': 'streak_100',
                'name': 'Century Club',
                'description': '100 day study streak (all time)',
                'icon': 'star',
                'earned': True,
                'earned_at': None
            })

        # Flashcard achievements
        total_reviews = len(study_records)
        if total_reviews >= 100:
            achievements.append({
                'id': 'reviews_100',
                'name': 'Getting Started',
                'description': '100 flashcard reviews',
                'icon': 'book',
                'earned': True
            })
        if total_reviews >= 1000:
            achievements.append({
                'id': 'reviews_1000',
                'name': 'Dedicated Learner',
                'description': '1000 flashcard reviews',
                'icon': 'book_open',
                'earned': True
            })
        if total_reviews >= 10000:
            achievements.append({
                'id': 'reviews_10000',
                'name': 'Flashcard Master',
                'description': '10000 flashcard reviews',
                'icon': 'crown',
                'earned': True
            })

        # Mastery achievements
        mastered_count = len([uf for uf in user_flashcards if uf.ef > 2.5])
        if mastered_count >= 50:
            achievements.append({
                'id': 'mastered_50',
                'name': 'Quick Learner',
                'description': '50 cards mastered',
                'icon': 'brain',
                'earned': True
            })
        if mastered_count >= 500:
            achievements.append({
                'id': 'mastered_500',
                'name': 'Knowledge Keeper',
                'description': '500 cards mastered',
                'icon': 'graduation_cap',
                'earned': True
            })

        # Exam achievements
        total_exams = len(exam_results)
        if total_exams >= 10:
            achievements.append({
                'id': 'exams_10',
                'name': 'Test Taker',
                'description': '10 exams completed',
                'icon': 'clipboard_check',
                'earned': True
            })

        perfect_exams = len([e for e in exam_results if e.score and e.score >= 100])
        if perfect_exams >= 1:
            achievements.append({
                'id': 'perfect_exam',
                'name': 'Perfectionist',
                'description': 'Perfect score on an exam',
                'icon': 'check_circle',
                'earned': True
            })

        # Suggestions (co użytkownik powinien zrobić)
        suggestions = []

        cards_due = len([uf for uf in user_flashcards if uf.next_review and uf.next_review <= now])
        if cards_due > 0:
            suggestions.append({
                'type': 'review_due',
                'priority': 'high',
                'title': f'{cards_due} cards due for review',
                'description': 'Keep your memory fresh by reviewing these cards',
                'action': 'flashcards'
            })

        if not streak_data['is_active_today']:
            suggestions.append({
                'type': 'keep_streak',
                'priority': 'high',
                'title': 'Keep your streak alive!',
                'description': f"You have a {streak_data['current']} day streak. Study today to continue!",
                'action': 'flashcards'
            })

        difficult_cards = len([uf for uf in user_flashcards if uf.ef <= 1.8])
        if difficult_cards > 10:
            suggestions.append({
                'type': 'difficult_cards',
                'priority': 'medium',
                'title': f'{difficult_cards} difficult cards need attention',
                'description': 'Focus on these cards to improve your mastery',
                'action': 'flashcards'
            })

        # Milestones (najbliższe cele)
        milestones = []

        # Next streak milestone
        for milestone in [7, 14, 30, 60, 100, 365]:
            if streak_data['current'] < milestone:
                days_left = milestone - streak_data['current']
                milestones.append({
                    'type': 'streak',
                    'target': milestone,
                    'current': streak_data['current'],
                    'days_left': days_left,
                    'description': f'{milestone} day streak'
                })
                break

        # Next review milestone
        for milestone in [100, 500, 1000, 5000, 10000]:
            if total_reviews < milestone:
                reviews_left = milestone - total_reviews
                milestones.append({
                    'type': 'reviews',
                    'target': milestone,
                    'current': total_reviews,
                    'remaining': reviews_left,
                    'description': f'{milestone} flashcard reviews'
                })
                break

        # Next mastery milestone
        for milestone in [50, 100, 250, 500, 1000]:
            if mastered_count < milestone:
                cards_left = milestone - mastered_count
                milestones.append({
                    'type': 'mastery',
                    'target': milestone,
                    'current': mastered_count,
                    'remaining': cards_left,
                    'description': f'{milestone} cards mastered'
                })
                break

        return {
            "streak": streak_data,
            "achievements": achievements,
            "suggestions": suggestions,
            "milestones": milestones,
            "stats": {
                "total_reviews": total_reviews,
                "mastered_cards": mastered_count,
                "total_exams": total_exams,
                "perfect_exams": perfect_exams,
                "cards_due_today": cards_due
            },
            "generated_at": now.isoformat()
        }

    except SQLAlchemyError as e:
        logger.error(f"Database error in goals: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in goals: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.post("/invalidate-cache")
async def invalidate_dashboard_cache(
    current_user: User = Depends(get_current_user),
):
    """
    Invaliduje cache dashboardu dla użytkownika.
    Wywołuj po zakończeniu sesji nauki lub egzaminu.
    """
    success = await invalidate_user_dashboard_cache(current_user.id_)
    return {
        "message": "Cache invalidated" if success else "Cache invalidation attempted",
        "success": success,
        "user_id": current_user.id_,
        "timestamp": datetime.utcnow().isoformat()
    }

