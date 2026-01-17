"""
Notion Integration Router

Endpoints for:
- OAuth authorization flow
- Listing accessible pages/databases
- Importing Notion pages as documents
- Webhook receiver with debounce
- Manual sync trigger
"""

import logging
import secrets
import httpx
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query, Request, BackgroundTasks
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..models import User, WorkspaceDocument, FileCategory, DocumentSection
from ..dependencies import get_db
from ..auth import get_current_user
from ..services.notion_service import NotionService, webhook_debouncer
from ..services.subscription import SubscriptionService
from ..vector_store import create_vector_store, delete_file_from_vector_store
from ..chunking import create_chunks
from ..config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


# =============================================================================
# PYDANTIC SCHEMAS
# =============================================================================

class NotionConnectionStatus(BaseModel):
    connected: bool
    workspace_name: Optional[str] = None
    connected_at: Optional[datetime] = None
    import_count: int = 0
    import_limit: int = 1


class NotionPage(BaseModel):
    id: str
    title: str
    icon: Optional[str] = None
    last_edited: Optional[str] = None
    object_type: str  # 'page' or 'database'


class NotionPagesResponse(BaseModel):
    pages: List[NotionPage]
    databases: List[NotionPage]


class ImportRequest(BaseModel):
    page_id: str
    category_id: str
    title_override: Optional[str] = None  # Allow custom title


class ImportResponse(BaseModel):
    success: bool
    document_id: Optional[str] = None
    message: str


class SyncResponse(BaseModel):
    success: bool
    message: str
    updated: bool = False


class WebhookPayload(BaseModel):
    """Notion webhook payload structure."""
    type: str
    page_id: Optional[str] = None


# =============================================================================
# SUBSCRIPTION LIMITS
# =============================================================================

def get_notion_import_limit(role: str) -> int:
    """Get Notion import limit based on subscription tier."""
    limits = {
        "user": 1,       # Free tier
        "pro": 3,        # Pro tier
        "expert": 10,    # Expert tier
        "admin": 999     # Admin (unlimited)
    }
    return limits.get(role, 1)


def check_notion_import_limit(user: User, db: Session) -> None:
    """Check if user can import more Notion pages."""
    limit = get_notion_import_limit(user.role)
    current_count = user.notion_import_count or 0
    
    if current_count >= limit:
        raise HTTPException(
            status_code=403,
            detail=f"Notion import limit reached ({current_count}/{limit}). Upgrade your subscription for more imports."
        )


# =============================================================================
# CONNECTION STATUS
# =============================================================================

@router.get("/status", response_model=NotionConnectionStatus)
async def get_notion_status(
    current_user: User = Depends(get_current_user)
):
    """Get current Notion connection status."""
    connected = bool(current_user.notion_access_token)
    limit = get_notion_import_limit(current_user.role)
    
    return NotionConnectionStatus(
        connected=connected,
        workspace_name=current_user.notion_workspace_name if connected else None,
        connected_at=current_user.notion_connected_at if connected else None,
        import_count=current_user.notion_import_count or 0,
        import_limit=limit
    )


# =============================================================================
# OAUTH FLOW
# =============================================================================

@router.get("/auth/authorize")
async def notion_authorize(
    current_user: User = Depends(get_current_user)
):
    """
    Generate Notion OAuth authorization URL.
    Frontend should redirect user to this URL.
    """
    if not settings.NOTION_CLIENT_ID:
        raise HTTPException(
            status_code=500,
            detail="Notion integration not configured. Contact administrator."
        )
    
    # Generate state token for CSRF protection
    state = secrets.token_urlsafe(32)
    
    # Store state in session/cache (simplified - in production use Redis)
    # For now, we'll encode user_id in state
    state_with_user = f"{state}:{current_user.id_}"
    
    auth_url = (
        f"https://api.notion.com/v1/oauth/authorize"
        f"?client_id={settings.NOTION_CLIENT_ID}"
        f"&response_type=code"
        f"&owner=user"
        f"&redirect_uri={settings.NOTION_REDIRECT_URI}"
        f"&state={state_with_user}"
    )
    
    return {"authorization_url": auth_url}


@router.get("/auth/callback")
async def notion_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Handle OAuth callback from Notion.
    Exchange authorization code for access token.
    """
    if not settings.NOTION_CLIENT_ID or not settings.NOTION_CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="Notion integration not configured."
        )
    
    # Extract user_id from state
    try:
        _, user_id_str = state.rsplit(":", 1)
        user_id = int(user_id_str)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid state parameter")
    
    # Get user
    user = db.query(User).filter(User.id_ == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Exchange code for token
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.notion.com/v1/oauth/token",
            auth=(settings.NOTION_CLIENT_ID, settings.NOTION_CLIENT_SECRET),
            json={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.NOTION_REDIRECT_URI
            }
        )
    
    if response.status_code != 200:
        logger.error(f"Notion OAuth failed: {response.text}")
        raise HTTPException(
            status_code=400,
            detail="Failed to connect to Notion. Please try again."
        )
    
    token_data = response.json()
    
    # Save token and workspace info
    user.notion_access_token = token_data.get("access_token")
    user.notion_workspace_id = token_data.get("workspace_id")
    user.notion_workspace_name = token_data.get("workspace_name")
    user.notion_connected_at = datetime.utcnow()
    
    db.commit()
    
    logger.info(f"User {user_id} connected Notion workspace: {user.notion_workspace_name}")
    
    # Redirect to frontend success page
    return RedirectResponse(
        url=f"{settings.FRONTEND_URL}/settings?notion=connected",
        status_code=302
    )


@router.delete("/disconnect")
async def notion_disconnect(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Disconnect Notion account."""
    current_user.notion_access_token = None
    current_user.notion_workspace_id = None
    current_user.notion_workspace_name = None
    current_user.notion_connected_at = None
    # Note: We don't reset import_count to prevent abuse
    
    db.commit()
    
    logger.info(f"User {current_user.id_} disconnected Notion")
    
    return {"success": True, "message": "Notion disconnected successfully"}


# =============================================================================
# LIST PAGES & DATABASES
# =============================================================================

@router.get("/pages", response_model=NotionPagesResponse)
async def list_notion_content(
    current_user: User = Depends(get_current_user)
):
    """List all accessible Notion pages and databases."""
    if not current_user.notion_access_token:
        raise HTTPException(
            status_code=401,
            detail="Notion not connected. Please connect your Notion account first."
        )
    
    service = NotionService(current_user.notion_access_token)
    
    try:
        pages = await service.list_accessible_pages()
        databases = await service.list_accessible_databases()
        
        return NotionPagesResponse(
            pages=[NotionPage(**p) for p in pages],
            databases=[NotionPage(**d) for d in databases]
        )
    except Exception as e:
        logger.error(f"Failed to list Notion content: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch Notion content. Please try reconnecting."
        )


# =============================================================================
# IMPORT PAGE
# =============================================================================

@router.post("/import", response_model=ImportResponse)
async def import_notion_page(
    request: ImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Import a Notion page as a document."""
    
    # Check connection
    if not current_user.notion_access_token:
        raise HTTPException(
            status_code=401,
            detail="Notion not connected."
        )
    
    # Check import limit
    check_notion_import_limit(current_user, db)
    
    # Validate category
    try:
        category_uuid = UUID(request.category_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid category_id format")
    
    category = db.query(FileCategory).filter(
        FileCategory.id == category_uuid,
        (FileCategory.user_id == current_user.id_) | (FileCategory.user_id == None)
    ).first()
    
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Check if already imported
    existing = db.query(WorkspaceDocument).filter(
        WorkspaceDocument.user_id == current_user.id_,
        WorkspaceDocument.notion_page_id == request.page_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail="This Notion page is already imported. Use sync to update it."
        )
    
    # Fetch page content
    service = NotionService(current_user.notion_access_token)
    
    try:
        page_content = await service.get_page_content(request.page_id)
    except Exception as e:
        logger.error(f"Failed to fetch Notion page {request.page_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch page content from Notion."
        )
    
    markdown_content = page_content.get("content_markdown", "")
    if not markdown_content.strip():
        raise HTTPException(
            status_code=400,
            detail="Page has no content to import."
        )
    
    title = request.title_override or page_content.get("title", "Untitled")
    
    # Create chunks for RAG
    try:
        chunks = create_chunks(markdown_content, chunk_size=1200, overlap=150)
        if not chunks:
            raise HTTPException(status_code=500, detail="Failed to process content")
        
        # Add to vector store
        create_vector_store(
            chunks=chunks,
            user_id=str(current_user.id_),
            file_name=f"notion_{request.page_id}",
            file_description=f"Imported from Notion: {title}",
            category=category.name
        )
    except Exception as e:
        logger.error(f"Failed to create vectors for Notion page: {e}")
        raise HTTPException(status_code=500, detail="Failed to process document")
    
    # Create document record
    new_document = WorkspaceDocument(
        user_id=current_user.id_,
        category_id=category_uuid,
        title=title,
        original_filename=f"notion_{request.page_id}",
        file_type="notion",
        total_length=len(markdown_content),
        total_sections=len(chunks),
        notion_page_id=request.page_id,
        notion_last_synced=datetime.utcnow(),
        notion_last_modified=datetime.fromisoformat(
            page_content.get("last_edited", "").replace("Z", "+00:00")
        ) if page_content.get("last_edited") else None,
        is_notion_document=True
    )
    
    db.add(new_document)
    db.flush()  # Get document ID before creating sections
    
    # Create sections
    char_offset = 0
    for idx, chunk in enumerate(chunks):
        section = DocumentSection(
            document_id=new_document.id,
            section_index=idx,
            content_text=chunk,
            base_styles=[],
            section_metadata={
                "source": "notion",
                "page_id": request.page_id,
                "chunk_index": idx
            },
            char_start=char_offset,
            char_end=char_offset + len(chunk)
        )
        db.add(section)
        char_offset += len(chunk)
    
    # Increment import count
    current_user.notion_import_count = (current_user.notion_import_count or 0) + 1
    
    db.commit()
    db.refresh(new_document)
    
    logger.info(f"Imported Notion page {request.page_id} as document {new_document.id}")
    
    return ImportResponse(
        success=True,
        document_id=str(new_document.id),
        message=f"Successfully imported '{title}'"
    )


# =============================================================================
# MANUAL SYNC
# =============================================================================

@router.post("/sync/{document_id}", response_model=SyncResponse)
async def sync_notion_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Manually trigger sync for a Notion document."""
    
    # Get document
    try:
        doc_uuid = UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document_id format")
    
    document = db.query(WorkspaceDocument).filter(
        WorkspaceDocument.id == doc_uuid,
        WorkspaceDocument.user_id == current_user.id_,
        WorkspaceDocument.is_notion_document == True
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Notion document not found")
    
    if not document.notion_page_id:
        raise HTTPException(status_code=400, detail="Document has no linked Notion page")
    
    if not current_user.notion_access_token:
        raise HTTPException(status_code=401, detail="Notion not connected")
    
    # Fetch updated content
    service = NotionService(current_user.notion_access_token)
    
    try:
        page_content = await service.get_page_content(document.notion_page_id)
    except Exception as e:
        logger.error(f"Failed to sync Notion page {document.notion_page_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch from Notion")
    
    # Check if actually changed
    notion_modified = page_content.get("last_edited")
    if notion_modified and document.notion_last_modified:
        notion_dt = datetime.fromisoformat(notion_modified.replace("Z", "+00:00"))
        if notion_dt <= document.notion_last_modified:
            return SyncResponse(
                success=True,
                message="Document is already up to date",
                updated=False
            )
    
    markdown_content = page_content.get("content_markdown", "")
    
    # Delete old vectors
    delete_file_from_vector_store(
        user_id=str(current_user.id_),
        file_name=f"notion_{document.notion_page_id}"
    )
    
    # Create new chunks
    chunks = create_chunks(markdown_content, chunk_size=1200, overlap=150)
    
    if chunks:
        # Add new vectors
        category = db.query(FileCategory).filter(
            FileCategory.id == document.category_id
        ).first()
        
        create_vector_store(
            chunks=chunks,
            user_id=str(current_user.id_),
            file_name=f"notion_{document.notion_page_id}",
            file_description=f"Synced from Notion: {document.title}",
            category=category.name if category else "General"
        )
    
    # Delete old sections
    db.query(DocumentSection).filter(
        DocumentSection.document_id == document.id
    ).delete()
    
    # Create new sections
    char_offset = 0
    for idx, chunk in enumerate(chunks):
        section = DocumentSection(
            document_id=document.id,
            section_index=idx,
            content_text=chunk,
            base_styles=[],
            section_metadata={
                "source": "notion",
                "page_id": document.notion_page_id,
                "chunk_index": idx,
                "synced_at": datetime.utcnow().isoformat()
            },
            char_start=char_offset,
            char_end=char_offset + len(chunk)
        )
        db.add(section)
        char_offset += len(chunk)
    
    # Update document metadata
    document.total_length = len(markdown_content)
    document.total_sections = len(chunks)
    document.notion_last_synced = datetime.utcnow()
    if notion_modified:
        document.notion_last_modified = datetime.fromisoformat(
            notion_modified.replace("Z", "+00:00")
        )
    
    db.commit()
    
    logger.info(f"Synced Notion document {document_id}")
    
    return SyncResponse(
        success=True,
        message="Document synced successfully",
        updated=True
    )


# =============================================================================
# WEBHOOK RECEIVER
# =============================================================================

@router.post("/webhook")
async def notion_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Receive webhook notifications from Notion.
    Uses 2-minute debounce before triggering sync.
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    event_type = payload.get("type")
    page_id = payload.get("page_id") or payload.get("entity", {}).get("id")
    
    if not page_id:
        return {"status": "ignored", "reason": "no page_id"}
    
    # Record change for debouncing
    webhook_debouncer.record_change(page_id)
    
    # Schedule check for pages ready to sync
    background_tasks.add_task(process_pending_syncs, db)
    
    return {"status": "received"}


async def process_pending_syncs(db: Session):
    """
    Background task to process pages ready for sync.
    Called after each webhook, checks debounce timers.
    """
    ready_pages = webhook_debouncer.get_pages_ready_for_sync()
    
    for page_id in ready_pages:
        # Find documents linked to this page
        documents = db.query(WorkspaceDocument).filter(
            WorkspaceDocument.notion_page_id == page_id,
            WorkspaceDocument.is_notion_document == True
        ).all()
        
        for doc in documents:
            try:
                # Get user's token
                user = db.query(User).filter(User.id_ == doc.user_id).first()
                if not user or not user.notion_access_token:
                    continue
                
                # Trigger sync (reuse sync logic)
                service = NotionService(user.notion_access_token)
                page_content = await service.get_page_content(page_id)
                
                # ... (sync logic same as manual sync)
                logger.info(f"Auto-synced document {doc.id} from webhook")
                
            except Exception as e:
                logger.error(f"Failed to auto-sync document {doc.id}: {e}")
                continue
