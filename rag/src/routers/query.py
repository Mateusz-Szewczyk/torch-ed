import os
import logging
import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..schemas import QueryRequest
from ..dependencies import get_db
from ..auth import get_current_user
from ..models import User
from ..agent.agent import ChatAgent

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

    If selected_tools are provided, they will be executed in the specified order.
    Returns chunks of the answer as they are generated for a real-time typing effect.

    Each event is formatted as:
    data: {"chunk": "text content", "done": false}

    Final event:
    data: {"chunk": "", "done": true}
    """
    user_id = current_user.id_
    query = request.query
    conversation_id = request.conversation_id
    selected_tools = request.selected_tools

    logger.info(f"[STREAM] Received query from user_id: {user_id} - '{query}', selected_tools: {selected_tools}")

    async def generate_stream():
        """Generator function that yields SSE-formatted chunks"""
        try:
            agent = ChatAgent(
                user_id=str(user_id),
                conversation_id=conversation_id,
                openai_api_key=OPENAI_API_KEY,
                tavily_api_key=TAVILY_API_KEY,
                db=db,
            )

            logger.info(f"[STREAM] Starting stream for user_id: {user_id}")

            # Stream chunks from agent
            async for msg in agent.invoke(query=query, selected_tool_names=selected_tools):
                # Send each chunk as SSE
                msg_type = msg.get("type", "chunk")

                # Buduj odpowiedź w zależności od typu eventu
                if msg_type == "action":
                    # Event z akcją nawigacji (wygenerowane fiszki/egzamin)
                    data = {
                        "type": "action",
                        "action_type": msg.get("action_type"),
                        "id": msg.get("id"),
                        "name": msg.get("name"),
                        "count": msg.get("count", 0),
                        "done": False
                    }
                elif msg_type == "step":
                    # Event z krokiem procesu
                    data = {
                        "type": "step",
                        "content": msg.get("content", ""),
                        "status": msg.get("status", "complete"),
                        "done": False
                    }
                elif msg_type == "chunk":
                    # Event z fragmentem tekstu odpowiedzi
                    data = {
                        "type": "chunk",
                        "content": msg.get("content", ""),
                        "done": False
                    }
                elif msg_type == "error":
                    # Event z błędem (np. limit subskrypcji)
                    data = {
                        "type": "error",
                        "error": msg.get("error", "Unknown error"),
                        "done": True
                    }
                else:
                    continue

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
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )
