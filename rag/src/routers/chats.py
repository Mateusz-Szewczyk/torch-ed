from fastapi import APIRouter, HTTPException, Depends, Response, Body
from sqlalchemy import and_, exists
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid as uuid_module

from ..models import Conversation, Message, User, Deck, Exam, Workspace
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
        exam_id: Optional[int] = Body(None),
        workspace_id: Optional[str] = Body(None),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    """
    Utwórz nową konwersację dla zalogowanego użytkownika.
    Jeśli podany zostanie deck_id, to po utworzeniu konwersacji
    zostanie zaktualizowane pole conversation_id w tabeli decków.
    workspace_id pozwala na przypisanie konwersacji do workspace.
    """
    logger.info(f"Creating a new conversation for user_id: {current_user.id_}, workspace_id: {workspace_id}")
    try:
        # Validate workspace if provided
        workspace_uuid = None
        if workspace_id:
            try:
                workspace_uuid = uuid_module.UUID(workspace_id)
                workspace = db.query(Workspace).filter(
                    Workspace.id == workspace_uuid,
                    Workspace.user_id == current_user.id_
                ).first()
                if not workspace:
                    raise HTTPException(status_code=404, detail="Workspace not found")
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid workspace_id format")

        new_conversation = Conversation(
            user_id=current_user.id_,
            title="New conversation",
            workspace_id=workspace_uuid,
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

        if exam_id is not None:
            exam = db.query(Exam).filter_by(id=exam_id, user_id=current_user.id_).first()
            if exam:
                exam.conversation_id = new_conversation.id
                db.commit()

        logger.info(f"Created new conversation with ID {new_conversation.id}")

        # Return with workspace_id as string
        return {
            "id": new_conversation.id,
            "user_id": new_conversation.user_id,
            "title": new_conversation.title,
            "workspace_id": str(new_conversation.workspace_id) if new_conversation.workspace_id else None,
            "created_at": new_conversation.created_at,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating conversation: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error creating conversation: {str(e)}"
        )


@router.get("/", response_model=List[ConversationRead])
async def get_conversations(
        workspace_id: Optional[str] = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    """
    Pobierz konwersacje dla zalogowanego użytkownika.
    - Jeśli workspace_id jest podany, zwróć konwersacje tylko dla tego workspace.
    - Jeśli workspace_id nie jest podany, zwróć konwersacje bez workspace,
      wykluczając te które są już używane w egzaminach lub taliach kart.
    """
    user_id = current_user.id_
    logger.info(f"Fetching conversations for user_id: {user_id}, workspace_id: {workspace_id}")
    try:
        if workspace_id:
            # Get conversations for specific workspace
            try:
                workspace_uuid = uuid_module.UUID(workspace_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid workspace_id format")

            conversations = db.query(Conversation).filter(
                Conversation.user_id == user_id,
                Conversation.workspace_id == workspace_uuid
            ).order_by(Conversation.created_at.desc()).all()
        else:
            # Get standalone conversations (no workspace, no deck/exam link)
            conversations = db.query(Conversation).filter(
                Conversation.user_id == user_id,
                Conversation.workspace_id.is_(None),
                ~exists().where(
                    and_(
                        Exam.conversation_id == Conversation.id,
                        Exam.conversation_id.isnot(None)
                    )
                ),
                ~exists().where(
                    and_(
                        Deck.conversation_id == Conversation.id,
                        Deck.conversation_id.isnot(None)
                    )
                )
            ).order_by(Conversation.created_at.desc()).all()

        # Convert workspace_id to string for response
        result = []
        for conv in conversations:
            result.append({
                "id": conv.id,
                "user_id": conv.user_id,
                "title": conv.title,
                "workspace_id": str(conv.workspace_id) if conv.workspace_id else None,
                "created_at": conv.created_at,
            })
        return result
    except HTTPException:
        raise
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
    Deletes a conversation and its associated messages if it belongs to the logged-in user.
    Before deletion, sets the conversation_id field of any Deck (or Exam) referencing this conversation to NULL.
    """
    logger.info(f"Deleting conversation {conversation_id}")
    try:
        # Retrieve the conversation to delete
        conversation = db.query(Conversation).filter_by(id=conversation_id).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Authorization check
        if conversation.user_id != current_user.id_:
            raise HTTPException(
                status_code=403,
                detail="Forbidden: You cannot delete a conversation that isn't yours."
            )

        # Update all decks an exams that reference this conversation
        decks_to_update = db.query(Deck).filter(Deck.conversation_id == conversation_id).all()
        for deck in decks_to_update:
            deck.conversation_id = None

        exams_to_update = db.query(Exam).filter(Exam.conversation_id == conversation_id).all()
        for exam in exams_to_update:
            exam.conversation_id = None

        # Now delete the conversation
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
    Opcjonalnie można przekazać metadata z krokami (steps) i akcjami (actions).
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
            meta_json=message.metadata,  # Include metadata (steps, actions)
        )
        db.add(new_message)
        db.commit()
        db.refresh(new_message)

        # Manually create MessageRead to properly map meta_json to metadata
        return MessageRead(
            id=new_message.id,
            conversation_id=new_message.conversation_id,
            sender=new_message.sender,
            text=new_message.text,
            created_at=new_message.created_at,
            metadata=new_message.meta_json  # Map meta_json to metadata
        ) 
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

        # Manually map meta_json to metadata for proper JSON response
        result = []
        for msg in messages:
            result.append(MessageRead(
                id=msg.id,
                conversation_id=msg.conversation_id,
                sender=msg.sender,
                text=msg.text,
                created_at=msg.created_at,
                metadata=msg.meta_json  # Map meta_json to metadata
            ))
        return result
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

        if str(conversation.user_id) != str(current_user.id_):
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
