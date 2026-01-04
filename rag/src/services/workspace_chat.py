"""
Workspace Chat Service
Implements context-aware AI chat with color-filtered highlights.
The "Killer Feature": Use specific highlight colors as exclusive AI context.
"""
import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from ..models import (
    WorkspaceDocument,
    DocumentSection,
    UserHighlight,
)

logger = logging.getLogger(__name__)

# Color definitions for UI consistency
HIGHLIGHT_COLORS = {
    'red': {'name': 'Red', 'hex': '#ef4444', 'description': 'Important / Critical'},
    'orange': {'name': 'Orange', 'hex': '#f97316', 'description': 'Questions / Unclear'},
    'yellow': {'name': 'Yellow', 'hex': '#eab308', 'description': 'Key Concepts'},
    'green': {'name': 'Green', 'hex': '#22c55e', 'description': 'Understood / Good'},
    'blue': {'name': 'Blue', 'hex': '#3b82f6', 'description': 'Definitions'},
    'purple': {'name': 'Purple', 'hex': '#a855f7', 'description': 'Examples'},
}


class WorkspaceChatService:
    """
    Service for context-aware AI chat in Workspace.

    Supports two modes:
    1. Standard RAG: When no color filter is applied, uses ChromaDB vector search
    2. Color-filtered: When colors are specified, uses SQL to fetch only
       highlighted text of those colors as context (bypasses ChromaDB)
    """

    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id

    async def get_context_for_query(
        self,
        query: str,
        document_id: Optional[UUID] = None,
        filter_colors: Optional[List[str]] = None,
        max_context_length: int = 8000
    ) -> Dict[str, Any]:
        """
        Get context for AI query based on filter mode.

        Args:
            query: User's question
            document_id: Optional specific document to query
            filter_colors: List of color codes to filter by (e.g., ['red', 'yellow'])
                          If None or empty, uses standard RAG
            max_context_length: Maximum characters for context

        Returns:
            Dict with:
                - context_text: Combined context string
                - context_source: 'highlights' or 'rag'
                - highlights_used: List of highlight metadata (if color-filtered)
                - documents_searched: List of document IDs searched
        """

        if filter_colors and len(filter_colors) > 0:
            # COLOR-FILTERED MODE: Get only highlights of specified colors
            logger.info(f"Using color-filtered context: {filter_colors}")
            return await self._get_highlights_context(
                document_id=document_id,
                colors=filter_colors,
                max_length=max_context_length
            )
        else:
            # STANDARD RAG MODE: Use ChromaDB vector search
            logger.info("Using standard RAG context")
            return await self._get_rag_context(
                query=query,
                document_id=document_id,
                max_length=max_context_length
            )

    async def _get_highlights_context(
        self,
        document_id: Optional[UUID],
        colors: List[str],
        max_length: int
    ) -> Dict[str, Any]:
        """
        Fetch highlighted text by color from SQL.
        This is the "Killer Feature" - precise context control.
        """

        # Build query for highlights
        query = select(
            UserHighlight,
            DocumentSection.content_text,
            WorkspaceDocument.title
        ).join(
            DocumentSection,
            UserHighlight.section_id == DocumentSection.id
        ).join(
            WorkspaceDocument,
            UserHighlight.document_id == WorkspaceDocument.id
        ).where(
            and_(
                WorkspaceDocument.user_id == self.user_id,
                UserHighlight.color_code.in_(colors)
            )
        )

        # Filter by specific document if provided
        if document_id:
            query = query.where(UserHighlight.document_id == document_id)

        # Order by document and position for logical flow
        query = query.order_by(
            WorkspaceDocument.title,
            DocumentSection.section_index,
            UserHighlight.start_offset
        )

        result = self.db.execute(query).all()

        if not result:
            return {
                'context_text': "",
                'context_source': 'highlights',
                'highlights_used': [],
                'documents_searched': [],
                'message': f"No highlights found with colors: {colors}"
            }

        # Build context from highlights
        context_parts = []
        highlights_used = []
        documents_searched = set()
        current_length = 0

        current_doc = None

        for highlight, section_text, doc_title in result:
            # Extract the highlighted text
            highlighted_text = section_text[highlight.start_offset:highlight.end_offset]

            # Check if we need to add document header
            if doc_title != current_doc:
                current_doc = doc_title
                header = f"\n\n--- From: {doc_title} ---\n"
                if current_length + len(header) > max_length:
                    break
                context_parts.append(header)
                current_length += len(header)

            # Check length limit
            if current_length + len(highlighted_text) + 10 > max_length:
                # Try to fit at least part of it
                remaining = max_length - current_length - 10
                if remaining > 50:
                    highlighted_text = highlighted_text[:remaining] + "..."
                else:
                    break

            # Add highlight to context
            context_parts.append(f"[{highlight.color_code.upper()}] {highlighted_text}\n")
            current_length += len(highlighted_text) + 15

            documents_searched.add(str(highlight.document_id))
            highlights_used.append({
                'id': str(highlight.id),
                'color': highlight.color_code,
                'text_preview': highlighted_text[:100] + "..." if len(highlighted_text) > 100 else highlighted_text,
                'annotation': highlight.annotation_text,
                'document_title': doc_title
            })

        context_text = "".join(context_parts)

        return {
            'context_text': context_text,
            'context_source': 'highlights',
            'highlights_used': highlights_used,
            'documents_searched': list(documents_searched),
            'colors_filtered': colors,
            'total_highlights': len(highlights_used)
        }

    async def _get_rag_context(
        self,
        query: str,
        document_id: Optional[UUID],
        max_length: int
    ) -> Dict[str, Any]:
        """
        Use standard RAG with ChromaDB for context retrieval.
        """
        try:
            # Search using existing vector store
            results = await search_documents_by_user(
                query=query,
                user_id=self.user_id,
                n_results=5
            )

            if not results:
                return {
                    'context_text': "",
                    'context_source': 'rag',
                    'highlights_used': [],
                    'documents_searched': [],
                    'message': "No relevant documents found"
                }

            # Build context from RAG results
            context_parts = []
            documents_searched = set()
            current_length = 0

            for result in results:
                text = result.get('content', result.get('text', ''))
                metadata = result.get('metadata', {})
                doc_name = metadata.get('file_name', 'Unknown')

                # Check length
                if current_length + len(text) + 50 > max_length:
                    remaining = max_length - current_length - 50
                    if remaining > 100:
                        text = text[:remaining] + "..."
                    else:
                        break

                context_parts.append(f"[From: {doc_name}]\n{text}\n\n")
                current_length += len(text) + len(doc_name) + 20

                if 'document_id' in metadata:
                    documents_searched.add(metadata['document_id'])

            context_text = "".join(context_parts)

            return {
                'context_text': context_text,
                'context_source': 'rag',
                'highlights_used': [],
                'documents_searched': list(documents_searched),
                'rag_results_count': len(results)
            }

        except Exception as e:
            logger.error(f"RAG search error: {e}")
            return {
                'context_text': "",
                'context_source': 'rag',
                'highlights_used': [],
                'documents_searched': [],
                'error': str(e)
            }

    def get_available_colors(self) -> Dict[str, Any]:
        """
        Return available highlight colors with metadata.
        """
        return HIGHLIGHT_COLORS

    async def get_document_highlight_summary(
        self,
        document_id: UUID
    ) -> Dict[str, Any]:
        """
        Get summary of highlights in a document by color.
        Useful for showing color chips in the UI.
        """
        from sqlalchemy import func

        query = select(
            UserHighlight.color_code,
            func.count(UserHighlight.id).label('count')
        ).join(
            WorkspaceDocument,
            UserHighlight.document_id == WorkspaceDocument.id
        ).where(
            and_(
                UserHighlight.document_id == document_id,
                WorkspaceDocument.user_id == self.user_id
            )
        ).group_by(UserHighlight.color_code)

        result = self.db.execute(query).all()

        summary = {
            'document_id': str(document_id),
            'colors': {}
        }

        for color_code, count in result:
            if color_code in HIGHLIGHT_COLORS:
                summary['colors'][color_code] = {
                    **HIGHLIGHT_COLORS[color_code],
                    'count': count
                }

        return summary


async def search_documents_by_user(query: str, user_id: str, n_results: int = 5) -> List[Dict]:
    """
    Helper function to search documents using existing vector store.
    This integrates with the existing RAG system.
    """
    from ..search_engine import search_and_rerank

    try:
        results = search_and_rerank(
            query=query,
            user_id=user_id,
            n_results=n_results
        )
        return results or []
    except Exception as e:
        logger.error(f"Vector search error: {e}")
        return []

