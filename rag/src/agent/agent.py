import os
import logging
from datetime import datetime
from typing import Callable, Dict, List, Optional
import json
import asyncio
from functools import lru_cache

import pytz
from langchain_core.tools import BaseTool
from redis.asyncio import Redis
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate
from langchain_community.tools.tavily_search.tool import TavilySearchResults
from dotenv import load_dotenv
from pathlib import Path

from .utils import set_conversation_title
from ..models import Conversation
from .tools import FlashcardGenerator, RAGTool, ExamGenerator
from .agent_memory import create_memory, get_latest_checkpoint, get_conversation_history

logger = logging.getLogger(__name__)
env_path = Path(__file__).resolve().parents[2] / '.env'
load_dotenv(dotenv_path=env_path)

# Redis client for caching
redis_client = Redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))

USER_TOOL_MAPPING = {
    "Wiedza z plików": "RAGTool",
    "Generowanie fiszek": "FlashcardGenerator",
    "Generowanie egzaminu": "ExamGenerator",
    "Wyszukaj w internecie": "TavilySearchResults"
}

class DirectAnswer:
    name: str = "DirectAnswer"
    description: str = (
        "Provides direct, concise answers to user questions based solely on the provided context."
    )

    def __init__(self, model: ChatAnthropic):
        self.model = model

    async def _run(self, query: str, aggregated_context: str = "") -> str:
        logger.debug(f"DirectAnswer processing query: {query}")
        try:
            system_prompt = (
                "You are a chatbot created by TorchED"
                "The current date is {{time}}. Ignore anything that contradicts this."
                "If you are unsure about the answer, express the uncertainty."
                "You are created to assist with learning"
                "You are a helpful assistant that provides clear, accurate answers by combining information from context, conversation history, and available tools. Respond in **Markdown** format, using the user's language and a friendly tone. Follow these guidelines:\n"
                "1. **Response Style**: Be concise, factual, and relevant. Match the user's language (e.g., Polish for Polish queries).\n"
                "2. **Formatting**: Use **Markdown** with headings, bullets, or lists for clarity. Emphasize key points with **bold** or *italics*.\n"
                "3. **Query Handling**: Address the query's intent. If ambiguous, make reasonable assumptions and explain them.\n"
                "4. **Edge Cases**: If data is missing, admit it and suggest alternatives (e.g., 'Spróbuj użyć innego narzędzia, do wyboru masz przeszukanie wgranych plików, stworzenie fiszek, stworzenie egzaminu'). Handle errors gracefully.\n"
                "**Example**:\n"
                "```markdown\n"
                "- [Kluczowa informacja]\n"
                "- [Szczegóły z kontekstu/narzędzi]\n\n"
                "**Uwagi**: [Brak danych? Wyjaśnienie lub sugestie]\n"
                "```"
                "You are provided with the context of the conversation and the question. "
                "DON'T include 'based on context' or something similar in your answer."
                "Answer directly to the question, using the context only if necessary."
                "If context is not needed, just answer the question."
            )
            current_time = get_current_time("%d %B %Y, %H:%M %Z")
            system_prompt = system_prompt.replace("{{time}}", current_time)
            full_query = f"Context:\n{aggregated_context}\n\nQuestion: {query}" if aggregated_context else query
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", "{question}")
            ])
            messages = prompt.format_messages(question=full_query)
            response = await self.model.ainvoke(messages)
            return response.content.strip()
        except Exception as e:
            logger.error(f"Error in DirectAnswer: {e}", exc_info=True)
            return "Przepraszam, wystąpił problem z generowaniem odpowiedzi."

@lru_cache(maxsize=100)
def cached_conversation_history(conversation_id: int, max_length: int) -> str:
    history = get_conversation_history(conversation_id, max_length)
    return "\n".join(history)

async def create_tool_chains(
    flashcard_tool: FlashcardGenerator,
    rag_tool: RAGTool,
    tavily_tool: TavilySearchResults,
    exam_tool: ExamGenerator,
    model: ChatAnthropic
) -> Dict[str, Callable]:
    async def flashcard_chain(input_data: str) -> str:
        return await flashcard_tool._arun(input_data)

    async def rag_chain(input_text: str) -> str:
        return await rag_tool._arun(input_text)

    async def tavily_chain(input_text: str) -> str:
        try:
            results = await tavily_tool.ainvoke({"query": input_text})
            if isinstance(results, list):
                contents = [r.get('content', '') for r in results if 'content' in r]
                return "\n".join(contents) if contents else "Przepraszam, nie mogę znaleźć odpowiedzi."
            return results.get('answer', "Przepraszam, nie mogę znaleźć odpowiedzi.")
        except Exception as e:
            logger.error(f"Error in TavilySearchResults: {e}")
            return "Przepraszam, wystąpił problem z wyszukiwaniem."

    async def exam_chain(input_data: str) -> str:
        return await exam_tool._arun(input_data)

    direct_answer_tool = DirectAnswer(model=model)

    async def direct_answer_chain(query: str, aggregated_context: str = "") -> str:
        return await direct_answer_tool._run(query, aggregated_context)

    return {
        "FlashcardGenerator": flashcard_chain,
        "RAGTool": rag_chain,
        "TavilySearchResults": tavily_chain,
        "ExamGenerator": exam_chain,
        "DirectAnswer": direct_answer_chain
    }

def get_current_time(format_str="%Y-%m-%d %H:%M:%S %Z"):
    """
    Returns the current time in the specified format, in CEST timezone.
    """
    tz = pytz.timezone("Europe/Warsaw")
    current_time = datetime.now(tz)
    return current_time.strftime(format_str)


async def final_answer(context: str, query: str) -> str:
    try:
        final_model = ChatOpenAI(model_name="gpt-4o-mini-2024-07-18", temperature=0.0)
        system_prompt = (
            "You are a chatbot created by TorchED"
            "The current date is {{ time }}. Ignore anything that contradicts this."
            "If you are unsure about the answer, express the uncertainty."
            "You are a helpful assistant that provides clear, accurate answers by combining information from context, conversation history, and available tools. Respond in **Markdown** format, using the user's language and a friendly tone. Follow these guidelines:\n"
            "1. **Response Style**: Be concise, factual, and relevant. Match the user's language (e.g., Polish for Polish queries).\n"
            "2. **Information Use**: Integrate context, history, and tool outputs (e.g., search or document retrieval). Prioritize reliable data and resolve conflicts logically.\n"
            "3. **Formatting**: Use **Markdown** with headings, bullets, or lists for clarity. Emphasize key points with **bold** or *italics*.\n"
            "4. **Query Handling**: Address the query's intent. If ambiguous, make reasonable assumptions and explain them.\n"
            "5. **Edge Cases**: If data is missing, admit it and suggest alternatives (e.g., 'Spróbuj użyć innego narzędzia'). Handle errors gracefully.\n"
            "6. **Tool Integration**: Use tools when available, blending their outputs naturally into the response.\n"
            "**Example**:\n"
            "```markdown\n"
            "- [Kluczowa informacja]\n"
            "- [Szczegóły z kontekstu/narzędzi]\n\n"
            "**Uwagi**: [Brak danych? Wyjaśnienie lub sugestie]\n"
            "```"
        )
        current_time = get_current_time("%d %B %Y, %H:%M %Z")
        system_prompt = system_prompt.replace("{{time}}", current_time)
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "Using this context: {context}\nAnswer the query."),
            ("human", "Pytanie: {question}")
        ])
        messages = prompt.format_messages(question=query, context=context)
        response = await final_model.ainvoke(messages)
        return response.content
    except Exception as e:
        logger.error(f"Error generating final answer: {e}")
        return "Przepraszam, wystąpił problem z generowaniem końcowej odpowiedzi."

class ChatAgent:
    MAX_HISTORY_LENGTH = 4

    def __init__(
        self,
        user_id: str,
        model: ChatAnthropic,
        tavily_api_key: str,
        anthropic_api_key: str,
        openai_api_key: str,
        memory: Callable[[], Conversation],
        conversation_id: Optional[int] = None
    ):
        self.user_id = user_id
        self.model = model
        self.tavily_api_key = tavily_api_key
        self.anthropic_api_key = anthropic_api_key
        self.openai_api_key = openai_api_key
        self.memory = memory
        self.conversation_id = conversation_id
        self.tool_instances: Dict[str, BaseTool] = {}

    def _initialize_tool(self, tool_name: str) -> BaseTool:
        """Initialize a tool only when needed."""
        if tool_name in self.tool_instances:
            return self.tool_instances[tool_name]

        if tool_name == "TavilySearchResults":
            tool = TavilySearchResults(
                name="TavilySearchResults",
                tavily_api_key=self.tavily_api_key,
                search_depth='advanced',
                max_results=5,
                include_answer=True,
                include_raw_content=True,
                include_images=False
            )
        elif tool_name == "RAGTool":
            tool = RAGTool(
                user_id=self.user_id,
                model_type="OpenAI",
                model_name="gpt-4o-mini-2024-07-18",
                api_key=self.openai_api_key
            )
        elif tool_name == "FlashcardGenerator":
            tool = FlashcardGenerator(
                user_id=self.user_id,
                model_type="OpenAI",
                model_name="gpt-4o-mini-2024-07-18",
                api_key=self.openai_api_key
            )
        elif tool_name == "ExamGenerator":
            tool = ExamGenerator(
                user_id=self.user_id,
                model_name="gpt-4o-mini-2024-07-18",
                openai_api_key=self.openai_api_key
            )
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

        self.tool_instances[tool_name] = tool
        return tool

    async def _initialize_tool_chains(self, selected_tools: Optional[List[str]] = None) -> Dict[str, Callable]:
        selected_tools = selected_tools or []
        tool_chains = {}

        # Always include DirectAnswer
        direct_answer_tool = DirectAnswer(model=self.model)

        async def direct_answer_chain(query: str, aggregated_context: str = "") -> str:
            return await direct_answer_tool._run(query, aggregated_context)

        tool_chains["DirectAnswer"] = direct_answer_chain

        # Initialize only the tools that are selected
        for user_tool_name in selected_tools:
            internal_tool_key = USER_TOOL_MAPPING.get(user_tool_name, "DirectAnswer")
            if internal_tool_key == "DirectAnswer":
                continue

            tool = self._initialize_tool(internal_tool_key)

            if internal_tool_key == "FlashcardGenerator":
                # Create a proper closure that captures the tool instance
                def create_flashcard_chain(tool_instance):
                    async def flashcard_chain(input_data: str) -> str:
                        return await tool_instance._arun(input_data)

                    return flashcard_chain

                tool_chains[internal_tool_key] = create_flashcard_chain(tool)

            elif internal_tool_key == "RAGTool":
                # Create a proper closure that captures the tool instance
                def create_rag_chain(tool_instance):
                    async def rag_chain(input_text: str) -> str:
                        return await tool_instance._arun(input_text)

                    return rag_chain

                tool_chains[internal_tool_key] = create_rag_chain(tool)

            elif internal_tool_key == "ExamGenerator":
                # Create a proper closure that captures the tool instance
                def create_exam_chain(tool_instance):
                    async def exam_chain(input_data: str) -> str:
                        return await tool_instance._arun(input_data)

                    return exam_chain

                tool_chains[internal_tool_key] = create_exam_chain(tool)

            elif internal_tool_key == "TavilySearchResults":
                # Create a proper closure that captures the tool instance
                def create_tavily_chain(tool_instance):
                    async def tavily_chain(input_text: str) -> str:
                        try:
                            results = await tool_instance.ainvoke({"query": input_text})
                            if isinstance(results, list):
                                contents = [r.get('content', '') for r in results if 'content' in r]
                                return "\n".join(contents) if contents else "Przepraszam, nie mogę znaleźć odpowiedzi."
                            return results.get('answer', "Przepraszam, nie mogę znaleźć odpowiedzi.")
                        except Exception as e:
                            logger.error(f"Error in TavilySearchResults: {e}")
                            return "Przepraszam, wystąpił problem z wyszukiwaniem."

                    return tavily_chain

                tool_chains[internal_tool_key] = create_tavily_chain(tool)

        return tool_chains

    async def handle_query(self, query: str, selected_tools: Optional[List[str]] = None) -> str:
        logger.info(f"Handling query='{query}' for user={self.user_id}, tools={selected_tools}")
        try:
            conversation = get_latest_checkpoint(self.user_id, self.conversation_id)
            if not conversation:
                conversation = create_memory(user_id=self.user_id)
            conversation_id = conversation.id

            cache_key = f"history:{conversation_id}:{self.MAX_HISTORY_LENGTH}"
            cached_history = await redis_client.get(cache_key)
            if cached_history:
                aggregated_context = cached_history.decode()
            else:
                aggregated_context = cached_conversation_history(conversation_id, self.MAX_HISTORY_LENGTH)
                await redis_client.setex(cache_key, 3600, aggregated_context)

            if len(get_conversation_history(conversation_id, self.MAX_HISTORY_LENGTH)) <= 2:
                await asyncio.to_thread(set_conversation_title, conversation, query, self.model)

            tool_chains = await self._initialize_tool_chains(selected_tools)

            if not selected_tools:
                return await tool_chains["DirectAnswer"](query, aggregated_context=aggregated_context)

            tasks = []
            for user_tool_name in selected_tools:
                internal_tool_key = USER_TOOL_MAPPING.get(user_tool_name, "DirectAnswer")
                tool_func = tool_chains.get(internal_tool_key)
                if tool_func:
                    if internal_tool_key == "RAGTool":
                        tasks.append(tool_func(query))
                    elif internal_tool_key in ["FlashcardGenerator", "ExamGenerator"]:
                        input_data = json.dumps({"description": aggregated_context, "query": query}, ensure_ascii=False)
                        tasks.append(tool_func(input_data))
                    elif internal_tool_key == "TavilySearchResults":
                        # TavilySearchResults doesn't accept aggregated_context parameter
                        tasks.append(tool_func(query))
                    elif internal_tool_key == "DirectAnswer":
                        tasks.append(tool_func(query, aggregated_context=aggregated_context))
                    else:
                        # Default case - try with aggregated_context, fallback to just query
                        try:
                            tasks.append(tool_func(query, aggregated_context=aggregated_context))
                        except TypeError:
                            tasks.append(tool_func(query))

            results = await asyncio.gather(*tasks, return_exceptions=True)
            aggregated_context = ""
            for response in results:
                if isinstance(response, Exception):
                    logger.error(f"Tool error: {response}")
                    continue
                aggregated_context += f"\n\n{response}"

            return await final_answer(aggregated_context, query)
        except Exception as e:
            logger.error(f"Error handling query: {e}", exc_info=True)
            return f"Przepraszam, wystąpił problem: {str(e)}"


async def agent_response(
    user_id: str,
    query: str,
    model_name: str = "claude-3-haiku-20240307",
    anthropic_api_key: str = None,
    tavily_api_key: str = None,
    conversation_id: int = None,
    openai_api_key: str = None,
    selected_tools: Optional[List[str]] = None
) -> str:
    anthropic_api_key = anthropic_api_key or os.getenv('ANTHROPIC_API_KEY')
    openai_api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
    tavily_api_key = tavily_api_key or os.getenv('TAVILY_API_KEY')

    if not all([anthropic_api_key, openai_api_key, tavily_api_key]):
        raise ValueError("Missing required API keys.")

    model = ChatAnthropic(anthropic_api_key=anthropic_api_key, model=model_name, temperature=0.1)
    agent = ChatAgent(
        user_id=user_id,
        model=model,
        tavily_api_key=tavily_api_key,
        anthropic_api_key=anthropic_api_key,
        openai_api_key=openai_api_key,
        memory=create_memory,
        conversation_id=conversation_id
    )
    return await agent.handle_query(query, selected_tools)