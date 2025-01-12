from sqlalchemy import (
    Integer,
    String,
    DateTime, Column, ForeignKey,
)

from datetime import datetime, timezone
from .base import Base


class ORMFile(Base):
    __tablename__ = 'files'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id_'), index=True, nullable=False)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)