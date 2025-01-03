from typing import List
from sqlalchemy import (
    ForeignKey,
    Integer,
    String,
    DateTime,
    func,
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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    conversation_id: Mapped[int] = mapped_column(Integer, ForeignKey('conversations.id'))
    sender: Mapped[str] = mapped_column(String, nullable=False)
    text: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    conversation: Mapped[List['Conversation']] = relationship("Conversation", back_populates="messages")


class Conversation(Base):
    __tablename__ = 'conversations'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)  # Użytkownik, do którego należy rozmowa
    created_at: Mapped[DateTime] = mapped_column(DateTime, default=datetime.now(timezone.utc), nullable=False)  # Data i czas rozpoczęcia rozmowy
    title: Mapped[str] = mapped_column(String, nullable=True)

    # Relacja do wiadomości
    messages: Mapped[List['Message']] = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


