"""
Router for File Categories Management
"""
import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import or_, text, cast, String
from sqlalchemy.orm import Session

from ..dependencies import get_db
from ..models import FileCategory, User
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
    user_id: Optional[int] = None
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
        # Use raw SQL to handle potential type mismatch between model and database
        # Database may have user_id as UUID while model defines Integer
        user_id_str = str(current_user.id_)

        result = db.execute(
            text("""
                SELECT id, user_id, name, created_at 
                FROM file_categories 
                WHERE user_id IS NULL OR user_id::text = :user_id
                ORDER BY created_at
            """),
            {"user_id": user_id_str}
        ).fetchall()

        # Transform to include is_system flag
        categories = []
        for row in result:
            # user_id could be integer or UUID depending on database schema
            # For response, we just need to know if it's null (system) or not
            uid = None
            if row.user_id is not None:
                try:
                    uid = int(str(row.user_id))
                except (ValueError, TypeError):
                    # Keep as None if can't convert
                    uid = None

            categories.append(CategoryRead(
                id=row.id,
                name=row.name,
                user_id=uid,
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

        # Check if category with this name already exists for this user using raw SQL
        existing = db.execute(
            text("""
                SELECT id FROM file_categories 
                WHERE user_id::text = :user_id AND name = :name
            """),
            {"user_id": user_id_str, "name": category.name}
        ).fetchone()

        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Category '{category.name}' already exists"
            )

        # Insert using raw SQL to handle type conversion
        # Database column is UUID type, so we need to cast the user_id properly
        result = db.execute(
            text("""
                INSERT INTO file_categories (id, user_id, name, created_at)
                VALUES (gen_random_uuid(), :user_id::uuid, :name, NOW())
                RETURNING id, user_id, name, created_at
            """),
            {"user_id": user_id_str, "name": category.name}
        ).fetchone()

        db.commit()

        logger.info(f"Created category '{category.name}' for user {current_user.id_}")

        # Convert user_id safely
        uid = None
        if result.user_id is not None:
            try:
                uid = int(str(result.user_id))
            except (ValueError, TypeError):
                uid = None

        return CategoryRead(
            id=result.id,
            name=result.name,
            user_id=uid,
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

        # Find category using raw SQL
        category = db.execute(
            text("""
                SELECT id, user_id, name FROM file_categories 
                WHERE id = :category_id AND user_id::text = :user_id
            """),
            {"category_id": str(category_id), "user_id": user_id_str}
        ).fetchone()

        if not category:
            raise HTTPException(
                status_code=404,
                detail="Category not found or not owned by user"
            )

        # System categories cannot be deleted (user_id is null)
        if category.user_id is None:
            raise HTTPException(
                status_code=403,
                detail="Cannot delete system categories"
            )

        # Delete using raw SQL
        db.execute(
            text("DELETE FROM file_categories WHERE id = :category_id"),
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

