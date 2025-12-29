from enum import Enum
from typing import Dict, Any, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models import User, ORMFile, Deck, Exam, ExamQuestion, Flashcard, Message
import datetime
from datetime import timedelta

class UserRole(str, Enum):
    FREE = "user"
    PRO = "pro"
    EXPERT = "expert"

# Use -1 to represent unlimited (JSON doesn't support float('inf'))
UNLIMITED = -1

LIMITS = {
    UserRole.FREE: {
        "max_file_size_mb": 5,
        "max_files": 3,
        "max_decks": 5,
        "max_questions_period": 50,
        "question_period_days": 7, # weekly
    },
    UserRole.PRO: {
        "max_file_size_mb": 5,
        "max_files": 10,
        "max_decks": 20,
        "max_questions_period": 500,
        "question_period_days": 30, # monthly
    },
    UserRole.EXPERT: {
        "max_file_size_mb": 5,
        "max_files": UNLIMITED,
        "max_decks": UNLIMITED,
        "max_questions_period": UNLIMITED,
        "question_period_days": 30,
    }
}

class SubscriptionService:
    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user
        # Default to FREE if role is unknown
        try:
            self.role = UserRole(user.role)
        except ValueError:
            self.role = UserRole.FREE

        self.limits = LIMITS[self.role]

    def get_usage_stats(self) -> Dict[str, Any]:
        """Returns current usage stats for the user."""

        # Files
        file_count = self.db.query(func.count(ORMFile.id)).filter(ORMFile.user_id == self.user.id_).scalar()

        # Decks
        deck_count = self.db.query(func.count(Deck.id)).filter(Deck.user_id == self.user.id_).scalar()

        # Questions generated (Exams + Flashcards)
        # Note: This is a bit tricky because we don't strictly track "generated" vs "created manually"
        # but for now we can count all questions/flashcards created in the period.
        # Or we can try to infer from logs/metadata if we had it.
        # For simplicity, let's count created items in the period.

        period_days = self.limits["question_period_days"]
        start_date = datetime.datetime.now(datetime.UTC) - timedelta(days=period_days)

        total_questions_used = self.db.query(Message)\
            .filter(Message.sender != 'bot')\
            .filter(Message.created_at >= start_date)\
            .count()

        # Get role_expiry if user has premium subscription
        role_expiry = None
        if hasattr(self.user, 'role_expiry') and self.user.role_expiry:
            role_expiry = self.user.role_expiry.isoformat() if isinstance(self.user.role_expiry, datetime.datetime) else str(self.user.role_expiry)

        return {
            "role": self.role.value,
            "role_expiry": role_expiry,
            "limits": self.limits,
            "usage": {
                "files": file_count,
                "decks": deck_count,
                "questions_period": total_questions_used
            }
        }

    def check_file_upload_limit(self, file_size_bytes: int):
        # Check file size
        max_size_mb = self.limits["max_file_size_mb"]
        if file_size_bytes > max_size_mb * 1024 * 1024:
             raise HTTPException(status_code=403, detail=f"File too large. Limit is {max_size_mb}MB.")

        # Check file count
        max_files = self.limits["max_files"]
        if max_files == UNLIMITED:
            return

        current_files = self.db.query(func.count(ORMFile.id)).filter(ORMFile.user_id == self.user.id_).scalar()
        if current_files >= max_files:
            raise HTTPException(status_code=403, detail=f"File limit reached. Limit is {max_files} files.")

    def check_deck_limit(self):
        max_decks = self.limits["max_decks"]
        if max_decks == UNLIMITED:
            return

        current_decks = self.db.query(func.count(Deck.id)).filter(Deck.user_id == self.user.id_).scalar()
        if current_decks >= max_decks:
            raise HTTPException(status_code=403, detail=f"Deck limit reached. Limit is {max_decks} decks.")

    def check_generation_limit(self, estimated_count: int = 1):
        """
        Checks if user can generate more content (flashcards/questions).
        """
        max_questions = self.limits["max_questions_period"]
        if max_questions == UNLIMITED:
            return

        stats = self.get_usage_stats()
        current_usage = stats["usage"]["questions_period"]

        if current_usage + estimated_count > max_questions:
            raise HTTPException(
                status_code=403,
                detail=f"Generation limit reached. You have used {current_usage}/{max_questions} questions in the last {self.limits['question_period_days']} days."
            )

