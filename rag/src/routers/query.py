import os
import logging
import json
from uuid import UUID
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..schemas import QueryRequest
from ..dependencies import get_db
from ..auth import get_current_user
from ..models import User
from ..agent.agent import ChatAgent
from ..services.workspace_chat import WorkspaceChatService

router = APIRouter()
logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[logging.StreamHandler()]
)

ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
if not ANTHROPIC_API_KEY:
    raise ValueError("Anthropic API key is not set. Please set the ANTHROPIC_API_KEY environment variable.")

TAVILY_API_KEY = os.getenv('TAVILY_API_KEY')
if not TAVILY_API_KEY:
    raise ValueError("Tavily API key is not set. Please set the TAVILY_API_KEY environment variable.")

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    raise ValueError("OpenAI API key is not set. Please set the OPENAI_API_KEY environment variable.")


@router.post("/")
async def query_knowledge(
        request: QueryRequest,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    """
    Streaming endpoint that responds to user queries with Server-Sent Events (SSE).

    Supports two chat types:
    - "normal": Standard chat with optional RAG and tools
    - "workspace": Chat with document highlights as context (workspace_metadata required)

    For workspace chat, if filter_colors is provided in workspace_metadata,
    the system will use highlighted text of those colors as context instead of RAG.
    """
    user_id = current_user.id_
    query = request.query
    conversation_id = request.conversation_id
    selected_tools = request.selected_tools
    chat_type = request.chat_type
    workspace_metadata = request.workspace_metadata

    logger.info(f"[STREAM] Received query from user_id: {user_id} - '{query}', "
                f"selected_tools: {selected_tools}, chat_type: {chat_type}")

    async def generate_stream():
        """Generator function that yields SSE-formatted chunks"""
        try:
            # Handle workspace chat context
            workspace_context = None
            workspace_context_source = None

            if chat_type == "workspace" and workspace_metadata:
                # Get context from highlights if colors are specified
                if workspace_metadata.filter_colors and len(workspace_metadata.filter_colors) > 0:
                    logger.info(f"[WORKSPACE] Using color-filtered context: {workspace_metadata.filter_colors}")

                    # Emit step for context fetching
                    yield f"data: {json.dumps({'type': 'step', 'content': 'Pobieranie kontekstu z zaznaczonych fragmentów...', 'status': 'loading', 'done': False})}\n\n"

                    try:
                        workspace_service = WorkspaceChatService(db=db, user_id=user_id)
                        document_id = UUID(workspace_metadata.document_id) if workspace_metadata.document_id else None

                        context_result = await workspace_service.get_context_for_query(
                            query=query,
                            document_id=document_id,
                            filter_colors=workspace_metadata.filter_colors
                        )

                        if context_result.get('context_text'):
                            workspace_context = context_result['context_text']
                            workspace_context_source = f"zaznaczonych fragmentów ({', '.join(workspace_metadata.filter_colors)})"
                            logger.info(f"[WORKSPACE] Got {len(workspace_context)} chars from highlights")
                        else:
                            logger.info("[WORKSPACE] No highlights found for specified colors")

                        yield f"data: {json.dumps({'type': 'step', 'content': 'Pobieranie kontekstu z zaznaczonych fragmentów...', 'status': 'complete', 'done': False})}\n\n"

                    except Exception as e:
                        logger.error(f"[WORKSPACE] Error getting highlight context: {e}")
                        yield f"data: {json.dumps({'type': 'step', 'content': 'Pobieranie kontekstu z zaznaczonych fragmentów...', 'status': 'complete', 'done': False})}\n\n"

            agent = ChatAgent(
                user_id=str(user_id),
                conversation_id=conversation_id,
                openai_api_key=OPENAI_API_KEY,
                tavily_api_key=TAVILY_API_KEY,
                db=db,
                # Pass workspace context if available
                workspace_context=workspace_context,
                workspace_context_source=workspace_context_source,
            )

            logger.info(f"[STREAM] Starting stream for user_id: {user_id}")

            # Stream chunks from agent
            async for msg in agent.invoke(query=query, selected_tool_names=selected_tools):
                # Send each chunk as SSE
                msg_type = msg.get("type", "chunk")
                data = None

                # Build response based on event type
                if msg_type == "action":
                    action_type = msg.get("action_type")

                    if action_type == "set_conversation_title":
                        # Handle title update specifically
                        data = {
                            "type": "action",
                            "action_type": "set_conversation_title",
                            "name": msg.get("name"),
                            "done": False
                        }
                    else:
                        # Handle standard navigation actions (flashcards/exams)
                        data = {
                            "type": "action",
                            "action_type": action_type,
                            "id": msg.get("id"),
                            "name": msg.get("name"),
                            "count": msg.get("count", 0),
                            "done": False
                        }

                elif msg_type == "step":
                    # Process step event
                    data = {
                        "type": "step",
                        "content": msg.get("content", ""),
                        "status": msg.get("status", "complete"),
                        "done": False
                    }
                elif msg_type == "chunk":
                    # Text content chunk
                    data = {
                        "type": "chunk",
                        "content": msg.get("content", ""),
                        "done": False
                    }
                elif msg_type == "error":
                    # Error event
                    data = {
                        "type": "error",
                        "error": msg.get("error", "Unknown error"),
                        "done": True
                    }

                if data:
                    yield f"data: {json.dumps(data)}\n\n"

            # Send completion signal
            logger.info(f"[STREAM] Stream completed for user_id: {user_id}")
            yield f"data: {json.dumps({'type': 'done', 'content': '', 'done': True})}\n\n"

        except Exception as e:
            logger.error(f"[STREAM] Error during streaming for user_id: {user_id}, query '{query}': {e}", exc_info=True)
            # Send error as final event
            error_msg = f"Error generating answer: {str(e)}"
            yield f"data: {json.dumps({'error': error_msg, 'done': True})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )