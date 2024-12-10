# agent_memory.py

from typing import List, Optional, Dict, Any
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import SQLAlchemyError

from ..models import Base, Conversation, Message  # Ensure models are correctly imported
from ..database import DATABASE_URL
import logging

# ------------------------------
# 1. Konfiguracja Logowania
# ------------------------------

logger = logging.getLogger(__name__)

# ------------------------------
# 2. Konfiguracja SQLAlchemy
# ------------------------------

# Tworzenie silnika SQLAlchemy
engine = create_engine(DATABASE_URL)

# Tworzenie sesji
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

# Tworzenie wszystkich tabel (jeśli jeszcze nie istnieją)
Base.metadata.create_all(bind=engine)


# ------------------------------
# 3. Funkcje Obsługi Pamięci
# ------------------------------

def create_memory(user_id: str, title: Optional[str] = None) -> Conversation:
    """
    Tworzy nową rozmowę dla użytkownika lub zwraca najnowszą istniejącą.

    Args:
        user_id (str): ID użytkownika.
        title (Optional[str], optional): Tytuł rozmowy. Defaults to None.

    Returns:
        Conversation: Instancja rozmowy.
    """
    session = SessionLocal()
    try:
        # Sprawdzenie, czy istnieje otwarta rozmowa dla użytkownika
        conversation = session.query(Conversation).filter_by(user_id=user_id).order_by(
            desc(Conversation.created_at)).first()
        if conversation:
            logger.debug(f"Znaleziono istniejącą rozmowę dla użytkownika {user_id}.")
            return conversation
        else:
            # Tworzenie nowej rozmowy
            new_conversation = Conversation(user_id=user_id, title=title)
            session.add(new_conversation)
            session.commit()
            session.refresh(new_conversation)
            logger.info(f"Utworzono nową rozmowę dla użytkownika {user_id}.")
            return new_conversation
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Error podczas tworzenia lub pobierania rozmowy: {e}", exc_info=True)
        raise
    finally:
        session.close()


def get_latest_checkpoint(user_id: str, conversation_id: int) -> Optional[Conversation]:
    """
    Pobiera rozmowę dla danego użytkownika o konkretnym ID rozmowy.

    Args:
        user_id (str): ID użytkownika.
        conversation_id (int): ID rozmowy.
    Returns:
        Optional[Conversation]: Rozmowa lub None, jeśli nie istnieje.
    """
    session = SessionLocal()
    try:
        conversation = session.query(Conversation).filter_by(
            user_id=user_id,
            id=conversation_id
        ).first()

        if conversation:
            logger.debug(f"Znaleziono rozmowę: ID={conversation.id} dla użytkownika {user_id}.")
            return conversation
        else:
            logger.debug(f"Nie znaleziono rozmowy o ID {conversation_id} dla użytkownika {user_id}.")
            return None
    except SQLAlchemyError as e:
        logger.error(f"Error podczas pobierania rozmowy: {e}", exc_info=True)
        return None
    finally:
        session.close()


def get_conversation_history(conversation_id: int, max_history_length: int) -> List[str]:
    """
    Pobiera historię rozmowy do określonej długości.

    Args:
        conversation_id (int): ID rozmowy.
        max_history_length (int): Maksymalna liczba wymian (query-response).

    Returns:
        List[str]: Lista wiadomości przeplatanych użytkownika i AI.
    """
    session = SessionLocal()
    try:
        messages = session.query(Message).filter_by(conversation_id=conversation_id).order_by(Message.created_at).all()
        if not messages:
            logger.debug(f"Brak wiadomości w rozmowie ID={conversation_id}.")
            return []

        # Ograniczenie do ostatnich max_history_length wymian
        # Każda wymiana to dwie wiadomości: użytkownik i AI
        pairs = []
        temp_pair = []
        for msg in messages:
            temp_pair.append(msg.text)
            if len(temp_pair) == 2:
                pairs.append(temp_pair)
                temp_pair = []
        if temp_pair:
            pairs.append(temp_pair)  # Dodanie ostatniej niepełnej pary

        limited_pairs = pairs[-max_history_length:]

        conversation_history = []
        for pair in limited_pairs:
            conversation_history.extend(pair)

        logger.debug(f"Retrieved conversation history for conversation ID={conversation_id}: {conversation_history}")
        return conversation_history
    except SQLAlchemyError as e:
        logger.error(f"Error podczas pobierania historii rozmowy: {e}", exc_info=True)
        return []
    finally:
        session.close()
