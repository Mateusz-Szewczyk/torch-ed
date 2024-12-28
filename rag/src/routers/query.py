# src/routers/query.py

from fastapi import APIRouter, HTTPException, Depends, Form
from ..schemas import QueryResponse, QueryRequest
from ..dependencies import get_db

from ..agent.agent import agent_response

import os
import logging
import asyncio

router = APIRouter()
logger = logging.getLogger(__name__)

# Configure logging format (optional but recommended)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# Load API keys
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
async def query_knowledge(request: QueryRequest):
    user_id = request.user_id
    query = request.query
    conversation_id = request.conversation_id

    logger.info(f"Received query from user_id: {user_id} - '{query}'")

    try:
        # Generate response
        answer = await asyncio.to_thread(
            agent_response,
            user_id,
            query,
            conversation_id=conversation_id,
            model_name="claude-3-haiku-20240307",
            anthropic_api_key=ANTHROPIC_API_KEY,
            tavily_api_key=TAVILY_API_KEY
        )
        logger.info(f"Generated answer for user_id: {user_id} with query: '{query}'")
        return QueryResponse(
            user_id=user_id,
            query=query,
            answer=answer
        )
    except Exception as e:
        logger.error(f"Error generating answer for user_id: {user_id}, query '{query}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating answer: {str(e)}")
