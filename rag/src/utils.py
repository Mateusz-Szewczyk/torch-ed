import secrets
import string
import datetime
import logging
from contextlib import contextmanager

from psycopg2.errors import UniqueViolation
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import func

from .dependencies import get_db
from .models import (
    ShareableContent, Deck, Flashcard, Exam, ExamQuestion, ExamAnswer,
    UserDeckAccess, UserExamAccess, User
)

logger = logging.getLogger(__name__)


@contextmanager
def get_db_session(provided_session: Session = None):
    """Context manager dla bezpiecznego zarządzania sesjami"""
    if provided_session:
        yield provided_session
    else:
        # Prawidłowe pobieranie sesji z generatora
        db_gen = get_db()
        session = next(db_gen)
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            try:
                next(db_gen)  # Cleanup generatora
            except StopIteration:
                pass


def generate_share_code() -> str:
    """Generuje unikalny 12-znakowy kod udostępniania"""
    characters = string.ascii_uppercase + string.digits
    # POPRAWKA: dodano brakującą spację w replace()
    characters = characters.replace('0', '').replace('O', '').replace('I', '').replace('1', '')

    max_attempts = 10

    for attempt in range(max_attempts):
        code = ''.join(secrets.choice(characters) for _ in range(12))

        # Sprawdź unikalność w bazie
        with get_db_session() as session:
            existing = session.query(ShareableContent).filter_by(share_code=code).first()
            if not existing:
                return code

    raise Exception("Failed to generate unique share code after maximum attempts")


# ===========================================
# FUNKCJE DLA DECK'ÓW
# ===========================================

def create_shareable_deck(deck_id: int, creator_id: int, db_session: Session = None) -> str:
    """Tworzy udostępnialny deck i zwraca kod (lub reaktywuje istniejący)"""

    # Używaj przekazanej sesji zamiast context managera
    db = db_session if db_session else next(get_db())

    try:
        logger.info(f"Creating/reactivating shareable deck for deck_id={deck_id}, creator_id={creator_id}")

        # Sprawdź czy deck istnieje i należy do użytkownika
        original_deck = db.query(Deck).filter(
            Deck.id == deck_id,
            Deck.user_id == creator_id
        ).first()

        if not original_deck:
            logger.error(f"Deck {deck_id} not found or access denied for user {creator_id}")
            raise Exception("Deck not found or access denied")

        # SPRAWDŹ CZY ISTNIEJE JAKIKOLWIEK KOD (aktywny lub nieaktywny)
        existing_share = db.query(ShareableContent).filter(
            ShareableContent.content_type == 'deck',
            ShareableContent.content_id == deck_id,
            ShareableContent.creator_id == creator_id  # Dodaj sprawdzenie creator_id dla bezpieczeństwa
        ).first()  # Usuń filtr is_public!

        if existing_share:
            if existing_share.is_public:
                # Kod już aktywny - zwróć istniejący
                logger.info(f"Deck {deck_id} already has active share code: {existing_share.share_code}")
                return existing_share.share_code
            else:
                # REAKTYWUJ NIEAKTYWNY KOD
                logger.info(f"Reactivating existing share code for deck {deck_id}")

                # Wygeneruj nowy kod (dla bezpieczeństwa)
                new_share_code = generate_share_code()

                # Zaktualizuj istniejący wpis
                existing_share.share_code = new_share_code
                existing_share.is_public = True
                existing_share.created_at = func.now()  # Zaktualizuj datę
                existing_share.access_count = 0  # Resetuj licznik (opcjonalnie)

                # Oznacz oryginalny deck jako szablon
                original_deck.is_template = True

                # Commituj jeśli używamy dependency
                if db_session:
                    db.commit()

                logger.info(f"Reactivated share code {new_share_code} for deck {deck_id}")
                return new_share_code

        # UTWÓRZ NOWY KOD (pierwsza udostępnianie tego deck'a)
        logger.info(f"Creating new share code for deck {deck_id}")

        # Wygeneruj unikalny kod
        share_code = generate_share_code()
        logger.info(f"Generated new share code: {share_code}")

        # Utwórz nowy kod udostępniania
        shareable = ShareableContent(
            share_code=share_code,
            content_type='deck',
            content_id=deck_id,
            creator_id=creator_id,
            is_public=True,
            access_count=0
        )

        # Oznacz oryginalny deck jako szablon
        original_deck.is_template = True

        # Dodaj do sesji
        db.add(shareable)

        # Commituj jeśli używamy dependency
        if db_session:
            db.commit()
            logger.info(f"New share code {share_code} created and committed successfully")

        return share_code

    except (IntegrityError, UniqueViolation) as e:
        logger.error(f"Database constraint error: {e}")
        if db_session:
            db.rollback()
        raise Exception("Failed to create share code - database constraint error")
    except Exception as e:
        logger.error(f"Error creating shareable deck: {e}")
        if db_session:
            db.rollback()
        raise


def add_deck_by_code(user_id: int, share_code: str, db_session: Session) -> dict:
    """Dodaje deck do biblioteki użytkownika na podstawie kodu"""

    try:
        logger.info(f"Adding deck by code: {share_code} for user {user_id}")

        # Znajdź shareable content
        shareable = db_session.query(ShareableContent).filter(
            ShareableContent.share_code == share_code,
            ShareableContent.content_type == 'deck',
            ShareableContent.is_public == True
        ).first()

        if not shareable:
            logger.warning(f"Share code {share_code} not found or inactive")
            return {'success': False, 'message': 'Invalid or expired share code'}

        original_deck_id = shareable.content_id

        # Sprawdź czy użytkownik nie próbuje dodać własny deck
        original_deck = db_session.query(Deck).filter(Deck.id == original_deck_id).first()
        if not original_deck:
            logger.error(f"Original deck {original_deck_id} not found")
            return {'success': False, 'message': 'Deck not found'}

        if original_deck.user_id == user_id:
            logger.warning(f"User {user_id} tried to add own deck {original_deck_id}")
            return {'success': False, 'message': 'Cannot add your own deck'}

        # SPRAWDŹ CZY ISTNIEJE JAKIKOLWIEK DOSTĘP (aktywny lub nieaktywny)
        existing_access = db_session.query(UserDeckAccess).filter(
            UserDeckAccess.user_id == user_id,
            UserDeckAccess.original_deck_id == original_deck_id
        ).first()  # Bez filtra is_active!

        if existing_access:
            if existing_access.is_active:
                logger.info(f"User {user_id} already has active access to deck {original_deck_id}")
                return {'success': False, 'message': 'You already have this deck in your library'}
            else:
                # REAKTYWUJ ISTNIEJĄCY DOSTĘP
                logger.info(f"Reactivating existing access for user {user_id} to deck {original_deck_id}")

                # Sprawdź czy kopia deck'a nadal istnieje
                user_deck = db_session.query(Deck).filter(Deck.id == existing_access.user_deck_id).first()

                if user_deck:
                    # Kopia istnieje - tylko reaktywuj dostęp
                    existing_access.is_active = True
                    existing_access.accessed_via_code = share_code  # Zaktualizuj kod
                    existing_access.added_at = func.now()  # Zaktualizuj datę

                    logger.info(f"Reactivated access to existing deck copy {user_deck.id}")
                    deck_id = user_deck.id
                    deck_name = user_deck.name
                else:
                    # Kopia nie istnieje - utwórz nową i zaktualizuj dostęp
                    logger.info(f"Creating new deck copy for reactivated access")

                    # Utwórz nową kopię deck'a
                    new_user_deck = Deck(
                        name=original_deck.name,
                        description=original_deck.description,
                        user_id=user_id,
                        is_template=False,
                        template_id=original_deck_id
                    )

                    db_session.add(new_user_deck)
                    db_session.flush()  # Aby uzyskać ID

                    # Skopiuj flashcards
                    original_flashcards = db_session.query(Flashcard).filter(
                        Flashcard.deck_id == original_deck_id
                    ).all()

                    for original_card in original_flashcards:
                        user_card = Flashcard(
                            question=original_card.question,
                            answer=original_card.answer,
                            deck_id=new_user_deck.id,
                            media_url=original_card.media_url
                        )
                        db_session.add(user_card)

                    # Zaktualizuj dostęp
                    existing_access.user_deck_id = new_user_deck.id
                    existing_access.is_active = True
                    existing_access.accessed_via_code = share_code
                    existing_access.added_at = func.now()

                    logger.info(f"Created new deck copy {new_user_deck.id} and updated access")
                    deck_id = new_user_deck.id
                    deck_name = new_user_deck.name
        else:
            # UTWÓRZ NOWY DOSTĘP (pierwszy raz)
            logger.info(f"Creating new access for user {user_id} to deck {original_deck_id}")

            # Utwórz kopię deck'a dla użytkownika
            user_deck = Deck(
                name=original_deck.name,
                description=original_deck.description,
                user_id=user_id,
                is_template=False,
                template_id=original_deck_id
            )

            db_session.add(user_deck)
            db_session.flush()  # Aby uzyskać ID przed commit

            # Skopiuj flashcards
            original_flashcards = db_session.query(Flashcard).filter(
                Flashcard.deck_id == original_deck_id
            ).all()

            for original_card in original_flashcards:
                user_card = Flashcard(
                    question=original_card.question,
                    answer=original_card.answer,
                    deck_id=user_deck.id,
                    media_url=original_card.media_url
                )
                db_session.add(user_card)

            # Utwórz wpis w UserDeckAccess
            deck_access = UserDeckAccess(
                user_id=user_id,
                original_deck_id=original_deck_id,
                user_deck_id=user_deck.id,
                accessed_via_code=share_code,
                is_active=True
            )

            db_session.add(deck_access)

            logger.info(f"Created new deck copy {user_deck.id} and access record")
            deck_id = user_deck.id
            deck_name = user_deck.name

        # Zwiększ licznik dostępów
        shareable.access_count += 1

        # Commituj wszystkie zmiany
        db_session.commit()

        logger.info(f"Successfully added/reactivated deck {original_deck_id} for user {user_id}")

        return {
            'success': True,
            'message': f'Deck "{deck_name}" added to your library successfully',
            'deck_id': deck_id,
            'deck_name': deck_name
        }

    except (IntegrityError, UniqueViolation) as e:
        logger.error(f"Database constraint error: {e}")
        db_session.rollback()
        return {'success': False, 'message': 'Database error - deck may already be in your library'}
    except Exception as e:
        logger.error(f"Error adding deck by code: {e}")
        db_session.rollback()
        return {'success': False, 'message': 'Failed to add deck to your library'}


def copy_deck_for_user(original_deck_id: int, user_id: int, db_session: Session = None) -> int:
    """Tworzy kopię deck'a dla użytkownika"""
    with get_db_session(db_session) as session:
        try:
            original_deck = session.query(Deck).filter_by(id=original_deck_id).first()
            if not original_deck:
                raise Exception("Original deck not found")

            # Utwórz kopię deck'a
            user_deck = Deck(
                user_id=user_id,
                name=f"{original_deck.name} (shared)",
                description=original_deck.description,
                template_id=original_deck.id,
                is_template=False
            )
            session.add(user_deck)
            session.flush()  # Aby otrzymać ID

            # Skopiuj flashcards
            original_flashcards = session.query(Flashcard).filter_by(deck_id=original_deck.id).all()
            for original_card in original_flashcards:
                user_card = Flashcard(
                    question=original_card.question,
                    answer=original_card.answer,
                    deck_id=user_deck.id,
                    media_url=original_card.media_url
                )
                session.add(user_card)

            if not db_session:
                session.commit()

            return user_deck.id

        except Exception as e:
            logger.error(f"Error copying deck for user: {e}")
            raise


def get_user_shared_decks(user_id: int, db_session: Session = None) -> list:
    """Pobiera listę udostępnionych deck'ów użytkownika"""
    with get_db_session(db_session) as session:
        try:
            shared_decks = session.query(UserDeckAccess).filter_by(
                user_id=user_id,
                is_active=True
            ).all()

            result = []
            for access in shared_decks:
                original_deck = session.query(Deck).filter_by(id=access.original_deck_id).first()
                user_deck = session.query(Deck).filter_by(id=access.user_deck_id).first()

                if original_deck and user_deck:
                    flashcard_count = session.query(Flashcard).filter_by(deck_id=user_deck.id).count()
                    result.append({
                        'user_deck_id': access.user_deck_id,
                        'original_deck_id': access.original_deck_id,
                        'deck_name': user_deck.name,
                        'original_deck_name': original_deck.name,
                        'flashcard_count': flashcard_count,
                        'added_at': access.added_at.isoformat(),
                        'code_used': access.accessed_via_code
                    })

            return result

        except Exception as e:
            logger.error(f"Error getting user shared decks: {e}")
            return []


# ===========================================
# FUNKCJE DLA EGZAMINÓW - POPRAWIONE
# ===========================================

def create_shareable_exam(exam_id: int, creator_id: int, db_session: Session = None) -> str:
    """Tworzy udostępnialny egzamin i zwraca kod (lub reaktywuje istniejący)"""

    # Używaj przekazanej sesji zamiast context managera
    db = db_session if db_session else next(get_db())

    try:
        logger.info(f"Creating/reactivating shareable exam for exam_id={exam_id}, creator_id={creator_id}")

        # Sprawdź czy egzamin istnieje i należy do użytkownika
        original_exam = db.query(Exam).filter(
            Exam.id == exam_id,
            Exam.user_id == creator_id
        ).first()

        if not original_exam:
            logger.error(f"Exam {exam_id} not found or access denied for user {creator_id}")
            raise Exception("Exam not found or access denied")

        # SPRAWDŹ CZY ISTNIEJE JAKIKOLWIEK KOD (aktywny lub nieaktywny)
        existing_share = db.query(ShareableContent).filter(
            ShareableContent.content_type == 'exam',
            ShareableContent.content_id == exam_id,
            ShareableContent.creator_id == creator_id
        ).first()  # Usuń filtr is_public!

        if existing_share:
            if existing_share.is_public:
                # Kod już aktywny - zwróć istniejący
                logger.info(f"Exam {exam_id} already has active share code: {existing_share.share_code}")
                return existing_share.share_code
            else:
                # REAKTYWUJ NIEAKTYWNY KOD
                logger.info(f"Reactivating existing share code for exam {exam_id}")

                # Wygeneruj nowy kod (dla bezpieczeństwa)
                new_share_code = generate_share_code()

                # Zaktualizuj istniejący wpis
                existing_share.share_code = new_share_code
                existing_share.is_public = True
                existing_share.created_at = func.now()
                existing_share.access_count = 0  # Resetuj licznik

                # Oznacz oryginalny egzamin jako szablon
                original_exam.is_template = True

                # Commituj jeśli używamy dependency
                if db_session:
                    db.commit()

                logger.info(f"Reactivated share code {new_share_code} for exam {exam_id}")
                return new_share_code

        # UTWÓRZ NOWY KOD (pierwsza udostępnianie tego egzaminu)
        logger.info(f"Creating new share code for exam {exam_id}")

        # Wygeneruj unikalny kod
        share_code = generate_share_code()
        logger.info(f"Generated new share code: {share_code}")

        # Utwórz nowy kod udostępniania
        shareable = ShareableContent(
            share_code=share_code,
            content_type='exam',
            content_id=exam_id,
            creator_id=creator_id,
            is_public=True,
            access_count=0
        )

        # Oznacz oryginalny egzamin jako szablon
        original_exam.is_template = True

        # Dodaj do sesji
        db.add(shareable)

        # Commituj jeśli używamy dependency
        if db_session:
            db.commit()
            logger.info(f"New share code {share_code} created and committed successfully")

        return share_code

    except (IntegrityError, UniqueViolation) as e:
        logger.error(f"Database constraint error: {e}")
        if db_session:
            db.rollback()
        raise Exception("Failed to create share code - database constraint error")
    except Exception as e:
        logger.error(f"Error creating shareable exam: {e}")
        if db_session:
            db.rollback()
        raise


def add_exam_by_code(user_id: int, share_code: str, db_session: Session) -> dict:
    """Dodaje egzamin do biblioteki użytkownika na podstawie kodu"""

    try:
        logger.info(f"Adding exam by code: {share_code} for user {user_id}")

        # Znajdź shareable content
        shareable = db_session.query(ShareableContent).filter(
            ShareableContent.share_code == share_code,
            ShareableContent.content_type == 'exam',
            ShareableContent.is_public == True
        ).first()

        if not shareable:
            logger.warning(f"Share code {share_code} not found or inactive")
            return {'success': False, 'message': 'Invalid or expired share code'}

        original_exam_id = shareable.content_id

        # Sprawdź czy użytkownik nie próbuje dodać własny egzamin
        original_exam = db_session.query(Exam).filter(Exam.id == original_exam_id).first()
        if not original_exam:
            logger.error(f"Original exam {original_exam_id} not found")
            return {'success': False, 'message': 'Exam not found'}

        if original_exam.user_id == user_id:
            logger.warning(f"User {user_id} tried to add own exam {original_exam_id}")
            return {'success': False, 'message': 'Cannot add your own exam'}

        # SPRAWDŹ CZY ISTNIEJE JAKIKOLWIEK DOSTĘP (aktywny lub nieaktywny)
        existing_access = db_session.query(UserExamAccess).filter(
            UserExamAccess.user_id == user_id,
            UserExamAccess.original_exam_id == original_exam_id
        ).first()  # Bez filtra is_active!

        if existing_access:
            if existing_access.is_active:
                logger.info(f"User {user_id} already has active access to exam {original_exam_id}")
                return {'success': False, 'message': 'You already have this exam in your library'}
            else:
                # REAKTYWUJ ISTNIEJĄCY DOSTĘP
                logger.info(f"Reactivating existing access for user {user_id} to exam {original_exam_id}")

                # Sprawdź czy kopia egzaminu nadal istnieje
                user_exam = db_session.query(Exam).filter(Exam.id == existing_access.user_exam_id).first()

                if user_exam:
                    # Kopia istnieje - tylko reaktywuj dostęp
                    existing_access.is_active = True
                    existing_access.accessed_via_code = share_code
                    existing_access.added_at = func.now()

                    logger.info(f"Reactivated access to existing exam copy {user_exam.id}")
                    exam_id = user_exam.id
                    exam_name = user_exam.name
                else:
                    # Kopia nie istnieje - utwórz nową i zaktualizuj dostęp
                    logger.info(f"Creating new exam copy for reactivated access")

                    # Utwórz nową kopię egzaminu
                    new_user_exam = Exam(
                        name=original_exam.name,
                        description=original_exam.description,
                        user_id=user_id,
                        is_template=False,
                        template_id=original_exam_id
                    )

                    db_session.add(new_user_exam)
                    db_session.flush()  # Aby uzyskać ID

                    # Skopiuj pytania i odpowiedzi
                    original_questions = db_session.query(ExamQuestion).filter(
                        ExamQuestion.exam_id == original_exam_id
                    ).all()

                    for original_question in original_questions:
                        user_question = ExamQuestion(
                            text=original_question.text,
                            exam_id=new_user_exam.id
                        )
                        db_session.add(user_question)
                        db_session.flush()

                        # Skopiuj odpowiedzi
                        original_answers = db_session.query(ExamAnswer).filter(
                            ExamAnswer.question_id == original_question.id
                        ).all()

                        for original_answer in original_answers:
                            user_answer = ExamAnswer(
                                text=original_answer.text,
                                is_correct=original_answer.is_correct,
                                question_id=user_question.id
                            )
                            db_session.add(user_answer)

                    # Zaktualizuj dostęp
                    existing_access.user_exam_id = new_user_exam.id
                    existing_access.is_active = True
                    existing_access.accessed_via_code = share_code
                    existing_access.added_at = func.now()

                    logger.info(f"Created new exam copy {new_user_exam.id} and updated access")
                    exam_id = new_user_exam.id
                    exam_name = new_user_exam.name
        else:
            # UTWÓRZ NOWY DOSTĘP (pierwszy raz)
            logger.info(f"Creating new access for user {user_id} to exam {original_exam_id}")

            # Utwórz kopię egzaminu dla użytkownika
            user_exam = Exam(
                name=original_exam.name,
                description=original_exam.description,
                user_id=user_id,
                is_template=False,
                template_id=original_exam_id
            )

            db_session.add(user_exam)
            db_session.flush()  # Aby uzyskać ID przed commit

            # Skopiuj pytania i odpowiedzi
            original_questions = db_session.query(ExamQuestion).filter(
                ExamQuestion.exam_id == original_exam_id
            ).all()

            for original_question in original_questions:
                user_question = ExamQuestion(
                    text=original_question.text,
                    exam_id=user_exam.id
                )
                db_session.add(user_question)
                db_session.flush()

                # Skopiuj odpowiedzi
                original_answers = db_session.query(ExamAnswer).filter(
                    ExamAnswer.question_id == original_question.id
                ).all()

                for original_answer in original_answers:
                    user_answer = ExamAnswer(
                        text=original_answer.text,
                        is_correct=original_answer.is_correct,
                        question_id=user_question.id
                    )
                    db_session.add(user_answer)

            # Utwórz wpis w UserExamAccess
            exam_access = UserExamAccess(
                user_id=user_id,
                original_exam_id=original_exam_id,
                user_exam_id=user_exam.id,
                accessed_via_code=share_code,
                is_active=True
            )

            db_session.add(exam_access)

            logger.info(f"Created new exam copy {user_exam.id} and access record")
            exam_id = user_exam.id
            exam_name = user_exam.name

        # Zwiększ licznik dostępów
        shareable.access_count += 1

        # Commituj wszystkie zmiany
        db_session.commit()

        logger.info(f"Successfully added/reactivated exam {original_exam_id} for user {user_id}")

        return {
            'success': True,
            'message': f'Exam "{exam_name}" added to your library successfully',
            'exam_id': exam_id,
            'exam_name': exam_name
        }

    except (IntegrityError, UniqueViolation) as e:
        logger.error(f"Database constraint error: {e}")
        db_session.rollback()
        return {'success': False, 'message': 'Database error - exam may already be in your library'}
    except Exception as e:
        logger.error(f"Error adding exam by code: {e}")
        db_session.rollback()
        return {'success': False, 'message': 'Failed to add exam to your library'}


def copy_exam_for_user(original_exam_id: int, user_id: int, db_session: Session = None) -> int:
    """Tworzy kopię egzaminu dla użytkownika"""
    with get_db_session(db_session) as session:
        try:
            original_exam = session.query(Exam).filter_by(id=original_exam_id).first()
            if not original_exam:
                raise Exception("Original exam not found")

            # Utwórz kopię egzaminu
            user_exam = Exam(
                name=f"{original_exam.name} (shared)",
                description=original_exam.description,
                user_id=user_id,
                template_id=original_exam.id,
                is_template=False
            )
            session.add(user_exam)
            session.flush()

            # Skopiuj pytania i odpowiedzi
            original_questions = session.query(ExamQuestion).filter_by(exam_id=original_exam.id).all()
            for original_question in original_questions:
                user_question = ExamQuestion(
                    text=original_question.text,
                    exam_id=user_exam.id
                )
                session.add(user_question)
                session.flush()

                # Skopiuj odpowiedzi
                original_answers = session.query(ExamAnswer).filter_by(question_id=original_question.id).all()
                for original_answer in original_answers:
                    user_answer = ExamAnswer(
                        text=original_answer.text,
                        is_correct=original_answer.is_correct,
                        question_id=user_question.id
                    )
                    session.add(user_answer)

            if not db_session:
                session.commit()

            return user_exam.id

        except Exception as e:
            logger.error(f"Error copying exam for user: {e}")
            raise


def get_user_shared_exams(user_id: int, db_session: Session = None) -> list:
    """Pobiera listę udostępnionych egzaminów użytkownika"""
    with get_db_session(db_session) as session:
        try:
            shared_exams = session.query(UserExamAccess).filter_by(
                user_id=user_id,
                is_active=True
            ).all()

            result = []
            for access in shared_exams:
                original_exam = session.query(Exam).filter_by(id=access.original_exam_id).first()
                user_exam = session.query(Exam).filter_by(id=access.user_exam_id).first()

                if original_exam and user_exam:
                    question_count = session.query(ExamQuestion).filter_by(exam_id=user_exam.id).count()
                    result.append({
                        'user_exam_id': access.user_exam_id,
                        'original_exam_id': access.original_exam_id,
                        'exam_name': user_exam.name,
                        'original_exam_name': original_exam.name,
                        'question_count': question_count,
                        'added_at': access.added_at.isoformat(),
                        'code_used': access.accessed_via_code
                    })

            return result

        except Exception as e:
            logger.error(f"Error getting user shared exams: {e}")
            return []


# ===========================================
# FUNKCJE WSPÓLNE
# ===========================================

def get_shareable_content_info(share_code: str, content_type: str, db_session: Session = None) -> dict | None:
    """Pobiera informacje o udostępnianym zasobie"""
    with get_db_session(db_session) as session:
        try:
            shared_content = session.query(ShareableContent).filter_by(
                share_code=share_code,
                content_type=content_type,
                is_public=True
            ).first()

            if not shared_content:
                return None

            if content_type == 'deck':
                original = session.query(Deck).filter_by(id=shared_content.content_id).first()
                if not original:
                    return None

                creator = session.query(User).filter_by(id_=shared_content.creator_id).first()
                flashcard_count = session.query(Flashcard).filter_by(deck_id=original.id).count()

                return {
                    'share_code': share_code,
                    'content_id': original.id,
                    'deck_name': original.name,
                    'deck_description': original.description,
                    'creator_name': creator.user_name if creator else 'Unknown',
                    'created_at': shared_content.created_at.isoformat(),
                    'access_count': shared_content.access_count,
                    'flashcard_count': flashcard_count,
                    'content_type': 'deck'
                }

            elif content_type == 'exam':
                original = session.query(Exam).filter_by(id=shared_content.content_id).first()
                if not original:
                    return None

                creator = session.query(User).filter_by(id_=shared_content.creator_id).first()
                question_count = session.query(ExamQuestion).filter_by(exam_id=original.id).count()

                return {
                    'share_code': share_code,
                    'content_id': original.id,
                    'exam_name': original.name,
                    'exam_description': original.description,
                    'creator_name': creator.user_name if creator else 'Unknown',
                    'created_at': shared_content.created_at.isoformat(),
                    'access_count': shared_content.access_count,
                    'question_count': question_count,
                    'content_type': 'exam'
                }

            return None

        except Exception as e:
            logger.error(f"Error getting shareable content info: {e}")
            return None


def deactivate_share_code(share_code: str, creator_id: int, content_type: str, db_session: Session = None) -> bool:
    """Dezaktywuje kod udostępniania"""
    with get_db_session(db_session) as session:
        try:
            shared_content = session.query(ShareableContent).filter_by(
                share_code=share_code.upper(),
                creator_id=creator_id,
                content_type=content_type
            ).first()

            if not shared_content:
                return False

            shared_content.is_public = False

            if not db_session:
                session.commit()

            logger.info(f"Share code {share_code} deactivated by user {creator_id}")
            return True

        except Exception as e:
            logger.error(f"Error deactivating share code: {e}")
            return False


def get_user_created_share_codes(creator_id: int, content_type: str = None, db_session: Session = None) -> list:
    """Pobiera listę kodów udostępniania utworzonych przez użytkownika"""
    with get_db_session(db_session) as session:
        try:
            query = session.query(ShareableContent).filter_by(
                creator_id=creator_id,
                is_public=True
            )

            if content_type:
                query = query.filter_by(content_type=content_type)

            shared_contents = query.all()

            result = []
            for content in shared_contents:
                if content.content_type == 'deck':
                    original = session.query(Deck).filter_by(id=content.content_id).first()
                    if original:
                        item_count = session.query(Flashcard).filter_by(deck_id=original.id).count()
                        result.append({
                            'share_code': content.share_code,
                            'content_type': content.content_type,
                            'content_id': content.content_id,
                            'content_name': original.name,
                            'item_count': item_count,
                            'created_at': content.created_at.isoformat(),
                            'access_count': content.access_count
                        })

                elif content.content_type == 'exam':
                    original = session.query(Exam).filter_by(id=content.content_id).first()
                    if original:
                        item_count = session.query(ExamQuestion).filter_by(exam_id=original.id).count()
                        result.append({
                            'share_code': content.share_code,
                            'content_type': content.content_type,
                            'content_id': content.content_id,
                            'content_name': original.name,
                            'item_count': item_count,
                            'created_at': content.created_at.isoformat(),
                            'access_count': content.access_count
                        })

            return result

        except Exception as e:
            logger.error(f"Error getting user created share codes: {e}")
            return []


# ===========================================
# FUNKCJE STATYSTYK
# ===========================================

def get_sharing_statistics(user_id: int, db_session: Session = None) -> dict:
    """Pobiera statystyki udostępniania dla użytkownika"""
    with get_db_session(db_session) as session:
        try:
            # Statystyki utworzonych kodów
            created_deck_codes = session.query(ShareableContent).filter_by(
                creator_id=user_id,
                content_type='deck'
            ).count()

            created_exam_codes = session.query(ShareableContent).filter_by(
                creator_id=user_id,
                content_type='exam'
            ).count()

            # Statystyki pobranych zasobów
            added_decks = session.query(UserDeckAccess).filter_by(
                user_id=user_id,
                is_active=True
            ).count()

            added_exams = session.query(UserExamAccess).filter_by(
                user_id=user_id,
                is_active=True
            ).count()

            # Łączna liczba dostępów do kodów użytkownika - POPRAWIONA WERSJA
            total_deck_accesses = session.query(func.sum(ShareableContent.access_count)).filter_by(
                creator_id=user_id,
                content_type='deck'
            ).scalar() or 0

            total_exam_accesses = session.query(func.sum(ShareableContent.access_count)).filter_by(
                creator_id=user_id,
                content_type='exam'
            ).scalar() or 0

            return {
                'created_deck_codes': created_deck_codes,
                'created_exam_codes': created_exam_codes,
                'added_shared_decks': added_decks,
                'added_shared_exams': added_exams,
                'total_deck_accesses': total_deck_accesses,
                'total_exam_accesses': total_exam_accesses,
                'total_created_codes': created_deck_codes + created_exam_codes,
                'total_added_content': added_decks + added_exams
            }

        except Exception as e:
            logger.error(f"Error getting sharing statistics: {e}")
            return {}
