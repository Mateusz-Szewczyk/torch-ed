# agent.py

import os
import logging
from typing import Callable, Dict, List, Optional
import json

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate
from langchain_community.tools.tavily_search.tool import TavilySearchResults
from dotenv import load_dotenv
from pathlib import Path

from .utils import set_conversation_title
from ..models import Conversation
from .tools import FlashcardGenerator, RAGTool, ExamGenerator
from .agent_memory import (
    create_memory,
    get_latest_checkpoint,
    get_conversation_history,
)
from langchain.tools import BaseTool

logger = logging.getLogger(__name__)

env_path = Path(__file__).resolve().parents[2] / '.env'
load_dotenv(dotenv_path=env_path)


#
# ---------------------- DirectAnswer Tool ----------------------
#
class DirectAnswer(BaseTool):
    name: str = "DirectAnswer"
    description: str = (
        "Provides direct, concise answers to user questions based solely on the provided context. "
        "Use this tool for short/personal questions or fallback if no other tool is needed."
    )

    model: Optional[ChatAnthropic] = None

    def __init__(self, model: ChatAnthropic):
        super().__init__()
        self.model = model

    def _run(self, query: str, aggregated_context: str = "") -> str:
        logger.debug(f"DirectAnswer tool processing query: {query}")
        if self.model is None:
            raise ValueError("ChatAnthropic model is not initialized")

        try:
            system_prompt = (
                "You are a helpful assistant providing a direct, concise answer using only the given context. "
                "If context is insufficient, answer as best you can."
            )

            # Łączymy kontekst + query (jeżeli mamy kontekst)
            full_query = (
                f"Context:\n{aggregated_context}\n\nQuestion: {query}"
                if aggregated_context else query
            )

            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", "{question}")
            ])
            messages = prompt.format_messages(question=full_query)
            logger.debug(f"Generating direct answer with messages: {messages}")
            response = self.model.invoke(messages).content

            return response.strip()

        except Exception as e:
            logger.error(f"Error generating direct answer: {e}", exc_info=True)
            return "Przepraszam, wystąpił problem z generowaniem odpowiedzi."

    async def _arun(self, query: str) -> str:
        # Asynchroniczna wersja (niewdrożona)
        raise NotImplementedError("DirectAnswer does not support async operations.")


#
# ---------------------- create_tool_chains ----------------------
#
def create_tool_chains(
    flashcard_tool: FlashcardGenerator,
    rag_tool: RAGTool,
    tavily_tool: TavilySearchResults,
    exam_tool: ExamGenerator,
    model: ChatAnthropic
) -> Dict[str, callable]:
    """
    Mapa nazw narzędzi -> funkcje uruchamiające je.
    """
    def flashcard_chain(input_data: str) -> str:
        return flashcard_tool.run(input_data)

    def rag_chain(input_text: str) -> str:
        return rag_tool.run(input_text)

    def tavily_chain(input_text: str) -> str:
        logger.debug(f"Invoking TavilySearchResults with query: {input_text}")
        try:
            results = tavily_tool.invoke({"query": input_text})
            logger.debug(f"TavilySearchResults response: {results}")
            if isinstance(results, list):
                contents = [r.get('content', '') for r in results if 'content' in r]
                return "\n".join(contents) if contents else "Przepraszam, nie mogę znaleźć odpowiedzi."
            elif isinstance(results, dict) and 'answer' in results:
                return results['answer']
            else:
                logger.error(f"Unexpected format from TavilySearchResults: {results}")
                return "Przepraszam, nie mogę znaleźć odpowiedzi."
        except Exception as e:
            logger.error(f"Error invoking TavilySearchResults: {e}")
            return "Przepraszam, wystąpił problem z wyszukiwaniem."

    def exam_chain(input_data: str) -> str:
        return exam_tool.run(input_data)

    direct_answer_tool = DirectAnswer(model=model)

    # Umożliwiamy przekazanie query i kontekstu
    def direct_answer_chain(query: str, aggregated_context: str = "") -> str:
        return direct_answer_tool.run(query, aggregated_context=aggregated_context)

    return {
        "FlashcardGenerator": flashcard_chain,
        "RAGTool": rag_chain,
        "TavilySearchResults": tavily_chain,
        "ExamGenerator": exam_chain,
        "DirectAnswer": direct_answer_chain
    }


#
# ---------------------- final_answer ----------------------
#
def final_answer(context: str, query: str) -> str:
    """
    Generuje końcową, ładnie sformatowaną odpowiedź (Markdown) bazując na kontekście i pytaniu.
    """
    try:
        final_model = ChatOpenAI(
            model_name="gpt-4o-mini-2024-07-18",
            temperature=0.0
        )

        system_prompt = (
            "Jesteś pomocnym asystentem łączącym informacje z wielu źródeł. "
            "Na podstawie kontekstu i pytania użytkownika wygeneruj odpowiedź w formacie **Markdown**, "
            "ładnie sformatowaną i czytelną."
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "Using this context: {context}\nAnswer the query."),
            ("human", "Pytanie: {question}")
        ])
        messages = prompt.format_messages(question=query, context=context)
        logger.debug(f"Generating final answer with messages: {messages}")

        response = final_model.invoke(messages)
        response_text = response.content

        logger.debug(f"Finalized response: {response_text}")
        return response_text

    except Exception as e:
        logger.error(f"Error generating final answer: {e}")
        return "Przepraszam, wystąpił problem z generowaniem końcowej odpowiedzi."



#
# ---------------------- Mapowanie nazw używanych w UI na wewnętrzne klucze narzędzi ----------------------
#
USER_TOOL_MAPPING = {
    "Wiedza z plików": "RAGTool",
    "Generowanie fiszek": "FlashcardGenerator",
    "Generowanie egzaminu": "ExamGenerator",
    "Wyszukaj w internecie": "TavilySearchResults"
}


#
# ---------------------- ChatAgent ----------------------
#

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

        # Inicjalizacja narzędzi
        self.flashcard_tool = FlashcardGenerator(
            user_id=self.user_id,
            model_type="OpenAI",
            model_name="gpt-4o-mini-2024-07-18",
            api_key=openai_api_key
        )
        self.rag_tool = RAGTool(
            user_id=self.user_id,
            model_type="OpenAI",
            model_name="gpt-4o-mini-2024-07-18",
            api_key=openai_api_key
        )
        self.tavily_tool = TavilySearchResults(
            name="TavilySearchResults",
            tavily_api_key=self.tavily_api_key,
            search_depth='advanced',
            max_results=5,
            include_answer=True,
            include_raw_content=True,
            include_images=True
        )
        self.exam_tool = ExamGenerator(
            user_id=self.user_id,
            model_name="gpt-4o-mini-2024-07-18",
            openai_api_key=openai_api_key
        )
        self.direct_answer_tool = DirectAnswer(model=self.model)

        # Słownik narzędzi
        self.tool_chains = create_tool_chains(
            flashcard_tool=self.flashcard_tool,
            rag_tool=self.rag_tool,
            tavily_tool=self.tavily_tool,
            exam_tool=self.exam_tool,
            model=self.model
        )

    def handle_query(
        self,
        query: str,
        selected_tools: Optional[List[str]] = None
    ) -> str:
        """
        Obsługa zapytania:
          - Jeśli brak narzędzi (selected_tools) => DirectAnswer z historią jako kontekstem.
          - W przeciwnym razie iterujemy po narzędziach, doklejamy odpowiedzi do aggregated_context,
            a na końcu generujemy final_answer.
        """

        logger.info(f"Handling query='{query}' for user={self.user_id}, tools={selected_tools}")

        # 1. Pobieramy / tworzymy konwersację i historię
        try:
            conversation = get_latest_checkpoint(self.user_id, self.conversation_id)
            if not conversation:
                conversation = create_memory(user_id=self.user_id)
            conversation_id = conversation.id

            conversation_history = get_conversation_history(conversation_id, self.MAX_HISTORY_LENGTH)
        except Exception as e:
            logger.error(f"Error retrieving conversation: {e}")
            return "Przepraszam, wystąpił problem z przetworzeniem Twojego zapytania."

        # 2. Jeżeli nowa konwersacja – ustawiamy jej nazwę
        logger.info(f"Conversation history length: {len(conversation_history)}")
        if len(conversation_history) <= 2:
            set_conversation_title(conversation, query, self.model)

        # 3. Zbuduj kontekst z historii
        aggregated_context = "\n".join(conversation_history) if conversation_history else ""

        # 4. Brak narzędzi => DirectAnswer z kontekstem
        if not selected_tools:
            return self.tool_chains["DirectAnswer"](query, aggregated_context=aggregated_context)

        # 5. Iterujemy narzędzia, w kolejności wybranej przez użytkownika
        for user_tool_name in selected_tools:
            internal_tool_key = USER_TOOL_MAPPING.get(user_tool_name, "DirectAnswer")
            tool_func = self.tool_chains[internal_tool_key]

            try:
                if internal_tool_key == "RAGTool":
                    # RAGTool przyjmuje tylko query
                    response = tool_func(query)

                elif internal_tool_key in ["FlashcardGenerator", "ExamGenerator"]:
                    # Tworzymy JSON z description = kontekst + query
                    input_data = json.dumps({
                        "description": aggregated_context,
                        "query": query
                    }, ensure_ascii=False)
                    response = tool_func(input_data)

                elif internal_tool_key == "TavilySearchResults":
                    # Tylko query
                    response = tool_func(query)

                else:
                    # DirectAnswer -> context + query
                    response = tool_func(query, aggregated_context=aggregated_context)

                logger.debug(f"Tool '{internal_tool_key}' response:\n{response}")

                # Jeśli nie jest to komunikat o błędzie ("Przepraszam..."), doklejamy do kontekstu
                if not response.startswith("Przepraszam"):
                    aggregated_context += f"\n\n{response}"

            except Exception as e:
                logger.error(f"Error using tool {internal_tool_key}: {e}", exc_info=True)
                return f"Przepraszam, wystąpił problem z narzędziem '{user_tool_name}'."

        # 6. Gdy skończymy wywoływać narzędzia, tworzymy finalną odpowiedź z całym zebranym kontekstem
        return final_answer(aggregated_context, query)


#
# ---------------------- Główna funkcja agent_response ----------------------
#
def agent_response(
    user_id: str,
    query: str,
    model_name: str = "claude-3-haiku-20240307",
    anthropic_api_key: str = None,
    tavily_api_key: str = None,
    conversation_id: int = None,
    openai_api_key: str = None,
    selected_tools: Optional[List[str]] = None
) -> str:
    """
    Główna funkcja – tworzy ChatAgent i zwraca odpowiedź.

    Jeśli selected_tools jest puste => DirectAnswer z historią.
    Jeśli jakieś narzędzia są wybrane => uruchom je kolejno, a na końcu final_answer.
    """
    logger.info(f"Generating response for user_id={user_id}, query='{query}'")

    # Pobieranie kluczy API z env jeśli nie podano
    if not anthropic_api_key:
        anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        if not anthropic_api_key:
            raise ValueError("Anthropic API key is not set.")

    if not openai_api_key:
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            raise ValueError("OpenAI API key is not set.")

    if not tavily_api_key:
        tavily_api_key = os.getenv('TAVILY_API_KEY')
        if not tavily_api_key:
            raise ValueError("Tavily API key is not set.")

    try:
        # Inicjalizacja modelu Anthropic
        model = ChatAnthropic(
            anthropic_api_key=anthropic_api_key,
            model=model_name,
            temperature=0.1
        )

        # Tworzenie instancji agenta
        agent = ChatAgent(
            user_id=user_id,
            model=model,
            tavily_api_key=tavily_api_key,
            anthropic_api_key=anthropic_api_key,
            openai_api_key=openai_api_key,
            memory=create_memory,
            conversation_id=conversation_id
        )

        # Wywołanie metody agenta
        logger.info(f"Selected tools: {selected_tools}")
        response = agent.handle_query(query, selected_tools)
        logger.info(f"Generated response: '{response}'")
        return response

    except Exception as e:
        logger.error(f"Error generating response: {e}", exc_info=True)
        return f"Wystąpił błąd podczas generowania odpowiedzi: {str(e)}"
