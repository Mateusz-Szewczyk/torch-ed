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
        # A lightweight model for synthesis and query rewriting
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

        # Ensure user_id is a string when initializing tools
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

        if not history:
            print(f"[DEBUG] No history, returning original query")
            return query

        system_prompt = "Given a chat history and a follow-up question, rephrase the follow-up question to be a standalone question that can be understood without the history. If the question is already standalone, return it unchanged."
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

    async def _get_prioritized_context(self, query: str, selected_tools: List[str]) -> Tuple[Optional[str], str]:
        """Implements the RAG-first content sourcing strategy."""
        print(f"[DEBUG] Getting prioritized context for query: '{query}'")
        print(f"[DEBUG] Selected tools: {selected_tools}")

        source_name = "general knowledge"
        retrieved_context = None

        # Prioritize RAGTool if selected
        if "RAGTool" in selected_tools:
            print(f"[DEBUG] RAGTool is selected, attempting to retrieve context...")
            logger.info("Attempting to retrieve context from RAGTool...")
            rag_tool = self._initialize_tool("RAGTool")
            try:
                print(f"[DEBUG] Calling RAGTool._arun with query: '{query}'")
                rag_result = await rag_tool._arun(query)
                print(f"[DEBUG] RAGTool result length: {len(rag_result) if rag_result else 0}")
                print(f"[DEBUG] RAGTool result preview: {rag_result[:200] if rag_result else 'None'}...")

                if rag_result and "error" not in rag_result.lower() and len(rag_result) > 50:
                    print(f"[DEBUG] RAGTool provided sufficient context ({len(rag_result)} chars)")
                    logger.info("Successfully retrieved context from RAGTool.")
                    retrieved_context = rag_result
                    source_name = "your documents"
                else:
                    print(
                        f"[DEBUG] RAGTool context insufficient - Length: {len(rag_result) if rag_result else 0}, Contains error: {'error' in rag_result.lower() if rag_result else False}")
            except Exception as e:
                print(f"[ERROR] RAGTool execution failed: {str(e)}")
                logger.error(f"Error executing RAGTool: {e}")

        # If RAGTool didn't provide context or wasn't selected, try Tavily if selected
        if not retrieved_context and "TavilySearchResults" in selected_tools:
            print(f"[DEBUG] RAG provided no context, attempting TavilySearchResults...")
            logger.info(
                "RAG provided no context or wasn't selected. Attempting to retrieve from TavilySearchResults...")
            tavily_tool = self._initialize_tool("TavilySearchResults")
            try:
                print(f"[DEBUG] Calling TavilySearchResults with query: '{query}'")
                search_results = await tavily_tool.ainvoke({"query": query})
                print(f"[DEBUG] Tavily search results type: {type(search_results)}")
                print(f"[DEBUG] Tavily search results length: {len(search_results) if search_results else 0}")

                if search_results and isinstance(search_results, list):
                    print(f"[DEBUG] Processing {len(search_results)} Tavily results")
                    combined_content = "\n\n".join([r.get('content', '') for r in search_results if 'content' in r])
                    print(f"[DEBUG] Combined Tavily content length: {len(combined_content)}")

                    if len(combined_content) > 50:
                        print(f"[DEBUG] Tavily provided sufficient context ({len(combined_content)} chars)")
                        logger.info("Successfully retrieved context from TavilySearchResults.")
                        retrieved_context = combined_content
                        source_name = "a web search"
                    else:
                        print(f"[DEBUG] Tavily content too short: {len(combined_content)} chars")
                else:
                    print(f"[DEBUG] Tavily returned unexpected format or empty results")
            except Exception as e:
                print(f"[ERROR] TavilySearchResults execution failed: {str(e)}")
                logger.error(f"Error executing Tavily Search: {e}")

        if not retrieved_context:
            print(f"[DEBUG] No substantial context found from any source")
            logger.info("No substantial context found from RAG or Tavily.")
        else:
            print(f"[DEBUG] Final context source: {source_name}, length: {len(retrieved_context)}")

        return retrieved_context, source_name

    async def final_synthesis(self, original_query: str, history: str, context: Optional[str], context_source: str,
                              tool_results: Dict[str, ToolResult]) -> str:
        """Generates the final, user-facing response, including navigational guidance and conversation history."""
        print(f"[DEBUG] Starting final synthesis")
        print(f"[DEBUG] Original query: '{original_query}'")
        print(f"[DEBUG] Context source: {context_source}")
        print(f"[DEBUG] Context length: {len(context) if context else 0}")
        print(f"[DEBUG] Tool results: {list(tool_results.keys())}")

        if 'FlashcardGenerator' in tool_results and tool_results['FlashcardGenerator'].success:
            print(f"[DEBUG] Returning FlashcardGenerator result")

            try:
                flashcard_data = json.loads(tool_results['FlashcardGenerator'].content)
                if 'error' in flashcard_data:
                    print(f"[DEBUG] FlashcardGenerator JSON contains error: {flashcard_data['error']}")
                    return f"Napotkałem problem podczas tworzenia fiszek:\n{flashcard_data['error']}"

                topic = flashcard_data.get('topic', 'Twoje fiszki')
                num_flashcards = len(flashcard_data.get('flashcards', []))

                nav_msg = f"""## ✅ Fiszki zostały pomyślnie utworzone!

    **📚 Temat:** {topic}  
    **🔢 Liczba fiszek:** {num_flashcards} (ilość fiszek może się minimalnie różnić od podanej w zapytaniu)

    ### 🎯 Co dalej?
    Twoje nowe fiszki czekają na Ciebie! Możesz teraz:
    - 📖 **Przeglądać** wszystkie swoje fiszki
    - 🧠 **Ćwiczyć** w trybie nauki
    - 📊 **Śledzić** swoje postępy

    👈 Przejdź do sekcji **'Fiszki'** w menu nawigacyjnym po lewej stronie, aby rozpocząć naukę!"""

                return nav_msg

            except (json.JSONDecodeError, KeyError) as e:
                print(f"[DEBUG] FlashcardGenerator JSON parsing failed: {str(e)}")
                return """## ✅ Fiszki zostały pomyślnie utworzone!

    ### 🎯 Co dalej?
    Twoje nowe fiszki są gotowe do nauki! 

    👈 Przejdź do sekcji **'Fiszki'** w menu nawigacyjnym po lewej stronie, aby:
    - 📖 Przeglądać swoje fiszki
    - 🧠 Rozpocząć sesję nauki
    - 📊 Monitorować postępy"""

        if 'ExamGenerator' in tool_results and tool_results['ExamGenerator'].success:
            print(f"[DEBUG] Returning ExamGenerator result")
            try:
                exam_data = json.loads(tool_results['ExamGenerator'].content)
                if 'error' in exam_data:
                    print(f"[DEBUG] ExamGenerator JSON contains error: {exam_data['error']}")
                    return f"Napotkałem problem podczas tworzenia egzaminu:\n{exam_data['error']}"

                topic = exam_data.get('topic', 'Twój egzamin')
                num_questions = exam_data.get('num_of_questions', len(exam_data.get('questions', [])))

                nav_msg = f"""## ✅ Egzamin został pomyślnie utworzony!

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

                return nav_msg

            except (json.JSONDecodeError, KeyError) as e:
                print(f"[DEBUG] ExamGenerator JSON parsing failed: {str(e)}")
                return """## ✅ Egzamin został pomyślnie utworzony!

    ### 🎯 Co dalej?
    Twój nowy egzamin czeka na rozwiązanie!

    👈 Przejdź do sekcji **'Egzaminy'** w menu nawigacyjnym po lewej stronie, aby:
    - 📋 Przystąpić do testu
    - ⏱️ Sprawdzić swoje wyniki
    - 📈 Przeanalizować odpowiedzi

    ### 💡 Wskazówka
    Możesz rozwiązywać egzamin wielokrotnie, aby doskonalić swoją wiedzę!"""

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
        context, context_source = None, "general knowledge"  # Initialize context to None and default source
        print(f"[DEBUG] Standalone query created: '{standalone_query}'")

        tool_results: Dict[str, ToolResult] = {}

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
                        print(f"[DEBUG] RAGTool execution successful - setting context")
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

                    # Only run if RAGTool hasn't already provided sufficient context
                    if not context or len(context) < 50:
                        print(f"[DEBUG] Context insufficient, proceeding with Tavily search")
                        tavily_output_raw = await tool.ainvoke({"query": standalone_query})
                        print(f"[DEBUG] Tavily raw output type: {type(tavily_output_raw)}")
                        print(f"[DEBUG] Tavily raw output: {tavily_output_raw}")

                        if tavily_output_raw and isinstance(tavily_output_raw, list):
                            print(f"[DEBUG] Processing {len(tavily_output_raw)} Tavily results")
                            combined_content = "\n\n".join(
                                [r.get('content', '') for r in tavily_output_raw if 'content' in r])
                            print(f"[DEBUG] Combined Tavily content length: {len(combined_content)}")

                            if len(combined_content) > 50:
                                print(f"[DEBUG] Tavily execution successful - setting context")
                                context = combined_content
                                context_source = "a web search"
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
                    else:
                        print(f"[DEBUG] Skipping Tavily - context already available from {context_source}")
                        logger.info(f"Skipping {tool_name} as context already retrieved from {context_source}.")
                        tool_results[tool_name] = ToolResult(tool_name, "Skipped - context already available.",
                                                             success=True)

                elif tool_name in ["FlashcardGenerator", "ExamGenerator"]:
                    print(f"[DEBUG] Executing {tool_name}")
                    print(f"[DEBUG] Available context length: {len(context) if context else 0}")

                    # Sprawdź czy to zapytanie o ogólną wiedzę czy o konkretne pliki
                    query_lower = query.lower()
                    is_general_knowledge_request = any(keyword in query_lower for keyword in [
                        "język", "matematyka", "historia", "geografia", "fizyka", "chemia",
                        "biologia", "podstawowe", "nauka", "słownictwo", "gramatyka", "japoński",
                        "angielski", "francuski", "niemiecki", "hiszpański", "włoski", "rosyjski"
                    ]) and not any(file_keyword in query_lower for file_keyword in [
                        "plik", "dokument", "materiał", "tekst", "z pliku", "na podstawie"
                    ])

                    if context:
                        # Standardowa ścieżka z kontekstem z plików/internetu
                        generator_input = json.dumps({
                            "description": context,
                            "query": query
                        })
                        print(f"[DEBUG] Generator input prepared from context, length: {len(generator_input)}")

                    elif is_general_knowledge_request:
                        # Nowa ścieżka - generowanie z ogólnej wiedzy
                        print(f"[DEBUG] Detected general knowledge request, generating from LLM knowledge")
                        generator_input = json.dumps({
                            "description": f"Generate educational content based on general knowledge for: {query}",
                            "query": query,
                            "use_general_knowledge": True
                        })
                        print(f"[DEBUG] Generator input prepared from general knowledge")

                    else:
                        # Brak kontekstu i nie jest to zapytanie o ogólną wiedzę
                        print(
                            f"[DEBUG] {tool_name} cannot execute - no context available and not general knowledge request")
                        tool_output = json.dumps({
                            "error": f"Aby wygenerować {tool_name.replace('Generator', '').lower()}, potrzebuję kontekstu. Proszę wybierz 'Wiedza z plików' lub 'Wyszukaj w internecie', albo przeformułuj zapytanie tak, aby dotyczyło ogólnej wiedzy."
                        }, ensure_ascii=False)
                        tool_execution_successful = False
                        tool_error = "No context available for generator tool."
                        tool_results[tool_name] = ToolResult(tool_name, tool_output, success=tool_execution_successful,
                                                             error=tool_error)
                        continue

                    print(f"[DEBUG] Generator input preview: {generator_input[:200]}...")

                    tool_output = await tool._arun(generator_input)
                    print(f"[DEBUG] {tool_name} output length: {len(tool_output) if tool_output else 0}")
                    print(f"[DEBUG] {tool_name} output preview: {tool_output[:300] if tool_output else 'None'}...")

                    tool_execution_successful = True  # Assume success unless error handling below indicates otherwise

                    # Check for an error message within the JSON output
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
                        # Not JSON, maybe raw error message or unexpected output
                        if "error" in tool_output.lower() or "failed" in tool_output.lower():
                            print(f"[DEBUG] {tool_name} output contains error keywords")
                            tool_execution_successful = False
                            tool_error = tool_output

                    tool_results[tool_name] = ToolResult(tool_name, tool_output, success=tool_execution_successful,
                                                         error=tool_error)

                    # If a generator tool ran successfully, it's usually the final step
                    if tool_execution_successful:
                        print(f"[DEBUG] {tool_name} successful, proceeding to final synthesis")
                        result = await self.final_synthesis(query, history_str, context, context_source, tool_results)
                        print(f"[DEBUG] ========== AGENT INVOKE END (EARLY RETURN) ==========")
                        return result

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
