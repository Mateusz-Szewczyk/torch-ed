# agent_memory.py

from typing import List, Optional, Type, Any
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker, scoped_session, InstrumentedAttribute
from sqlalchemy.exc import SQLAlchemyError

from ..models import Base, Conversation, Message
from ..database import DATABASE_URL
import logging

logger = logging.getLogger(__name__)

engine = create_engine(DATABASE_URL)
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base.metadata.create_all(bind=engine)

def create_memory(user_id: str, title: Optional[str] = None) -> Type[Conversation] | Conversation:
    session = SessionLocal()
    try:
        conversation = session.query(Conversation).filter_by(user_id=user_id).order_by(
            desc(Conversation.created_at)).first()
        if conversation:
            logger.debug(f"Znaleziono istniejącą rozmowę dla użytkownika {user_id}.")
            return conversation
        else:
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

def get_latest_checkpoint(user_id: str, conversation_id: int) -> Type[Conversation] | None:
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

def get_conversation_history(conversation_id: int, max_history_length: int) -> list[Any] | list[InstrumentedAttribute]:
    session = SessionLocal()
    try:
        messages = session.query(Message).filter_by(conversation_id=conversation_id).order_by(Message.created_at).all()
        if not messages:
            logger.debug(f"Brak wiadomości w rozmowie ID={conversation_id}.")
            return []

        pairs = []
        temp_pair = []
        for msg in messages:
            temp_pair.append(msg.text)
            if len(temp_pair) == 2:
                pairs.append(temp_pair)
                temp_pair = []
        if temp_pair:
            pairs.append(temp_pair)

        limited_pairs = pairs[-max_history_length:]

        conversation_history = []
        for pair in limited_pairs:
            conversation_history.extend(pair)

        logger.debug(f"Retrieved conversation history for conversation ID={conversation_id}: {conversation_history}")
        logger.info("conv history: %s", conversation_history)
        logger.info("conv history len %s", len(conversation_history))
        return conversation_history
    except SQLAlchemyError as e:
        logger.error(f"Error podczas pobierania historii rozmowy: {e}", exc_info=True)
        return []
    finally:
        session.close()