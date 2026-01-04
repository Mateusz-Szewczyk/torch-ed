"""
Router for File Categories Management
"""
import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..dependencies import get_db
from ..models import User
from ..auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/categories", tags=["categories"])


# =============================================================================
# PYDANTIC SCHEMAS
# =============================================================================

class CategoryBase(BaseModel):
    name: str

    class Config:
        from_attributes = True


class CategoryCreate(CategoryBase):
    pass


class CategoryRead(CategoryBase):
    id: UUID
    # Changed from int to UUID to match database schema implied by the SQL
    user_id: Optional[UUID] = None
    is_system: bool = False

    class Config:
        from_attributes = True


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/", response_model=List[CategoryRead])
async def get_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all available categories for the current user.
    Returns both System Default Categories (user_id=null) AND User's Custom Categories.
    """
    try:
        user_id_str = str(current_user.id_)

        # FIX: Use CAST(... AS UUID) instead of ::uuid to avoid parser syntax errors
        # We explicitly cast the string parameter to UUID for the comparison
        result = db.execute(
            text("""
                SELECT id, user_id, name, created_at 
                FROM file_categories 
                WHERE user_id IS NULL OR user_id = CAST(:user_id AS UUID)
                ORDER BY created_at
            """),
            {"user_id": user_id_str}
        ).fetchall()

        categories = []
        for row in result:
            categories.append(CategoryRead(
                id=row.id,
                name=row.name,
                user_id=row.user_id, # SQLAlchemy handles the UUID conversion
                is_system=(row.user_id is None)
            ))

        logger.info(f"Fetched {len(categories)} categories for user {current_user.id_}")
        return categories

    except Exception as e:
        logger.error(f"Error fetching categories: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching categories: {str(e)}")


@router.post("/", response_model=CategoryRead, status_code=201)
async def create_category(
    category: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new custom category for the current user.
    """
    try:
        user_id_str = str(current_user.id_)

        # FIX: Use CAST(:user_id AS UUID)
        existing = db.execute(
            text("""
                SELECT id FROM file_categories 
                WHERE user_id = CAST(:user_id AS UUID) AND name = :name
            """),
            {"user_id": user_id_str, "name": category.name}
        ).fetchone()

        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Category '{category.name}' already exists"
            )

        # FIX: The Main Fix.
        # Replaced ':user_id::uuid' with 'CAST(:user_id AS UUID)'
        # This prevents the syntax error where the parser confuses ':' with a parameter
        result = db.execute(
            text("""
                INSERT INTO file_categories (id, user_id, name, created_at)
                VALUES (gen_random_uuid(), CAST(:user_id AS UUID), :name, NOW())
                RETURNING id, user_id, name, created_at
            """),
            {"user_id": user_id_str, "name": category.name}
        ).fetchone()

        db.commit()

        logger.info(f"Created category '{category.name}' for user {current_user.id_}")

        return CategoryRead(
            id=result.id,
            name=result.name,
            user_id=result.user_id,
            is_system=False
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating category: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating category: {str(e)}")


@router.delete("/{category_id}", status_code=204)
async def delete_category(
    category_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a custom category (only user's own categories can be deleted).
    """
    try:
        user_id_str = str(current_user.id_)

        # FIX: Explicit casting for robust type safety
        category = db.execute(
            text("""
                SELECT id, user_id, name FROM file_categories 
                WHERE id = CAST(:category_id AS UUID) AND user_id = CAST(:user_id AS UUID)
            """),
            {"category_id": str(category_id), "user_id": user_id_str}
        ).fetchone()

        if not category:
            raise HTTPException(
                status_code=404,
                detail="Category not found or not owned by user"
            )

        if category.user_id is None:
            raise HTTPException(
                status_code=403,
                detail="Cannot delete system categories"
            )

        db.execute(
            text("DELETE FROM file_categories WHERE id = CAST(:category_id AS UUID)"),
            {"category_id": str(category_id)}
        )
        db.commit()

        logger.info(f"Deleted category {category_id} by user {current_user.id_}")
        return None

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting category: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting category: {str(e)}")
