import logging
import os
from typing import List, Optional, Any, Type
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import SQLAlchemyError

# Importy LangChain - kluczowe dla "prawidłowego" zarządzania pamięcią
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

from ..models import Base, Conversation, Message
from ..database import DATABASE_URL

logger = logging.getLogger(__name__)

# Konfiguracja silnika i sesji
engine = create_engine(DATABASE_URL)
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

# Inicjalizacja tabel (jeśli nie istnieją)
Base.metadata.create_all(bind=engine)


def create_memory(user_id: str, title: Optional[str] = None) -> Type[Conversation] | Conversation:
    """
    Pobiera najnowszą rozmowę użytkownika lub tworzy nową, jeśli żadna nie istnieje.
    Zwraca obiekt modelu Conversation.
    """
    session = SessionLocal()
    try:
        # Próba pobrania ostatniej aktywnej rozmowy
        conversation = session.query(Conversation).filter_by(user_id=user_id).order_by(
            desc(Conversation.created_at)).first()

        if conversation:
            logger.debug(f"Pobrano istniejącą rozmowę: ID={conversation.id} dla użytkownika {user_id}")
            return conversation
        else:
            # Tworzenie nowej rozmowy, jeśli baza jest pusta dla tego usera
            new_conversation = Conversation(user_id=user_id, title=title or "Nowa rozmowa")
            session.add(new_conversation)
            session.commit()
            session.refresh(new_conversation)
            logger.info(f"Utworzono nową rozmowę dla użytkownika {user_id}: ID={new_conversation.id}")
            return new_conversation
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Błąd SQLAlchemy w create_memory: {e}", exc_info=True)
        raise
    finally:
        session.close()


def get_latest_checkpoint(user_id: str, conversation_id: int) -> Optional[Conversation]:
    """
    Pobiera konkretną rozmowę po ID dla danego użytkownika.
    """
    session = SessionLocal()
    try:
        conversation = session.query(Conversation).filter_by(
            user_id=user_id,
            id=conversation_id
        ).first()
        return conversation
    except SQLAlchemyError as e:
        logger.error(f"Błąd podczas pobierania checkpointu: {e}", exc_info=True)
        return None
    finally:
        session.close()


def get_conversation_history(conversation_id: int, max_history_length: int) -> List[BaseMessage]:
    """
    Pobiera historię wiadomości i konwertuje ją na format LangChain (HumanMessage/AIMessage).
    Zapewnia poprawność ról, nawet jeśli sekwencja w bazie jest niestandardowa.
    """
    session = SessionLocal()
    try:
        # Pobieramy wiadomości posortowane chronologicznie
        db_messages = session.query(Message).filter_by(
            conversation_id=conversation_id
        ).order_by(Message.created_at).all()

        if not db_messages:
            return []

        langchain_messages = []
        for msg in db_messages:
            # Mapowanie roli z bazy danych na klasy LangChain
            # Przyjmujemy, że 'user' to Human, a 'bot'/'assistant' to AI
            if msg.sender.lower() in ['user', 'human']:
                langchain_messages.append(HumanMessage(content=msg.text))
            else:
                langchain_messages.append(AIMessage(content=msg.text))

        # Zwracamy tylko ostatnie N wiadomości (max_history_length)
        # Slicing od tyłu, aby zachować chronologię
        limited_history = langchain_messages[-max_history_length:]

        logger.info(f"Pobrano {len(limited_history)} wiadomości historii dla konwersacji {conversation_id}")
        return limited_history

    except SQLAlchemyError as e:
        logger.error(f"Błąd podczas pobierania historii: {e}", exc_info=True)
        return []
    finally:
        session.close()
