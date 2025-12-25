# routers/memories.py
"""
Router for managing user memories (long-term memory storage).
Allows users to view, add, search, and delete their memories.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from ..auth import get_current_user
from ..models import User
from ..vector_store import (
    add_user_memory,
    search_user_memories,
    delete_all_user_memories,
    memory_client
)

import logging

router = APIRouter()
logger = logging.getLogger(__name__)


# ================== Pydantic Schemas ==================

class MemoryCreate(BaseModel):
    """Schema for creating a new memory."""
    text: str = Field(..., min_length=1, max_length=2000, description="The memory text to store")
    importance: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Importance level from 0.0 to 1.0"
    )


class MemoryRead(BaseModel):
    """Schema for reading a memory."""
    id: str
    text: str
    importance: float
    created_at: str
    last_accessed: Optional[str] = None


class MemorySearchRequest(BaseModel):
    """Schema for searching memories."""
    query: str = Field(..., min_length=1, description="Search query")
    n_results: int = Field(default=5, ge=1, le=20, description="Number of results to return")
    min_importance: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum importance filter")


class MemorySearchResult(BaseModel):
    """Schema for search results."""
    memories: List[str]
    count: int


class MemoryListResponse(BaseModel):
    """Schema for listing all memories."""
    memories: List[MemoryRead]
    total_count: int


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str
    success: bool = True


# ================== Endpoints ==================

@router.get("/", response_model=MemoryListResponse)
async def list_memories(
    limit: int = Query(default=50, ge=1, le=100, description="Maximum number of memories to return"),
    current_user: User = Depends(get_current_user),
):
    """
    List all memories for the current user.
    Returns memories sorted by creation date (newest first).
    """
    user_id = str(current_user.id_)
    logger.info(f"Listing memories for user_id: {user_id}")

    try:
        # Get all memories from ChromaDB for this user
        results = memory_client.get(
            where={"user_id": user_id},
            limit=limit,
            include=["documents", "metadatas"]
        )

        memories = []
        if results and results.get("ids"):
            for i, doc_id in enumerate(results["ids"]):
                metadata = results["metadatas"][i] if results.get("metadatas") else {}
                text = results["documents"][i] if results.get("documents") else ""

                memories.append(MemoryRead(
                    id=doc_id,
                    text=text,
                    importance=metadata.get("importance", 0.5),
                    created_at=metadata.get("created_at", ""),
                    last_accessed=metadata.get("last_accessed")
                ))

        # Sort by created_at (newest first)
        memories.sort(key=lambda x: x.created_at, reverse=True)

        return MemoryListResponse(
            memories=memories[:limit],
            total_count=len(memories)
        )

    except Exception as e:
        logger.error(f"Error listing memories: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving memories: {str(e)}")


@router.post("/", response_model=MemoryRead)
async def create_memory(
    memory: MemoryCreate,
    current_user: User = Depends(get_current_user),
):
    """
    Create a new memory for the current user.
    Memories are stored as vector embeddings for semantic search.
    """
    user_id = str(current_user.id_)
    logger.info(f"Creating memory for user_id: {user_id}, text: '{memory.text[:50]}...'")

    try:
        doc_id = add_user_memory(
            user_id=user_id,
            text=memory.text,
            importance=memory.importance
        )

        if not doc_id:
            raise HTTPException(status_code=500, detail="Failed to create memory")

        return MemoryRead(
            id=doc_id,
            text=memory.text,
            importance=memory.importance,
            created_at=datetime.now().isoformat(),
            last_accessed=None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating memory: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating memory: {str(e)}")


@router.post("/search", response_model=MemorySearchResult)
async def search_memories(
    request: MemorySearchRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Search memories using semantic similarity.
    Returns memories that are semantically similar to the query.
    """
    user_id = str(current_user.id_)
    logger.info(f"Searching memories for user_id: {user_id}, query: '{request.query}'")

    try:
        memories = search_user_memories(
            query=request.query,
            user_id=user_id,
            n_results=request.n_results,
            min_importance=request.min_importance
        )

        return MemorySearchResult(
            memories=memories,
            count=len(memories)
        )

    except Exception as e:
        logger.error(f"Error searching memories: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error searching memories: {str(e)}")


@router.delete("/{memory_id}", response_model=MessageResponse)
async def delete_memory(
    memory_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Delete a specific memory by its ID.
    Only the owner can delete their memories.
    """
    user_id = str(current_user.id_)
    logger.info(f"Deleting memory {memory_id} for user_id: {user_id}")

    try:
        # Verify the memory belongs to the user before deleting
        results = memory_client.get(
            ids=[memory_id],
            include=["metadatas"]
        )

        if not results or not results.get("ids"):
            raise HTTPException(status_code=404, detail="Memory not found")

        metadata = results["metadatas"][0] if results.get("metadatas") else {}
        if metadata.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this memory")

        # Delete the memory
        memory_client.delete(ids=[memory_id])

        return MessageResponse(
            message=f"Memory {memory_id} deleted successfully",
            success=True
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting memory: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting memory: {str(e)}")


@router.delete("/", response_model=MessageResponse)
async def delete_all_memories(
    current_user: User = Depends(get_current_user),
):
    """
    Delete all memories for the current user.
    This action is irreversible!
    """
    user_id = str(current_user.id_)
    logger.info(f"Deleting all memories for user_id: {user_id}")

    try:
        success = delete_all_user_memories(user_id)

        if success:
            return MessageResponse(
                message="All memories deleted successfully",
                success=True
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to delete memories")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting all memories: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting memories: {str(e)}")


@router.get("/stats", response_model=dict)
async def get_memory_stats(
    current_user: User = Depends(get_current_user),
):
    """
    Get statistics about user's memories.
    Returns count and importance distribution.
    """
    user_id = str(current_user.id_)
    logger.info(f"Getting memory stats for user_id: {user_id}")

    try:
        results = memory_client.get(
            where={"user_id": user_id},
            include=["metadatas"]
        )

        total_count = len(results.get("ids", []))

        # Calculate importance distribution
        importance_sum = 0.0
        high_importance = 0  # >= 0.7
        medium_importance = 0  # 0.3 - 0.7
        low_importance = 0  # < 0.3

        if results.get("metadatas"):
            for metadata in results["metadatas"]:
                imp = metadata.get("importance", 0.5)
                importance_sum += imp
                if imp >= 0.7:
                    high_importance += 1
                elif imp >= 0.3:
                    medium_importance += 1
                else:
                    low_importance += 1

        avg_importance = importance_sum / total_count if total_count > 0 else 0.0

        return {
            "total_memories": total_count,
            "average_importance": round(avg_importance, 2),
            "importance_distribution": {
                "high": high_importance,
                "medium": medium_importance,
                "low": low_importance
            }
        }

    except Exception as e:
        logger.error(f"Error getting memory stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting stats: {str(e)}")

