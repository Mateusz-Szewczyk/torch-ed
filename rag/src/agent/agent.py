import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from langchain_community.tools.tavily_search.tool import TavilySearchResults
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI

from .agent_memory import get_conversation_history
from .tools import FlashcardGenerator, RAGTool, ExamGenerator, DirectAnswer

logger = logging.getLogger(__name__)


class ToolResult:
    """Container for tool execution results with metadata"""

    def __init__(self, tool_name: str, content: str, success: bool = True, error: Optional[str] = None):
        self.tool_name = tool_name
        self.content = content
        self.success = success
        self.error = error
        self.timestamp = datetime.now()
        print(
            f"[DEBUG] ToolResult created - Tool: {tool_name}, Success: {success}, Content length: {len(content) if content else 0}, Error: {error}")


class ChatAgent:
    """The main agent responsible for orchestrating tool use and generating final responses."""
    MAX_HISTORY_LENGTH = 5

    def __init__(self, user_id: str, conversation_id: int, openai_api_key: str, tavily_api_key: str, **kwargs):
        print(f"[DEBUG] ChatAgent initialization - User ID: {user_id}, Conversation ID: {conversation_id}")
        self.user_id = user_id
        self.conversation_id = conversation_id
        self.openai_api_key = openai_api_key
        self.tavily_api_key = tavily_api_key
        self.synthesis_model = ChatOpenAI(model_name="gpt-4o-mini-2024-07-18", temperature=0.1,
                                          openai_api_key=self.openai_api_key)
        self.tool_instances: Dict[str, BaseTool] = {}
        print(f"[DEBUG] ChatAgent initialized successfully")

    def _initialize_tool(self, tool_name: str) -> BaseTool:
        """Lazy initialization of tools to save resources."""
        print(f"[DEBUG] Initializing tool: {tool_name}")

        if tool_name in self.tool_instances:
            print(f"[DEBUG] Tool {tool_name} already exists in cache")
            return self.tool_instances[tool_name]

        user_id_str = str(self.user_id)
        print(f"[DEBUG] User ID for tool initialization: {user_id_str}")

        try:
            if tool_name == "TavilySearchResults":
                print(f"[DEBUG] Creating TavilySearchResults with API key: {self.tavily_api_key[:10]}...")
                tool = TavilySearchResults(tavily_api_key=self.tavily_api_key, max_results=3)
            elif tool_name == "RAGTool":
                print(f"[DEBUG] Creating RAGTool with user_id: {user_id_str}")
                tool = RAGTool(user_id=user_id_str, api_key=self.openai_api_key)
            elif tool_name == "FlashcardGenerator":
                print(f"[DEBUG] Creating FlashcardGenerator with user_id: {user_id_str}")
                tool = FlashcardGenerator(user_id=user_id_str, api_key=self.openai_api_key)
            elif tool_name == "ExamGenerator":
                print(f"[DEBUG] Creating ExamGenerator with user_id: {user_id_str}")
                tool = ExamGenerator(user_id=user_id_str, openai_api_key=self.openai_api_key)
            elif tool_name == "DirectAnswer":
                print(f"[DEBUG] Creating DirectAnswer tool")
                tool = DirectAnswer(model=self.synthesis_model)
            else:
                print(f"[ERROR] Unknown tool requested: {tool_name}")
                raise ValueError(f"Unknown tool: {tool_name}")

            self.tool_instances[tool_name] = tool
            print(f"[DEBUG] Tool {tool_name} initialized and cached successfully")
            return tool

        except Exception as e:
            print(f"[ERROR] Failed to initialize tool {tool_name}: {str(e)}")
            raise

    async def _create_standalone_query(self, query: str, history: str) -> str:
        """Uses an LLM to rephrase a follow-up query into a standalone question."""
        print(f"[DEBUG] Creating standalone query from: '{query}'")
        print(f"[DEBUG] History length: {len(history) if history else 0}")

        # If history is short or empty, return query directly
        if not history or len(history.strip()) < 200:
            print(f"[DEBUG] No or short history, returning original query")
            return query

        system_prompt = ("Given a chat history and a follow-up question, rephrase the follow-up question to be a "
                         "standalone question that can be understood without the history. "
                         "If the question is already standalone, return it unchanged. "
                         f"If applicable add information about date at the end of the standalone query. Today is: {datetime.now()}")
        user_prompt = f"""
Chat History:
---
{history}
---
Follow-up Question: "{query}"

Standalone Question:
"""
        try:
            print(f"[DEBUG] Sending query to synthesis model for standalone conversion")
            messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
            response = await self.synthesis_model.ainvoke(messages)
            standalone_query = response.content.strip().strip('"')
            print(f"[DEBUG] Original query: '{query}' -> Standalone query: '{standalone_query}'")
            logger.info(f"Original query: '{query}'. Standalone query: '{standalone_query}'")
            return standalone_query
        except Exception as e:
            print(f"[ERROR] Failed to create standalone query: {str(e)}")
            print(f"[DEBUG] Returning original query due to error")
            return query

    def _build_generator_context(self, query: str, rag_content: Optional[str], tavily_content: Optional[str]) -> str:
        """Builds context for generator tools by combining query with available content."""
        print(f"[DEBUG] Building generator context")
        print(f"[DEBUG] - Query: '{query}'")
        print(f"[DEBUG] - RAG content length: {len(rag_content) if rag_content else 0}")
        print(f"[DEBUG] - Tavily content length: {len(tavily_content) if tavily_content else 0}")

        context_parts = [f"User Request: {query}"]

        if rag_content and len(rag_content) > 50:
            context_parts.append(f"Information from your documents:\n{rag_content}")
            print(f"[DEBUG] Added RAG content to context")

        if tavily_content and len(tavily_content) > 50:
            context_parts.append(f"Additional information from web search:\n{tavily_content}")
            print(f"[DEBUG] Added Tavily content to context")

        combined_context = "\n\n".join(context_parts)
        print(f"[DEBUG] Final combined context length: {len(combined_context)}")
        return combined_context

    def _format_generator_messages(self, tool_results: Dict[str, ToolResult]) -> str:
        """Formats messages for successful generator tools, combining them if both are present."""
        print(f"[DEBUG] Formatting generator messages")

        flashcard_success = 'FlashcardGenerator' in tool_results and tool_results['FlashcardGenerator'].success
        exam_success = 'ExamGenerator' in tool_results and tool_results['ExamGenerator'].success

        messages = []

        # Handle FlashcardGenerator
        if flashcard_success:
            try:
                flashcard_data = json.loads(tool_results['FlashcardGenerator'].content)
                if 'error' in flashcard_data:
                    print(f"[DEBUG] FlashcardGenerator JSON contains error: {flashcard_data['error']}")
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
                print(f"[DEBUG] FlashcardGenerator JSON parsing failed: {str(e)}")
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
                    print(f"[DEBUG] ExamGenerator JSON contains error: {exam_data['error']}")
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
                print(f"[DEBUG] ExamGenerator JSON parsing failed: {str(e)}")
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

        # POPRAWKA: Właściwe zwracanie wiadomości
        if len(messages) > 1:
            print(f"[DEBUG] Combining {len(messages)} generator messages")
            return "\n\n---\n\n".join(messages)
        elif len(messages) == 1:
            print(f"[DEBUG] Returning single generator message")
            return messages[0]  # NAPRAWIONE: messages[0] zamiast messages
        else:
            print(f"[DEBUG] No successful generator tools found")
            return ""

    async def final_synthesis(self, original_query: str, history: str, context: Optional[str], context_source: str,
                              tool_results: Dict[str, ToolResult]) -> str:
        """Generates the final, user-facing response, including navigational guidance and conversation history."""
        print(f"[DEBUG] Starting final synthesis")
        print(f"[DEBUG] Original query: '{original_query}'")
        print(f"[DEBUG] Context source: {context_source}")
        print(f"[DEBUG] Context length: {len(context) if context else 0}")
        print(f"[DEBUG] Tool results: {list(tool_results.keys())}")

        # Check for successful generator tools
        flashcard_success = 'FlashcardGenerator' in tool_results and tool_results['FlashcardGenerator'].success
        exam_success = 'ExamGenerator' in tool_results and tool_results['ExamGenerator'].success

        if flashcard_success or exam_success:
            print(f"[DEBUG] Generator tool(s) succeeded, formatting messages")
            return self._format_generator_messages(tool_results)

        # If a DirectAnswer tool was explicitly used and successful, return its content
        if 'DirectAnswer' in tool_results and tool_results['DirectAnswer'].success:
            print(f"[DEBUG] Returning DirectAnswer result")
            return tool_results['DirectAnswer'].content

        # If no specific generator or direct answer tool was primarily invoked,
        # create a conversational answer based on retrieved context.
        print(f"[DEBUG] Creating conversational answer using synthesis model")
        system_prompt = """
You are TorchED, a helpful AI learning assistant. Your goal is to provide a clear, accurate, and helpful final answer.
- Continue the conversation naturally, using the provided history for context.
- Use the 'Retrieved Information' to form the basis of your answer.
- Be honest about your sources. If no information was retrieved, say so.
- Format your response using Markdown for readability.
"""
        prompt_context = f"""
**Conversation History:**
{history if history else "This is the beginning of the conversation."}

**Retrieved Information (Source: {context_source}):**
---
{context or "No specific information was retrieved."}
---

Based on the history and retrieved information, answer the user's latest query.

**User's Latest Query:** "{original_query}"

**Your Answer:**
"""
        try:
            print(f"[DEBUG] Sending final synthesis request to model")
            messages = [SystemMessage(content=system_prompt), HumanMessage(content=prompt_context)]
            response = await self.synthesis_model.ainvoke(messages)
            print(f"[DEBUG] Final synthesis completed, response length: {len(response.content)}")
            return response.content
        except Exception as e:
            print(f"[ERROR] Final synthesis failed: {str(e)}")
            return f"I apologize, but I encountered an error while generating the final response: {str(e)}"

    async def invoke(self, query: str, selected_tool_names: List[str]) -> str:
        """Main execution logic for the agent, with smarter tool routing."""
        print(f"[DEBUG] ========== AGENT INVOKE START ==========")
        print(f"[DEBUG] Query: '{query}'")
        print(f"[DEBUG] Selected tool names: {selected_tool_names}")

        history_list = get_conversation_history(self.conversation_id, self.MAX_HISTORY_LENGTH)
        history_str = "\n".join(history_list)
        print(f"[DEBUG] Conversation history length: {len(history_list)} messages")

        internal_tool_map = {
            "Wiedza z plików": "RAGTool",
            "Generowanie fiszek": "FlashcardGenerator",
            "Generowanie egzaminu": "ExamGenerator",
            "Wyszukaj w internecie": "TavilySearchResults"
        }

        # Convert user-friendly names to internal tool names, maintaining order
        ordered_tools_to_execute = [
            internal_tool_map[name] for name in selected_tool_names if name in internal_tool_map
        ]
        print(f"[DEBUG] Mapped tools to execute: {ordered_tools_to_execute}")

        standalone_query = await self._create_standalone_query(query, history_str)
        context, context_source = None, "user query"
        print(f"[DEBUG] Standalone query created: '{standalone_query}'")

        tool_results: Dict[str, ToolResult] = {}

        # Variables to track content from different sources
        rag_content = None
        tavily_content = None

        # --- Tool Execution Loop ---
        print(f"[DEBUG] ========== TOOL EXECUTION LOOP START ==========")
        for tool_name in ordered_tools_to_execute:
            print(f"[DEBUG] ========== EXECUTING TOOL: {tool_name} ==========")
            logger.info(f"Attempting to execute tool: {tool_name}")

            try:
                tool = self._initialize_tool(tool_name)
                print(f"[DEBUG] Tool {tool_name} initialized successfully")
            except Exception as e:
                print(f"[ERROR] Failed to initialize tool {tool_name}: {str(e)}")
                tool_results[tool_name] = ToolResult(tool_name, "", success=False,
                                                     error=f"Initialization failed: {str(e)}")
                continue

            tool_execution_successful = False
            tool_output = None
            tool_error = None

            try:
                if tool_name == "RAGTool":
                    print(f"[DEBUG] Executing RAGTool with standalone query: '{standalone_query}'")
                    rag_output = await tool._arun(standalone_query)
                    print(f"[DEBUG] RAGTool raw output length: {len(rag_output) if rag_output else 0}")
                    print(f"[DEBUG] RAGTool output preview: {rag_output[:300] if rag_output else 'None'}...")

                    if rag_output and "error" not in rag_output.lower() and len(rag_output) > 50:
                        print(f"[DEBUG] RAGTool execution successful - storing content")
                        rag_content = rag_output
                        context = rag_output
                        context_source = "your documents"
                        tool_execution_successful = True
                    else:
                        print(f"[DEBUG] RAGTool returned insufficient context")
                        print(f"[DEBUG] - Output exists: {rag_output is not None}")
                        print(f"[DEBUG] - Contains 'error': {'error' in rag_output.lower() if rag_output else False}")
                        print(f"[DEBUG] - Length > 50: {len(rag_output) > 50 if rag_output else False}")
                        logger.info("RAGTool returned insufficient context.")
                        tool_error = rag_output if rag_output else "No content from RAGTool"

                    tool_results[tool_name] = ToolResult(tool_name, rag_output, success=tool_execution_successful,
                                                         error=tool_error)

                elif tool_name == "TavilySearchResults":
                    print(f"[DEBUG] Executing TavilySearchResults")
                    print(f"[DEBUG] Current context length: {len(context) if context else 0}")

                    print(f"[DEBUG] Proceeding with Tavily search")
                    tavily_output_raw = await tool.ainvoke({"query": standalone_query})
                    print(f"[DEBUG] Tavily raw output type: {type(tavily_output_raw)}")
                    print(f"[DEBUG] Tavily raw output: {tavily_output_raw}")

                    if tavily_output_raw and isinstance(tavily_output_raw, list):
                        print(f"[DEBUG] Processing {len(tavily_output_raw)} Tavily results")
                        combined_content = "\n\n".join(
                            [r.get('content', '') for r in tavily_output_raw if 'content' in r])
                        print(f"[DEBUG] Combined Tavily content length: {len(combined_content)}")

                        if len(combined_content) > 50:
                            print(f"[DEBUG] Tavily execution successful - storing content")
                            tavily_content = combined_content
                            if not context:
                                context = combined_content
                                context_source = "a web search"
                            else:
                                context_source = "your documents and web search"
                            tool_execution_successful = True
                        else:
                            print(f"[DEBUG] Tavily returned insufficient content")
                            logger.info("TavilySearchResults returned insufficient context.")
                            tool_error = "No substantial content from TavilySearchResults"
                    else:
                        print(f"[DEBUG] Tavily returned unexpected format")
                        tool_error = "TavilySearchResults returned unexpected format"

                    tool_results[tool_name] = ToolResult(tool_name,
                                                         combined_content if 'combined_content' in locals() else "",
                                                         success=tool_execution_successful, error=tool_error)

                elif tool_name in ["FlashcardGenerator", "ExamGenerator"]:
                    print(f"[DEBUG] Executing {tool_name}")
                    print(f"[DEBUG] Available RAG content: {len(rag_content) if rag_content else 0} chars")
                    print(f"[DEBUG] Available Tavily content: {len(tavily_content) if tavily_content else 0} chars")

                    # Build context for generator - will always have at least the user query
                    generator_context = self._build_generator_context(query, rag_content, tavily_content)

                    generator_input = json.dumps({
                        "description": generator_context,
                        "query": query
                    })
                    print(f"[DEBUG] Generator input prepared, length: {len(generator_input)}")

                    tool_output = await tool._arun(generator_input)
                    print(f"[DEBUG] {tool_name} output length: {len(tool_output) if tool_output else 0}")
                    print(f"[DEBUG] {tool_name} output preview: {tool_output[:300] if tool_output else 'None'}...")

                    tool_execution_successful = True

                    # Check for error in JSON output
                    try:
                        parsed_output = json.loads(tool_output)
                        if 'error' in parsed_output:
                            print(f"[DEBUG] {tool_name} returned error in JSON: {parsed_output['error']}")
                            tool_execution_successful = False
                            tool_error = parsed_output['error']
                        else:
                            print(f"[DEBUG] {tool_name} executed successfully")
                    except json.JSONDecodeError:
                        print(f"[DEBUG] {tool_name} output is not valid JSON, checking for error keywords")
                        if "error" in tool_output.lower() or "failed" in tool_output.lower():
                            print(f"[DEBUG] {tool_name} output contains error keywords")
                            tool_execution_successful = False
                            tool_error = tool_output

                    tool_results[tool_name] = ToolResult(tool_name, tool_output, success=tool_execution_successful,
                                                         error=tool_error)

                else:
                    print(f"[WARNING] Tool {tool_name} not explicitly handled in routing logic")
                    logger.warning(
                        f"Tool {tool_name} is in selected_tools but not explicitly handled in routing logic.")
                    tool_results[tool_name] = ToolResult(tool_name, "Tool not handled by router logic.", success=False,
                                                         error="Unhandled tool")

            except Exception as e:
                print(f"[ERROR] Exception during {tool_name} execution: {str(e)}")
                logger.error(f"Error during execution of {tool_name}: {e}", exc_info=True)
                tool_results[tool_name] = ToolResult(tool_name, str(e), success=False, error=str(e))

        print(f"[DEBUG] ========== TOOL EXECUTION LOOP END ==========")
        print(f"[DEBUG] Proceeding to final synthesis with all tool results")
        result = await self.final_synthesis(query, history_str, context, context_source, tool_results)
        print(f"[DEBUG] ========== AGENT INVOKE END ==========")
        return result
