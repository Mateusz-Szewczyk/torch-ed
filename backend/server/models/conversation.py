from typing import List
from sqlalchemy import (
    ForeignKey,
    Integer,
    String,
    DateTime,
    func, Column,
)
from .base import Base
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)
from datetime import datetime, timezone


class Message(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey('conversations.id'))
    sender = Column(String, nullable=False)
    text = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    conversation = relationship(
        "Conversation",
        back_populates="messages"
    )


class Conversation(Base):
    __tablename__ = 'conversations'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id_'), index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    title = Column(String, nullable=True)

    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan"
    )