from fastapi import APIRouter, HTTPException, Depends, Response, Body
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from typing import List, Optional

from ..models import Conversation, Message, User, Deck
from ..schemas import (
    ConversationRead,
    MessageCreate,
    ConversationUpdate,
    MessageRead,
)
from ..dependencies import get_db
from ..auth import get_current_user

import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/", response_model=ConversationRead, status_code=201)
async def create_conversation(
    deck_id: Optional[int] = Body(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Utwórz nową konwersację dla zalogowanego użytkownika.
    Jeśli podany zostanie deck_id, to po utworzeniu konwersacji
    zostanie zaktualizowane pole conversation_id w tabeli decków.
    """
    logger.info(f"Creating a new conversation for user_id: {current_user.id_}")
    try:
        new_conversation = Conversation(
            user_id=current_user.id_,
            title="New conversation",
        )
        db.add(new_conversation)
        db.commit()
        db.refresh(new_conversation)

        # Jeśli przekazano deck_id, spróbuj zaktualizować odpowiedni deck
        if deck_id is not None:
            deck = db.query(Deck).filter_by(id=deck_id, user_id=current_user.id_).first()
            if deck:
                deck.conversation_id = new_conversation.id
                db.commit()
        logger.info(f"Created new conversation with ID {new_conversation.id}")
        return new_conversation
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating conversation: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error creating conversation: {str(e)}"
        )

@router.get("/", response_model=List[ConversationRead])
async def get_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Pobierz wszystkie konwersacje dla zalogowanego użytkownika.
    """
    user_id = current_user.id_
    logger.info(f"Fetching conversations for user_id: {user_id}")
    try:
        conversations = db.query(Conversation).filter_by(user_id=user_id).all()
        return conversations
    except Exception as e:
        logger.error(f"Error fetching conversations: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching conversations: {str(e)}"
        )

@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Usuń konwersację oraz powiązane z nią wiadomości,
    o ile należy do zalogowanego użytkownika.
    """
    logger.info(f"Deleting conversation {conversation_id}")
    try:
        conversation = db.query(Conversation).filter_by(id=conversation_id).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        if conversation.user_id != current_user.id_:
            raise HTTPException(
                status_code=403,
                detail="Forbidden: You cannot delete a conversation that isn't yours."
            )

        db.delete(conversation)
        db.commit()
        logger.info(f"Deleted conversation {conversation_id}")
        return Response(status_code=204)
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting conversation: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting conversation: {str(e)}"
        )

@router.post("/{conversation_id}/messages/", response_model=MessageRead, status_code=201)
async def create_message(
    conversation_id: int,
    message: MessageCreate = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Dodaj nową wiadomość w konwersacji, o ile konwersacja należy do zalogowanego użytkownika.
    """
    try:
        if not message.text or not message.sender:
            raise HTTPException(status_code=400, detail="Invalid message data")

        const_conversation = db.query(Conversation).filter_by(id=conversation_id).first()
        if not const_conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        if const_conversation.user_id != current_user.id_:
            raise HTTPException(
                status_code=403,
                detail="Forbidden: You cannot post messages to a conversation that isn't yours."
            )

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
        raise HTTPException(
            status_code=422,
            detail="Unable to save message due to database constraint"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/{conversation_id}/messages/", response_model=List[MessageRead])
async def get_messages(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Pobierz wiadomości dla konwersacji, o ile należy do zalogowanego użytkownika.
    """
    logger.info(f"Fetching messages for conversation {conversation_id}")
    try:
        conversation = db.query(Conversation).filter_by(id=conversation_id).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        if conversation.user_id != current_user.id_:
            raise HTTPException(
                status_code=403,
                detail="Forbidden: You cannot view messages from a conversation that isn't yours."
            )

        messages = (
            db.query(Message)
            .filter_by(conversation_id=conversation_id)
            .order_by(Message.created_at)
            .all()
        )
        return messages
    except Exception as e:
        logger.error(f"Error fetching messages: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching messages: {str(e)}"
        )

@router.patch("/{conversation_id}", response_model=ConversationRead)
async def update_conversation(
    conversation_id: int,
    conversation_update: ConversationUpdate = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Zmień tytuł konwersacji, o ile należy do zalogowanego użytkownika.
    """
    logger.info(f"Updating conversation {conversation_id}")
    try:
        conversation = db.query(Conversation).filter_by(id=conversation_id).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        if str(conversation.user_id) != current_user.id_:
            raise HTTPException(
                status_code=403,
                detail="Forbidden: You cannot update a conversation that isn't yours."
            )

        if conversation_update.title is not None:
            conversation.title = conversation_update.title

        db.commit()
        db.refresh(conversation)

        logger.info(f"Updated conversation {conversation_id}")
        return conversation
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating conversation: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error updating conversation: {str(e)}"
        )
