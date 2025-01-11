from typing import Optional
from sqlalchemy import (
    Integer,
    String,
    Boolean,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    scoped_session
)
from .base import Base


class User(Base):
    __tablename__ = 'users'
    
    id_: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_name: Mapped[str] = mapped_column(String, nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    role: Mapped[str] = mapped_column(String, nullable=False, default='user')    
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)

    @staticmethod
    def get_user(session: scoped_session, user_name: str) -> Optional['User'] | None:
        user: Optional['User'] | None = session.query(User).filter_by(user_name=user_name).first()
        return user
