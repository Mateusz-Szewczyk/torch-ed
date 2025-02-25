import logging
from sqlalchemy.exc import SQLAlchemyError
from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate
from typing import Optional
from .agent_memory import SessionLocal
from ..models import Conversation

logger = logging.getLogger(__name__)

def produce_conversation_name(query: str, model: ChatAnthropic) -> str:
    """
    Produces a concise conversation title based on the user's first query.
    The title is a short phrase (up to 5 words) that summarizes the topic.
    """
    system_prompt = (
        "You are an assistant that creates short, descriptive conversation titles based on the user's first query. "
        "Do not mention that you are generating a title. Provide a concise title (up to 5 words) that summarizes the topic."
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{question}")
    ])
    messages = prompt.format_messages(question=query)
    logger.debug(f"Generating conversation title with messages: {messages}")
    try:
        response = model.invoke(messages).content
        title = response.strip()
        if not title:
            logger.warning("Received empty title from model.")
            title = "New Conversation"
        logger.info(f"Generated conversation title: {title}")
        return title
    except Exception as e:
        logger.error(f"Error generating conversation title: {e}", exc_info=True)
        return "New Conversation"

def update_conversation_title(conversation_id: int, title: str) -> None:
    """
    Updates the title of an existing conversation in the database.
    """
    from ..models import Conversation  # Adjust the import path as needed.
    session = SessionLocal()
    try:
        conversation = session.query(Conversation).filter_by(id=conversation_id).first()
        if conversation:
            conversation.title = title
            session.commit()
            logger.info(f"Updated conversation ID={conversation_id} title to: {title}")
        else:
            logger.warning(f"Conversation ID={conversation_id} not found. Cannot update title.")
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Error updating conversation title: {e}", exc_info=True)
    finally:
        session.close()

def set_conversation_title(conversation: Conversation, query: str, model: ChatAnthropic) -> None:
    """
    If the conversation has a default title (e.g. "New Conversation"), produce a new title using the model and update it.
    """
    title = produce_conversation_name(query, model)
    update_conversation_title(conversation.id, title)
