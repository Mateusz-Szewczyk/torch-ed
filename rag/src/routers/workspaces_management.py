"""
Router for Workspaces Management
Workspaces organize work by filtering documents based on selected categories.
"""
import logging
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..dependencies import get_db
from ..models import (
    User,
    Workspace,
    WorkspaceCategory,
    FileCategory,
    WorkspaceDocument,
    Conversation
)
from ..auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


# =============================================================================
# PYDANTIC SCHEMAS
# =============================================================================

class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category_ids: List[UUID] = Field(default_factory=list, description="List of category IDs to filter documents")


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    category_ids: Optional[List[UUID]] = None


class CategoryBrief(BaseModel):
    id: UUID
    name: str

    class Config:
        from_attributes = True


class WorkspaceRead(BaseModel):
    id: UUID
    user_id: int
    name: str
    description: Optional[str] = None
    categories: List[CategoryBrief] = []
    document_count: int = 0
    conversation_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentBrief(BaseModel):
    id: UUID
    title: str
    file_type: Optional[str] = None
    category_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/", response_model=WorkspaceRead, status_code=201)
async def create_workspace(
    workspace_data: WorkspaceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new workspace with selected categories.
    """
    try:
        # Validate categories exist and belong to user or are system categories
        if workspace_data.category_ids:
            categories = db.query(FileCategory).filter(
                FileCategory.id.in_(workspace_data.category_ids)
            ).all()

            # Check if all categories are accessible
            for cat in categories:
                if cat.user_id is not None and cat.user_id != current_user.id_:
                    raise HTTPException(
                        status_code=403,
                        detail=f"Category '{cat.name}' is not accessible"
                    )

            if len(categories) != len(workspace_data.category_ids):
                raise HTTPException(
                    status_code=400,
                    detail="Some categories not found"
                )

        # Create workspace
        new_workspace = Workspace(
            user_id=current_user.id_,
            name=workspace_data.name,
            description=workspace_data.description
        )

        db.add(new_workspace)
        db.flush()

        # Add category associations
        for category_id in workspace_data.category_ids:
            workspace_cat = WorkspaceCategory(
                workspace_id=new_workspace.id,
                category_id=category_id
            )
            db.add(workspace_cat)

        db.commit()
        db.refresh(new_workspace)

        # Get categories for response
        categories = db.query(FileCategory).join(
            WorkspaceCategory,
            WorkspaceCategory.category_id == FileCategory.id
        ).filter(
            WorkspaceCategory.workspace_id == new_workspace.id
        ).all()

        # Count documents in this workspace
        doc_count = _count_workspace_documents(db, new_workspace.id, current_user.id_)

        logger.info(f"Created workspace '{workspace_data.name}' for user {current_user.id_}")

        return WorkspaceRead(
            id=new_workspace.id,
            user_id=new_workspace.user_id,
            name=new_workspace.name,
            description=new_workspace.description,
            categories=[CategoryBrief(id=c.id, name=c.name) for c in categories],
            document_count=doc_count,
            conversation_count=0,
            created_at=new_workspace.created_at,
            updated_at=new_workspace.updated_at
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating workspace: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating workspace: {str(e)}")


@router.get("/", response_model=List[WorkspaceRead])
async def get_workspaces(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all workspaces for the current user.
    """
    try:
        workspaces = db.query(Workspace).filter(
            Workspace.user_id == current_user.id_
        ).order_by(Workspace.updated_at.desc()).all()

        result = []
        for workspace in workspaces:
            # Get categories
            categories = db.query(FileCategory).join(
                WorkspaceCategory,
                WorkspaceCategory.category_id == FileCategory.id
            ).filter(
                WorkspaceCategory.workspace_id == workspace.id
            ).all()

            # Count documents
            doc_count = _count_workspace_documents(db, workspace.id, current_user.id_)

            # Count conversations
            conv_count = db.query(Conversation).filter(
                Conversation.workspace_id == workspace.id
            ).count()

            result.append(WorkspaceRead(
                id=workspace.id,
                user_id=workspace.user_id,
                name=workspace.name,
                description=workspace.description,
                categories=[CategoryBrief(id=c.id, name=c.name) for c in categories],
                document_count=doc_count,
                conversation_count=conv_count,
                created_at=workspace.created_at,
                updated_at=workspace.updated_at
            ))

        logger.info(f"Fetched {len(result)} workspaces for user {current_user.id_}")
        return result

    except Exception as e:
        logger.error(f"Error fetching workspaces: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching workspaces: {str(e)}")


@router.get("/{workspace_id}", response_model=WorkspaceRead)
async def get_workspace(
    workspace_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific workspace.
    """
    try:
        workspace = db.query(Workspace).filter(
            and_(
                Workspace.id == workspace_id,
                Workspace.user_id == current_user.id_
            )
        ).first()

        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")

        # Get categories
        categories = db.query(FileCategory).join(
            WorkspaceCategory,
            WorkspaceCategory.category_id == FileCategory.id
        ).filter(
            WorkspaceCategory.workspace_id == workspace.id
        ).all()

        # Count documents
        doc_count = _count_workspace_documents(db, workspace.id, current_user.id_)

        # Count conversations
        conv_count = db.query(Conversation).filter(
            Conversation.workspace_id == workspace.id
        ).count()

        return WorkspaceRead(
            id=workspace.id,
            user_id=workspace.user_id,
            name=workspace.name,
            description=workspace.description,
            categories=[CategoryBrief(id=c.id, name=c.name) for c in categories],
            document_count=doc_count,
            conversation_count=conv_count,
            created_at=workspace.created_at,
            updated_at=workspace.updated_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching workspace: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching workspace: {str(e)}")


@router.get("/{workspace_id}/documents", response_model=List[DocumentBrief])
async def get_workspace_documents(
    workspace_id: UUID,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get filtered documents for a workspace.
    CRITICAL: Returns only documents whose category_id is in the Workspace's associated categories.
    """
    try:
        # Verify workspace ownership
        workspace = db.query(Workspace).filter(
            and_(
                Workspace.id == workspace_id,
                Workspace.user_id == current_user.id_
            )
        ).first()

        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")

        # Get workspace category IDs
        category_ids = db.query(WorkspaceCategory.category_id).filter(
            WorkspaceCategory.workspace_id == workspace_id
        ).all()
        category_ids = [cat_id for (cat_id,) in category_ids]

        logger.info(f"[WORKSPACE FILTER] Workspace {workspace_id} has category_ids: {category_ids}")

        # Debug: Check all user documents regardless of category
        all_user_docs = db.query(WorkspaceDocument).filter(
            WorkspaceDocument.user_id == current_user.id_
        ).all()
        logger.info(f"[WORKSPACE FILTER] User {current_user.id_} has {len(all_user_docs)} total documents:")
        for doc in all_user_docs:
            logger.info(f"  - Document: id={doc.id}, title={doc.title}, category_id={doc.category_id}, type={type(doc.category_id)}")
            if category_ids:
                logger.info(f"    Category match check: {doc.category_id} in {category_ids} = {doc.category_id in category_ids}")

        if not category_ids:
            # No categories selected = no documents visible
            logger.info(f"[WORKSPACE FILTER] No categories in workspace {workspace_id}, returning empty list")
            return []

        # Query documents filtered by categories
        documents = db.query(WorkspaceDocument).filter(
            and_(
                WorkspaceDocument.user_id == current_user.id_,
                WorkspaceDocument.category_id.in_(category_ids)
            )
        ).order_by(
            WorkspaceDocument.updated_at.desc()
        ).offset(skip).limit(limit).all()

        logger.info(f"[WORKSPACE FILTER] Query returned {len(documents)} documents after filtering")

        # Debug: Check all user documents regardless of category
        all_user_docs = db.query(WorkspaceDocument).filter(
            WorkspaceDocument.user_id == current_user.id_
        ).all()
        logger.info(f"User {current_user.id_} has {len(all_user_docs)} total documents")
        for doc in all_user_docs:
            logger.info(f"  Document: id={doc.id}, title={doc.title}, category_id={doc.category_id}")

        result = [
            DocumentBrief(
                id=doc.id,
                title=doc.title,
                file_type=doc.file_type,
                category_name=doc.category.name if doc.category else None,
                created_at=doc.created_at
            )
            for doc in documents
        ]

        logger.info(f"Fetched {len(result)} documents for workspace {workspace_id}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching workspace documents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching workspace documents: {str(e)}")


@router.put("/{workspace_id}", response_model=WorkspaceRead)
async def update_workspace(
    workspace_id: UUID,
    workspace_data: WorkspaceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update workspace name, description, or categories.
    """
    try:
        workspace = db.query(Workspace).filter(
            and_(
                Workspace.id == workspace_id,
                Workspace.user_id == current_user.id_
            )
        ).first()

        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")

        # Update basic fields
        if workspace_data.name is not None:
            workspace.name = workspace_data.name
        if workspace_data.description is not None:
            workspace.description = workspace_data.description

        # Update categories if provided
        if workspace_data.category_ids is not None:
            # Validate categories
            if workspace_data.category_ids:
                categories = db.query(FileCategory).filter(
                    FileCategory.id.in_(workspace_data.category_ids)
                ).all()

                for cat in categories:
                    if cat.user_id is not None and cat.user_id != current_user.id_:
                        raise HTTPException(
                            status_code=403,
                            detail=f"Category '{cat.name}' is not accessible"
                        )

            # Remove old associations
            db.query(WorkspaceCategory).filter(
                WorkspaceCategory.workspace_id == workspace_id
            ).delete()

            # Add new associations
            for category_id in workspace_data.category_ids:
                workspace_cat = WorkspaceCategory(
                    workspace_id=workspace_id,
                    category_id=category_id
                )
                db.add(workspace_cat)

        db.commit()
        db.refresh(workspace)

        # Get categories for response
        categories = db.query(FileCategory).join(
            WorkspaceCategory,
            WorkspaceCategory.category_id == FileCategory.id
        ).filter(
            WorkspaceCategory.workspace_id == workspace.id
        ).all()

        # Count documents
        doc_count = _count_workspace_documents(db, workspace.id, current_user.id_)

        # Count conversations
        conv_count = db.query(Conversation).filter(
            Conversation.workspace_id == workspace.id
        ).count()

        logger.info(f"Updated workspace {workspace_id}")

        return WorkspaceRead(
            id=workspace.id,
            user_id=workspace.user_id,
            name=workspace.name,
            description=workspace.description,
            categories=[CategoryBrief(id=c.id, name=c.name) for c in categories],
            document_count=doc_count,
            conversation_count=conv_count,
            created_at=workspace.created_at,
            updated_at=workspace.updated_at
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating workspace: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error updating workspace: {str(e)}")


@router.delete("/{workspace_id}", status_code=204)
async def delete_workspace(
    workspace_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a workspace.
    Strategy: CASCADE delete conversations (set in FK), but documents remain (filtered by category).
    """
    try:
        workspace = db.query(Workspace).filter(
            and_(
                Workspace.id == workspace_id,
                Workspace.user_id == current_user.id_
            )
        ).first()

        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")

        db.delete(workspace)
        db.commit()

        logger.info(f"Deleted workspace {workspace_id}")
        return None

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting workspace: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting workspace: {str(e)}")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _count_workspace_documents(db: Session, workspace_id: UUID, user_id: int) -> int:
    """Count documents in a workspace based on category filtering."""
    # Get workspace category IDs
    category_ids = db.query(WorkspaceCategory.category_id).filter(
        WorkspaceCategory.workspace_id == workspace_id
    ).all()
    category_ids = [cat_id for (cat_id,) in category_ids]

    if not category_ids:
        return 0

    # Count documents with matching categories
    return db.query(WorkspaceDocument).filter(
        and_(
            WorkspaceDocument.user_id == user_id,
            WorkspaceDocument.category_id.in_(category_ids)
        )
    ).count()

