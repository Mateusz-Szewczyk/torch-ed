import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import asyncio

from langchain_community.tools.tavily_search.tool import TavilySearchResults
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI

from .agent_memory import get_conversation_history
from .utils import set_conversation_title
from .tools import FlashcardGenerator, RAGTool, ExamGenerator, DirectAnswer

logger = logging.getLogger(__name__)

# Debug flag - set via environment variable
DEBUG = os.getenv("DEBUG", "false").lower() == "true"


def debug_log(msg: str):
    """Conditional debug logging"""
    if DEBUG:
        logger.debug(msg)


class ToolResult:
    """Container for tool execution results with metadata"""

    def __init__(self, tool_name: str, content: str, success: bool = True, error: Optional[str] = None):
        self.tool_name = tool_name
        self.content = content
        self.success = success
        self.error = error
        self.timestamp = datetime.now()
        debug_log(
            f"ToolResult created - Tool: {tool_name}, Success: {success}, Content length: {len(content) if content else 0}, Error: {error}")


class ChatAgent:
    """The main agent responsible for orchestrating tool use and generating final responses."""
    MAX_HISTORY_LENGTH = 3  # Reduced from 5 for token optimization
    MAX_HISTORY_CHARS = 1500  # Character limit for history

    def __init__(self, user_id: str, conversation_id: int, openai_api_key: str, tavily_api_key: str, **kwargs):
        debug_log(f"ChatAgent initialization - User ID: {user_id}, Conversation ID: {conversation_id}")
        self.user_id = user_id
        self.conversation_id = conversation_id
        self.openai_api_key = openai_api_key
        self.tavily_api_key = tavily_api_key
        self.synthesis_model = ChatOpenAI(
            model_name="gpt-4o-mini-2024-07-18",
            temperature=0.1,
            openai_api_key=self.openai_api_key
        )
        self.tool_instances: Dict[str, BaseTool] = {}
        debug_log("ChatAgent initialized successfully")

    def _initialize_tool(self, tool_name: str) -> BaseTool:
        """Lazy initialization of tools to save resources."""
        debug_log(f"Initializing tool: {tool_name}")

        if tool_name in self.tool_instances:
            debug_log(f"Tool {tool_name} already exists in cache")
            return self.tool_instances[tool_name]

        user_id_str = str(self.user_id)

        try:
            if tool_name == "TavilySearchResults":
                tool = TavilySearchResults(tavily_api_key=self.tavily_api_key, max_results=3)
            elif tool_name == "RAGTool":
                tool = RAGTool(user_id=user_id_str, api_key=self.openai_api_key)
            elif tool_name == "FlashcardGenerator":
                tool = FlashcardGenerator(user_id=user_id_str, api_key=self.openai_api_key)
            elif tool_name == "ExamGenerator":
                tool = ExamGenerator(user_id=user_id_str, openai_api_key=self.openai_api_key)
            elif tool_name == "DirectAnswer":
                tool = DirectAnswer(model=self.synthesis_model)
            else:
                logger.error(f"Unknown tool requested: {tool_name}")
                raise ValueError(f"Unknown tool: {tool_name}")

            self.tool_instances[tool_name] = tool
            debug_log(f"Tool {tool_name} initialized and cached successfully")
            return tool

        except Exception as e:
            logger.error(f"Failed to initialize tool {tool_name}: {str(e)}")
            raise

    def _truncate_history(self, history: str) -> str:
        """Smart truncation - keep recent context only"""
        if len(history) <= self.MAX_HISTORY_CHARS:
            return history

        # Keep last N characters
        truncated = "...(earlier messages omitted)...\n" + history[-self.MAX_HISTORY_CHARS:]
        debug_log(f"History truncated: {len(history)} → {len(truncated)} chars")
        return truncated

    async def _create_standalone_query(self, query: str, history: str) -> str:
        """Uses an LLM to rephrase a follow-up query into a standalone question."""
        debug_log(f"Creating standalone query from: '{query}'")

        # OPTIMIZATION: Skip LLM call if no meaningful history
        if not history or len(history.strip()) < 200:
            debug_log("No or short history, returning original query")
            return query

        # OPTIMIZATION: Count actual conversation turns
        history_turns = history.count("User:") + history.count("Assistant:")
        if history_turns < 2:  # Less than 1 full conversation
            debug_log("Less than 2 turns in history, returning original query")
            return query

        # OPTIMIZATION: Shorter, more focused prompt
        system_prompt = (
            f"Rephrase as standalone question. Today: {datetime.now().strftime('%Y-%m-%d')}. "
            "If already standalone, return unchanged."
        )
        # Use only last 1000 chars of history
        user_prompt = f"History:\n{history[-1000:]}\n\nQuestion: {query}\n\nStandalone:"

        try:
            debug_log("Sending query to synthesis model for standalone conversion")
            messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
            response = await self.synthesis_model.ainvoke(messages)
            standalone_query = response.content.strip().strip('"')
            debug_log(f"Original query: '{query}' -> Standalone query: '{standalone_query}'")
            logger.info(f"Standalone query: '{standalone_query}'")
            return standalone_query
        except Exception as e:
            logger.error(f"Failed to create standalone query: {str(e)}")
            debug_log("Returning original query due to error")
            return query

    def _build_generator_context(self, query: str, rag_content: Optional[str], tavily_content: Optional[str]) -> str:
        """Builds context for generator tools by combining query with available content."""
        debug_log("Building generator context")

        context_parts = [f"User Request: {query}"]

        if rag_content and len(rag_content) > 50:
            context_parts.append(f"Information from your documents:\n{rag_content}")
            debug_log("Added RAG content to context")

        if tavily_content and len(tavily_content) > 50:
            context_parts.append(f"Additional information from web search:\n{tavily_content}")
            debug_log("Added Tavily content to context")

        combined_context = "\n\n".join(context_parts)
        debug_log(f"Final combined context length: {len(combined_context)}")
        return combined_context

    def _format_generator_messages(self, tool_results: Dict[str, ToolResult]) -> str:
        """Formats messages for successful generator tools, combining them if both are present."""
        debug_log("Formatting generator messages")

        flashcard_success = 'FlashcardGenerator' in tool_results and tool_results['FlashcardGenerator'].success
        exam_success = 'ExamGenerator' in tool_results and tool_results['ExamGenerator'].success

        messages = []

        # Handle FlashcardGenerator
        if flashcard_success:
            try:
                flashcard_data = json.loads(tool_results['FlashcardGenerator'].content)
                if 'error' in flashcard_data:
                    debug_log(f"FlashcardGenerator JSON contains error: {flashcard_data['error']}")
                    return f"❌ **Problem z tworzeniem fiszek:**\n{flashcard_data['error']}"

                topic = flashcard_data.get('topic', 'Twoje fiszki')
                num_flashcards = len(flashcard_data.get('flashcards', []))

                flashcard_msg = f"""## ✅ Fiszki zostały pomyślnie utworzone!

**📚 Temat:** {topic}  
**🔢 Liczba fiszek:** {num_flashcards}

### 🎯 Co dalej?
Twoje nowe fiszki czekają na Ciebie! Możesz teraz:
- 📖 **Przeglądać** wszystkie swoje fiszki
- 🧠 **Ćwiczyć** w trybie nauki
- 📊 **Śledzić** swoje postępy

👈 Przejdź do sekcji **'Fiszki'** w menu nawigacyjnym po lewej stronie, aby rozpocząć naukę!"""

                messages.append(flashcard_msg)

            except (json.JSONDecodeError, KeyError) as e:
                debug_log(f"FlashcardGenerator JSON parsing failed: {str(e)}")
                fallback_msg = """## ✅ Fiszki zostały pomyślnie utworzone!

### 🎯 Co dalej?
Twoje nowe fiszki są gotowe do nauki! 

👈 Przejdź do sekcji **'Fiszki'** w menu nawigacyjnym po lewej stronie, aby:
- 📖 Przeglądać swoje fiszki
- 🧠 Rozpocząć sesję nauki
- 📊 Monitorować postępy"""
                messages.append(fallback_msg)

        # Handle ExamGenerator
        if exam_success:
            try:
                exam_data = json.loads(tool_results['ExamGenerator'].content)
                if 'error' in exam_data:
                    debug_log(f"ExamGenerator JSON contains error: {exam_data['error']}")
                    return f"❌ **Problem z tworzeniem egzaminu:**\n{exam_data['error']}"

                topic = exam_data.get('topic', 'Twój egzamin')
                num_questions = exam_data.get('num_of_questions', len(exam_data.get('questions', [])))

                exam_msg = f"""## ✅ Egzamin został pomyślnie utworzony!

**📝 Temat:** {topic}  
**❓ Liczba pytań:** {num_questions}

### 🎯 Co dalej?
Twój nowy egzamin jest gotowy do rozwiązania! Możesz teraz:
- 📋 **Przystąpić** do egzaminu
- ⏱️ **Sprawdzić** swoje wyniki w czasie rzeczywistym
- 📈 **Analizować** swoje odpowiedzi po zakończeniu

👈 Przejdź do sekcji **'Egzaminy'** w menu nawigacyjnym po lewej stronie, aby rozpocząć test!

### 💡 Wskazówka
Pamiętaj, że możesz rozwiązywać egzamin wielokrotnie, aby poprawić swoje wyniki."""

                messages.append(exam_msg)

            except (json.JSONDecodeError, KeyError) as e:
                debug_log(f"ExamGenerator JSON parsing failed: {str(e)}")
                fallback_msg = """## ✅ Egzamin został pomyślnie utworzony!

### 🎯 Co dalej?
Twój nowy egzamin czeka na rozwiązanie!

👈 Przejdź do sekcji **'Egzaminy'** w menu nawigacyjnym po lewej stronie, aby:
- 📋 Przystąpić do testu
- ⏱️ Sprawdzić swoje wyniki
- 📈 Przeanalizować odpowiedzi

### 💡 Wskazówka
Możesz rozwiązywać egzamin wielokrotnie, aby doskonalić swoją wiedzę!"""
                messages.append(fallback_msg)

        # Return combined or single message
        if len(messages) > 1:
            debug_log(f"Combining {len(messages)} generator messages")
            return "\n\n---\n\n".join(messages)
        elif len(messages) == 1:
            debug_log("Returning single generator message")
            return messages[0]
        else:
            debug_log("No successful generator tools found")
            return ""

    async def _execute_rag(self, tool: BaseTool, query: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Execute RAG tool and return (success, content, error)"""
        try:
            debug_log(f"Executing RAGTool with query: '{query}'")
            output = await tool._arun(query)

            if output and "error" not in output.lower() and len(output) > 50:
                debug_log(f"RAGTool successful: {len(output)} chars")
                return True, output, None
            else:
                debug_log("RAGTool returned insufficient content")
                return False, output or "", "Insufficient content from RAGTool"
        except Exception as e:
            logger.error(f"RAGTool exception: {e}")
            return False, "", str(e)

    async def _execute_tavily(self, tool: BaseTool, query: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Execute Tavily tool and return (success, content, error)"""
        try:
            logger.info(f"[TAVILY] ========== STARTING TAVILY SEARCH ==========")
            logger.info(f"[TAVILY] Query: '{query}'")

            results = await tool.ainvoke({"query": query})

            logger.info(f"[TAVILY] Raw results type: {type(results)}")
            logger.info(f"[TAVILY] Raw results: {results[:500] if isinstance(results, str) else results}")

            if results and isinstance(results, list):
                logger.info(f"[TAVILY] Processing {len(results)} search results")

                # Log each result
                for idx, result in enumerate(results):
                    logger.info(
                        f"[TAVILY] Result {idx + 1}: {result.get('title', 'No title')} - {result.get('url', 'No URL')}")

                combined_content = "\n\n".join([r.get('content', '') for r in results if 'content' in r])

                if len(combined_content) > 50:
                    logger.info(f"[TAVILY] ✅ Success: {len(combined_content)} chars retrieved")
                    logger.info(f"[TAVILY] Content preview: {combined_content[:200]}...")
                    return (True, combined_content, None)
                else:
                    logger.warning(f"[TAVILY] ❌ Insufficient content: {len(combined_content)} chars")
                    return (False, combined_content or "", "Insufficient content from Tavily")
            else:
                logger.warning(f"[TAVILY] ❌ Unexpected format: {type(results)}")
                return (False, "", "Unexpected format from Tavily")

        except Exception as e:
            logger.error(f"[TAVILY] ❌ Exception during Tavily execution: {e}", exc_info=True)
            return (False, "", str(e))


    async def _final_synthesis_stream(self, original_query: str, history: str, context: Optional[str],
                                      context_source: str, tool_results: Dict[str, ToolResult]):
        """Streaming version of final synthesis that yields chunks as they're generated"""
        debug_log("Starting streaming final synthesis")

        # Check for DirectAnswer
        if 'DirectAnswer' in tool_results and tool_results['DirectAnswer'].success:
            debug_log("Returning DirectAnswer result (streaming)")
            yield tool_results['DirectAnswer'].content
            return

        # OPTIMIZATION: Truncate history before sending to LLM
        truncated_history = self._truncate_history(history)

        # OPTIMIZATION: Shorter system prompt
        system_prompt = """You are TorchED AI assistant. Answer clearly using the retrieved information.
Format: Markdown. Be honest about sources."""

        # OPTIMIZATION: More concise prompt structure
        prompt_context = f"""History: {truncated_history if truncated_history else "New conversation."}

Info ({context_source}): {context or "No specific information retrieved."}

Query: "{original_query}"

Answer:"""

        try:
            debug_log("Starting LLM streaming")
            messages = [SystemMessage(content=system_prompt), HumanMessage(content=prompt_context)]

            # Stream from OpenAI using astream()
            async for chunk in self.synthesis_model.astream(messages):
                if chunk.content:
                    debug_log(f"Yielding chunk: {chunk.content[:50]}...")
                    yield chunk.content

        except Exception as e:
            logger.error(f"Streaming synthesis failed: {e}")
            yield f"Error: {str(e)}"

    async def invoke(self, query: str, selected_tool_names: List[str]):
        """Main execution logic with streaming support - yields chunks as they're generated"""
        logger.info("========== AGENT INVOKE START (STREAMING) ==========")
        logger.info(f"Query: '{query}'")
        logger.info(f"Selected tool names: {selected_tool_names}")

        # Get conversation history
        history_list = get_conversation_history(self.conversation_id, self.MAX_HISTORY_LENGTH)
        if len(history_list) == 1:
            set_conversation_title(self.conversation_id, query, self.synthesis_model)
        history_str = "\n".join(history_list)
        logger.info(f"Conversation history length: {len(history_list)} messages")

        # Map user-friendly tool names to internal names
        internal_tool_map = {
            "Wiedza z plików": "RAGTool",
            "Generowanie fiszek": "FlashcardGenerator",
            "Generowanie egzaminu": "ExamGenerator",
            "Wyszukaj w internecie": "TavilySearchResults"
        }

        ordered_tools_to_execute = [
            internal_tool_map[name] for name in selected_tool_names if name in internal_tool_map
        ]
        logger.info(f"Mapped tools to execute: {ordered_tools_to_execute}")

        # Create standalone query
        standalone_query = await self._create_standalone_query(query, history_str)
        logger.info(f"Standalone query: '{standalone_query}'")

        context, context_source = None, "user query"
        tool_results: Dict[str, ToolResult] = {}

        # Separate tools into retrieval and generator categories
        retrieval_tools = [t for t in ordered_tools_to_execute if t in ["RAGTool", "TavilySearchResults"]]
        generator_tools = [t for t in ordered_tools_to_execute if t in ["FlashcardGenerator", "ExamGenerator"]]

        logger.info(f"Retrieval tools: {retrieval_tools}")
        logger.info(f"Generator tools: {generator_tools}")

        rag_content, tavily_content = None, None

        # ========== PHASE 1: RETRIEVAL TOOLS (PARALLEL) ==========
        if retrieval_tools:
            logger.info("========== PHASE 1: RETRIEVAL (PARALLEL) ==========")
            logger.info(f"Running {len(retrieval_tools)} retrieval tools in parallel: {retrieval_tools}")

            # Create async tasks for parallel execution
            retrieval_tasks = []
            task_tool_names = []

            for tool_name in retrieval_tools:
                logger.info(f"[PARALLEL] Preparing task for: {tool_name}")
                try:
                    tool = self._initialize_tool(tool_name)
                    task_tool_names.append(tool_name)

                    if tool_name == "RAGTool":
                        logger.info("[PARALLEL] Adding RAGTool task to parallel execution")
                        retrieval_tasks.append(self._execute_rag(tool, standalone_query))
                    elif tool_name == "TavilySearchResults":
                        logger.info("[PARALLEL] Adding TavilySearchResults task to parallel execution")
                        retrieval_tasks.append(self._execute_tavily(tool, standalone_query))

                except Exception as e:
                    logger.error(f"[PARALLEL] Failed to initialize {tool_name}: {e}", exc_info=True)

                    # Add error placeholder task
                    async def error_task():
                        return (False, "", str(e))

                    retrieval_tasks.append(error_task())

            # Execute all retrieval tools simultaneously
            if retrieval_tasks:
                logger.info(f"[PARALLEL] Executing {len(retrieval_tasks)} parallel tasks for: {task_tool_names}")
                retrieval_results = await asyncio.gather(*retrieval_tasks, return_exceptions=True)
                logger.info(f"[PARALLEL] Received {len(retrieval_results)} results from parallel execution")

                # Process results
                for tool_name, result in zip(task_tool_names, retrieval_results):
                    logger.info(f"[PARALLEL] Processing result for {tool_name}: {type(result)}")

                    if isinstance(result, Exception):
                        logger.error(f"[PARALLEL] {tool_name} failed with exception: {result}")
                        tool_results[tool_name] = ToolResult(tool_name, "", False, str(result))

                    elif result and isinstance(result, tuple) and len(result) == 3:
                        success, content, error = result
                        logger.info(
                            f"[PARALLEL] {tool_name} result - Success: {success}, Content length: {len(content) if content else 0}")
                        tool_results[tool_name] = ToolResult(tool_name, content or "", success, error)

                        if success and content:
                            if tool_name == "RAGTool":
                                rag_content = content
                                context = content
                                context_source = "your documents"
                                logger.info(f"[PARALLEL] RAG content retrieved: {len(content)} chars")
                            elif tool_name == "TavilySearchResults":
                                tavily_content = content
                                if not context:
                                    context = content
                                    context_source = "a web search"
                                else:
                                    context_source = "your documents and web search"
                                logger.info(f"[PARALLEL] Tavily content retrieved: {len(content)} chars")
                    else:
                        logger.warning(f"[PARALLEL] {tool_name} returned unexpected result format: {result}")
                        tool_results[tool_name] = ToolResult(tool_name, "", False, "Unexpected result format")

            logger.info(f"[PARALLEL] Phase 1 complete. Context source: {context_source}")

        # ========== PHASE 2: GENERATOR TOOLS (SEQUENTIAL) ==========
        if generator_tools:
            logger.info("========== PHASE 2: GENERATORS (AFTER RETRIEVAL) ==========")
            logger.info(f"Running {len(generator_tools)} generators: {generator_tools}")

            # Build context once for all generators
            generator_context = self._build_generator_context(query, rag_content, tavily_content)

            # Execute generators sequentially
            for tool_name in generator_tools:
                try:
                    tool = self._initialize_tool(tool_name)
                    generator_input = json.dumps({
                        "description": generator_context,
                        "query": query
                    })

                    logger.info(f"Executing {tool_name} with context length: {len(generator_context)}")
                    tool_output = await tool._arun(generator_input)

                    # Check for errors in output
                    tool_execution_successful = True
                    tool_error = None
                    try:
                        parsed_output = json.loads(tool_output)
                        if 'error' in parsed_output:
                            tool_execution_successful = False
                            tool_error = parsed_output['error']
                    except json.JSONDecodeError:
                        if "error" in tool_output.lower():
                            tool_execution_successful = False
                            tool_error = tool_output

                    tool_results[tool_name] = ToolResult(tool_name, tool_output, tool_execution_successful, tool_error)
                    logger.info(f"{tool_name} completed - Success: {tool_execution_successful}")

                except Exception as e:
                    logger.error(f"{tool_name} execution failed: {e}")
                    tool_results[tool_name] = ToolResult(tool_name, str(e), False, str(e))

            # For generators, return formatted message immediately (no streaming for structured JSON)
            flashcard_success = 'FlashcardGenerator' in tool_results and tool_results['FlashcardGenerator'].success
            exam_success = 'ExamGenerator' in tool_results and tool_results['ExamGenerator'].success

            if flashcard_success or exam_success:
                logger.info("Generator tools succeeded, yielding formatted message")
                result = self._format_generator_messages(tool_results)
                yield result
                logger.info("========== AGENT INVOKE END (GENERATORS) ==========")
                return

        # ========== PHASE 3: STREAM FINAL SYNTHESIS ==========
        logger.info("========== PHASE 3: STREAMING FINAL SYNTHESIS ==========")
        async for chunk in self._final_synthesis_stream(query, history_str, context, context_source, tool_results):
            yield chunk

        logger.info("========== AGENT INVOKE END (STREAMING) ==========")
