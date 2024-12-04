# src/routers/chats.py

from fastapi import APIRouter, HTTPException, Depends, status, Response, Body
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from typing import List

from ..models import Conversation, Message
from ..schemas import (
    ConversationCreate,
    ConversationRead,
    MessageCreate,
    MessageRead,
)
from ..dependencies import get_db

import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# Tworzenie nowej konwersacji
@router.post("/", response_model=ConversationRead, status_code=201)
async def create_conversation(conversation: ConversationCreate, db: Session = Depends(get_db)):
    """
    Utwórz nową konwersację.
    """
    logger.info(f"Creating a new conversation for user_id: {conversation.user_id}")

    try:
        new_conversation = Conversation(
            user_id=conversation.user_id,
            title=conversation.title,
        )

        db.add(new_conversation)
        db.commit()
        db.refresh(new_conversation)

        logger.info(f"Created new conversation with ID {new_conversation.id}")
        return new_conversation

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating conversation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating conversation: {str(e)}")

# Pobieranie konwersacji dla danego użytkownika
@router.get("/", response_model=List[ConversationRead])
async def get_conversations(user_id: str, db: Session = Depends(get_db)):
    """
    Pobierz wszystkie konwersacje dla konkretnego użytkownika.
    """
    logger.info(f"Fetching conversations for user_id: {user_id}")
    try:
        conversations = db.query(Conversation).filter(Conversation.user_id == user_id).all()
        return conversations
    except Exception as e:
        logger.error(f"Error fetching conversations: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching conversations: {str(e)}")

# Usuwanie konwersacji
@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(conversation_id: int, db: Session = Depends(get_db)):
    """
    Usuń konwersację oraz powiązane z nią wiadomości.
    """
    logger.info(f"Deleting conversation {conversation_id}")
    try:
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        db.delete(conversation)
        db.commit()
        logger.info(f"Deleted conversation {conversation_id}")
        return Response(status_code=204)
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting conversation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting conversation: {str(e)}")

# Tworzenie nowej wiadomości w konwersacji
@router.post("/{conversation_id}/messages/", response_model=MessageRead, status_code=201)
async def create_message(conversation_id: int, message: MessageCreate = Body(...), db: Session = Depends(get_db)):
    try:
        # Walidacja danych wejściowych
        if not message.text or not message.sender:
            raise HTTPException(status_code=400, detail="Invalid message data")

        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        new_message = Message(
            conversation_id=conversation_id,
            sender=message.sender,
            text=message.text,
        )

        db.add(new_message)
        db.commit()
        db.refresh(new_message)

        return new_message

    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=422, detail="Unable to save message due to database constraint")
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Pobieranie wiadomości dla konwersacji
@router.get("/{conversation_id}/messages/", response_model=List[MessageRead])
async def get_messages(conversation_id: int, db: Session = Depends(get_db)):
    """
    Pobierz wiadomości dla konwersacji.
    """
    logger.info(f"Fetching messages for conversation {conversation_id}")
    try:
        messages = db.query(Message).filter(Message.conversation_id == conversation_id).order_by(Message.created_at).all()
        return messages
    except Exception as e:
        logger.error(f"Error fetching messages: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching messages: {str(e)}")
