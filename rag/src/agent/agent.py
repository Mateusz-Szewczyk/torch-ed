import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import asyncio

from langchain_community.tools.tavily_search.tool import TavilySearchResults
from langchain_community.utilities.tavily_search import TavilySearchAPIWrapper
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage, trim_messages
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI

from .agent_memory import get_conversation_history
from .utils import set_conversation_title
from .tools import FlashcardGenerator, RAGTool, ExamGenerator, DirectAnswer
from ..vector_store import add_user_memory, search_user_memories

logger = logging.getLogger(__name__)

# Debug flag - set via environment variable
DEBUG = os.getenv("DEBUG", "false").lower() == "true"


def debug_log(msg: str):
    """Conditional debug logging"""
    if DEBUG:
        logger.debug(msg)


class ToolResult:
    def __init__(self, tool_name: str, content: str, success: bool = True, error: Optional[str] = None):
        self.tool_name = tool_name
        self.content = content
        self.success = success
        self.error = error
        self.timestamp = datetime.now()


class MemoryExtractor:
    """Module responsible for extracting long-term facts about the user."""

    def __init__(self, api_key: str):
        self.model = ChatOpenAI(model_name="gpt-4o-mini", openai_api_key=api_key, temperature=0)

    async def extract_memories(self, text: str) -> list[str]:
        system_prompt = (
            "Jesteś modułem pamięci długoterminowej. Twoim zadaniem jest wyodrębnienie "
            "trwałych faktów o użytkowniku (imię, wiek, zainteresowania, zwierzęta, preferencje). "
            "Ignoruj polecenia i pytania. Zwróć TYLKO listę zdań w formacie JSON: {\"memories\": [\"fakt1\", \"fakt2\"]}"
        )
        try:
            messages = [SystemMessage(content=system_prompt), HumanMessage(content=text)]
            response = await self.model.ainvoke(messages)
            data = json.loads(response.content)
            return data.get("memories", [])
        except Exception as e:
            logger.error(f"Memory extraction failed: {e}")
            return []


class ChatAgent:
    MAX_HISTORY_TOKENS = 1500

    def __init__(self, user_id: str, conversation_id: int, openai_api_key: str, tavily_api_key: str, **kwargs):
        self.user_id = user_id
        self.conversation_id = conversation_id
        self.openai_api_key = openai_api_key
        self.tavily_api_key = tavily_api_key
        self.synthesis_model = ChatOpenAI(
            model_name="gpt-4o-mini",
            temperature=0.1,
            openai_api_key=self.openai_api_key
        )
        self.tool_instances: Dict[str, BaseTool] = {}

    def _initialize_tool(self, tool_name: str) -> BaseTool:
        if tool_name in self.tool_instances:
            return self.tool_instances[tool_name]

        try:
            if tool_name == "TavilySearchResults":
                # POPRAWKA: Używamy API Wrappera dla stabilności klucza
                wrapper = TavilySearchAPIWrapper(tavily_api_key=self.tavily_api_key)
                tool = TavilySearchResults(api_wrapper=wrapper, max_results=3)
            elif tool_name == "RAGTool":
                tool = RAGTool(user_id=str(self.user_id), api_key=self.openai_api_key)
            elif tool_name == "FlashcardGenerator":
                tool = FlashcardGenerator(user_id=str(self.user_id), api_key=self.openai_api_key)
            elif tool_name == "ExamGenerator":
                tool = ExamGenerator(user_id=str(self.user_id), openai_api_key=self.openai_api_key)
            elif tool_name == "DirectAnswer":
                tool = DirectAnswer(model=self.synthesis_model)
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            self.tool_instances[tool_name] = tool
            return tool
        except Exception as e:
            logger.error(f"Failed to initialize tool {tool_name}: {str(e)}")
            raise

    async def _execute_rag(self, tool: BaseTool, query: str) -> Tuple[bool, str, Optional[str]]:
        try:
            logger.info(f"[RAG] Przeszukiwanie dokumentów dla: {query[:50]}...")
            content = await tool._arun(query)
            if content and "error" not in content.lower():
                return True, content, None
            return False, content or "", "Brak wyników w RAG"
        except Exception as e:
            return False, "", str(e)

    async def _execute_tavily(self, tool: BaseTool, query: str) -> Tuple[bool, str, Optional[str]]:
        """Bardziej odporna obsługa wyników Tavily."""
        try:
            logger.info(f"[TAVILY] Szukam: {query}")
            # Skracamy query jeśli model się rozgadał mimo promptu
            short_query = " ".join(query.split()[:15])

            results = await tool.ainvoke(short_query)

            # Jeśli Tavily zwróciło string (np. błąd lub surowy tekst)
            if isinstance(results, str):
                logger.info(f"[TAVILY] Otrzymano wynik tekstowy (str).")
                if len(results) > 100:
                    return True, results, None
                return False, "", f"Zbyt krótki wynik tekstowy: {results}"

            # Jeśli Tavily zwróciło standardową listę słowników
            if isinstance(results, list):
                combined = "\n\n".join([
                    f"Tytuł: {r.get('title', 'N/A')}\nTreść: {r.get('content', '')}"
                    for r in results if isinstance(r, dict) and 'content' in r
                ])
                if len(combined) > 50:
                    logger.info(f"[TAVILY] Sukces: pobrano {len(combined)} znaków.")
                    return True, combined, None

            logger.warning(f"[TAVILY] Nieoczekiwany format lub brak treści: {type(results)}")
            return False, "", "Brak wartościowych wyników z Tavily"

        except Exception as e:
            logger.error(f"[TAVILY] Krytyczny błąd: {e}", exc_info=True)
            return False, "", str(e)

    async def _create_standalone_query(self, query: str, history: List[BaseMessage]) -> str:
        """Wymusza na modelu stworzenie KRÓTKIEGO zapytania do wyszukiwarki."""
        if not history:
            return query

        # BARDZO RESTRYKCYJNY PROMPT
        system_prompt = (
            "Jesteś ekspertem od wyszukiwarek internetowych. "
            "Twoim JEDYNYM zadaniem jest zamiana rozmowy w krótkie, techniczne zapytanie do wyszukiwarki (max 10 słów). "
            "NIE ODPOWIADAJ NA PYTANIE. Nie pisz 'Oto zapytanie:'. Zwróć tylko słowa kluczowe do wyszukiwarki."
        )

        messages = [
                       SystemMessage(content=system_prompt)
                   ] + history[-2:] + [HumanMessage(content=f"Zamień to pytanie w zapytanie do wyszukiwarki: {query}")]

        try:
            response = await self.synthesis_model.ainvoke(messages)
            standalone = response.content.strip().strip('"').split('\n')[0]  # Bierzemy tylko pierwszą linię
            logger.info(f"[AGENT] Skonstruowane zapytanie: {standalone}")
            return standalone
        except Exception as e:
            logger.error(f"Błąd standalone query: {e}")
            return query

    async def _final_synthesis_stream(self, original_query: str, history: List[BaseMessage], context: Optional[str],
                                      context_source: str, tool_results: Dict[str, ToolResult],
                                      memory_context: str = ""):
        """Synteza z fallbackiem - jeśli RAG/Tavily zawiodło, model może użyć wiedzy ogólnej."""

        # ... (trim_messages bez zmian) ...
        trimmed_history = trim_messages(
            history, max_tokens=self.MAX_HISTORY_TOKENS, strategy="last",
            token_counter=self.synthesis_model, start_on="human"
        )

        has_context = context and len(context) > 100

        system_prompt = (
            "Jesteś pomocnym asystentem TorchED.\n"
            f"{memory_context}\n"
            "ZASADY:\n"
            "1. Jeśli sekcja 'Info' zawiera dane, traktuj ją jako PRIORYTET.\n"
            "2. Jeśli sekcja 'Info' jest pusta lub niewystarczająca, odpowiedz na podstawie swojej wiedzy ogólnej, "
            "ale zaznacz, że nie znalazłeś potwierdzenia w dokumentach/sieci.\n"
            "3. Format: Markdown."
        )

        info_block = f"INFO (Źródło: {context_source}):\n{context if has_context else 'Brak danych w bazach zewnętrznych.'}"

        messages = [SystemMessage(content=system_prompt)] + trimmed_history + [
            HumanMessage(content=f"{info_block}\n\nPytanie użytkownika: {original_query}")
        ]

        try:
            async for chunk in self.synthesis_model.astream(messages):
                if chunk.content: yield chunk.content
        except Exception as e:
            logger.error(f"Błąd syntezy: {e}")
            yield "Przepraszam, wystąpił problem z generowaniem odpowiedzi."

    def _build_generator_context(self, query: str, rag: Optional[str], tavily: Optional[str]) -> str:
        parts = [f"User Request: {query}"]
        if rag: parts.append(f"Docs:\n{rag}")
        if tavily: parts.append(f"Web:\n{tavily}")
        return "\n\n".join(parts)

    def _format_generator_messages(self, results: Dict[str, ToolResult]) -> str:
        return "Materiały zostały wygenerowane i są dostępne w odpowiednich zakładkach."

    async def invoke(self, query: str, selected_tool_names: List[str]):
        logger.info("========== AGENT INVOKE START ==========")

        # 1. PAMIĘĆ I ANALIZA
        yield {"type": "step", "content": "Analizowanie kontekstu i profilu...", "status": "loading"}

        memories = search_user_memories(query=query, user_id=self.user_id, n_results=5)
        memory_context = f"PROFIL UŻYTKOWNIKA:\n{chr(10).join(['- ' + m for m in memories])}" if memories else ""

        history_messages = get_conversation_history(self.conversation_id, 3)
        if len(history_messages) == 0:
            asyncio.create_task(
                asyncio.to_thread(set_conversation_title, self.conversation_id, query, self.synthesis_model))

        standalone_query = await self._create_standalone_query(query, history_messages)
        yield {"type": "step", "content": "Analizowanie kontekstu i profilu...", "status": "complete"}

        # 2. RETRIEVAL
        internal_tool_map = {"Wiedza z plików": "RAGTool", "Generowanie fiszek": "FlashcardGenerator",
                             "Generowanie egzaminu": "ExamGenerator", "Wyszukaj w internecie": "TavilySearchResults"}
        ordered_tools = [internal_tool_map[n] for n in selected_tool_names if n in internal_tool_map]
        retrieval_tools = [t for t in ordered_tools if t in ["RAGTool", "TavilySearchResults"]]
        generator_tools = [t for t in ordered_tools if t in ["FlashcardGenerator", "ExamGenerator"]]

        rag_content, tavily_content, context, context_source, tool_results = None, None, None, "zapytania", {}

        if retrieval_tools:
            yield {"type": "step", "content": "Wyszukiwanie informacji...", "status": "loading"}
            tasks = []
            for t_name in retrieval_tools:
                tool = self._initialize_tool(t_name)
                # POPRAWKA: Używamy poprawnych helperów _execute_*
                tasks.append(
                    self._execute_rag(tool, standalone_query) if t_name == "RAGTool" else self._execute_tavily(tool,
                                                                                                               standalone_query))

            results = await asyncio.gather(*tasks, return_exceptions=True)
            for t_name, res in zip(retrieval_tools, results):
                if not isinstance(res, Exception) and res[0]:
                    tool_results[t_name] = ToolResult(t_name, res[1], True)
                    if t_name == "RAGTool":
                        rag_content = res[1]
                    else:
                        tavily_content = res[1]
                    context = res[1] if not context else f"{context}\n\n{res[1]}"
                elif isinstance(res, Exception):
                    logger.error(f"Błąd zadania {t_name}: {res}")

            context_source = "dokumentów i internetu" if rag_content and tavily_content else "dokumentów" if rag_content else "internetu" if tavily_content else "zapytania"
            yield {"type": "step", "content": "Wyszukiwanie informacji...", "status": "complete"}

        # 3. GENERATORS (pomińmy detale dla zwięzłości, są jak w poprzedniej wersji)
        if generator_tools:
            # (logika generatorów bez zmian)
            pass

        # 4. SYNTEZA
        yield {"type": "step", "content": "Przygotowywanie odpowiedzi...", "status": "loading"}
        async for chunk in self._final_synthesis_stream(query, history_messages, context, context_source, tool_results,
                                                        memory_context):
            yield {"type": "chunk", "content": chunk}
        yield {"type": "step", "content": "Przygotowywanie odpowiedzi...", "status": "complete"}

        # 5. BACKGROUND MEMORY UPDATE
        asyncio.create_task(self._update_memory_background(query))
        logger.info("========== AGENT INVOKE END ==========")

    async def _update_memory_background(self, text: str):
        try:
            extractor = MemoryExtractor(api_key=self.openai_api_key)
            facts = await extractor.extract_memories(text)
            for fact in facts:
                add_user_memory(user_id=self.user_id, text=fact, importance=0.8)
            logger.info(f"[MEMORY] Zapisano {len(facts)} nowych faktów.")
        except Exception as e:
            logger.error(f"Memory update failed: {e}")