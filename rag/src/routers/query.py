import os
import logging
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from ..schemas import QueryResponse, QueryRequest
from ..dependencies import get_db
from ..auth import get_current_user  # Dekodowanie tokenu, zwraca obiekt User
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

@router.post("/", response_model=QueryResponse)
async def query_knowledge(
    request: QueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Odpowiada na zapytania użytkownika. Jeśli w request dodatkowo przesłano listę
    wybranych narzędzi (selected_tools), to zapytanie będzie przetwarzane przez nie w zadanej kolejności.
    Jeśli lista jest pusta, zostanie wywołana funkcja direct_response.
    """
    user_id = current_user.id_  # Dekodowane z tokenu
    query = request.query
    conversation_id = request.conversation_id
    selected_tools = request.selected_tools

    logger.info(f"Received query from user_id: {user_id} - '{query}', selected_tools: {selected_tools}")

    try:
        agent = ChatAgent(
            user_id=user_id,
            conversation_id=conversation_id,
            anthropic_api_key=ANTHROPIC_API_KEY,
            tavily_api_key=TAVILY_API_KEY,
            openai_api_key=OPENAI_API_KEY,
        )
        answer = await agent.invoke(
            selected_tool_names=selected_tools,
            query=query,
        )
        if not isinstance(answer, str):
            logger.error(f"agent_response returned non-string: {type(answer)}")
            raise ValueError(f"Expected string from agent_response, got {type(answer)}")
        logger.info(f"Generated answer for user_id: {user_id} with query: '{query}'")

        return QueryResponse(
            user_id=user_id,
            query=query,
            answer=answer
        )

    except Exception as e:
        logger.error(f"Error generating answer for user_id: {user_id}, query '{query}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating answer: {str(e)}")