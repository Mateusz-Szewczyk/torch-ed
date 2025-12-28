import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..dependencies import get_db
from ..auth import get_current_user
from ..models import User
from ..services.subscription import SubscriptionService

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/stats")
async def get_subscription_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns subscription stats for the current user."""
    try:
        subscription_service = SubscriptionService(db, current_user)
        return subscription_service.get_usage_stats()
    except Exception as e:
        logger.error(f"Error getting subscription stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting subscription stats: {str(e)}")

