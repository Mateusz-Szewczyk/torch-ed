import os
import logging
from langchain_anthropic import ChatAnthropic
from langchain.agents import AgentType, initialize_agent
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory

# Import tools
from tools import FlashcardGenerator
from tools import RAGTool
from langchain_community.tools import TavilySearchResults  # Import Tavily Search tool

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def initialize_agent_and_tools(user_id, model_name):
    """Initialize the agent and tools with proper configuration."""

    # Initialize Anthropic API key
    anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
    if not anthropic_api_key:
        raise ValueError("Anthropic API key is not set. Please set the ANTHROPIC_API_KEY environment variable.")

    # Initialize Tavily API key
    tavily_api_key = os.getenv('TAVILY_API_KEY')
    if not tavily_api_key:
        raise ValueError("Tavily API key is not set. Please set the TAVILY_API_KEY environment variable.")

    # Initialize the language model
    llm = ChatAnthropic(
        model_name=model_name,
        anthropic_api_key=anthropic_api_key,
        temperature=0
    )

    # Initialize tools
    try:
        flashcard_tool = FlashcardGenerator(
            model_name=model_name,
            anthropic_api_key=anthropic_api_key
        )
        logger.info("Initialized FlashcardGenerator tool.")
    except Exception as e:
        logger.error(f"Failed to initialize FlashcardGenerator tool: {e}")
        raise

    # Initialize the RAG tool
    rag_tool = RAGTool(
        user_id=user_id,
        model_name=model_name,
        anthropic_api_key=anthropic_api_key
    )

    # Initialize Tavily Search tool
    tavily_tool = TavilySearchResults(
        max_results=5,
        search_depth="advanced",
        include_answer=True,
        include_raw_content=True,
        include_images=True,
    )
    logger.info("Initialized TavilySearchResults tool.")

    # Create list of tools
    tools = [flashcard_tool, rag_tool, tavily_tool]

    # Create the prompt template
    tool_descriptions = "\n".join([f"{tool.name}: {tool.description}" for tool in tools])

    template = f"""Jesteś pomocnym asystentem AI, który używa narzędzi do pomocy użytkownikom w nauce i znajdowaniu informacji. Adaptujesz się do języka użytkownika (polskiego) i dostarczasz jak najlepszą odpowiedź, korzystając z dostępnych narzędzi.
    Na początku zaplanuj dokładnie swoje działania, pierwsza myśl powinna polegać na planie działania!!!
    Twoje myśli i wszystkie działania powinny być w języku użytkownika. Twoimi użytkownikami będą głównie ludzie polsko i angielkojęzyczni.
    Masz dostęp do następujących narzędzi:

    {tool_descriptions}

    Dla każdego pytania najpierw zastanów się, które narzędzie będzie najbardziej odpowiednie do zebrania niezbędnych informacji.

    Najpierw użyj odpowiednich narzędzi, aby zebrać wszystkie istotne dane potrzebne do odpowiedzi na prośbę użytkownika.

    **Z NARZĘDZIA flashcard_generator KORZYSTAJ TYLKO PO ZDOBYCIU INFORMACJI, NA SAMYM KONCU DZIAŁANIA!!!**

    Na końcu zadania, jeśli to konieczne, użyj narzędzia 'flashcard_generator' do stworzenia fiszek.

    Jeśli żadne z narzędzi nie jest odpowiednie, możesz prowadzić bezpośrednią rozmowę z użytkownikiem.

    Pamiętaj, aby dostarczyć kompleksową i pełną odpowiedź.

    Wykryj język wejściowy i odpowiedz w tym samym języku.

    Najnowsza wiadomość: {input}
    """

    prompt = PromptTemplate(
        input_variables=["input", "agent_scratchpad"],
        template=template
    )

    # Initialize memory
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        input_key="input",
        return_messages=True
    )

    # Initialize the agent using initialize_agent
    agent = initialize_agent(
        tools=tools,
        llm=llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        prompt=prompt,
        memory=memory,
        verbose=True,
        max_iterations=5,
        handle_parsing_errors=True
    )

    return agent

def agent_response(user_id: str, query: str, model_name="claude-3-haiku-20240307") -> str:
    """
    Generates an answer based on the user's query.

    Args:
        user_id (str): The ID of the user.
        query (str): The user's query.

    Returns:
        str: Generated answer.
    """
    logger.info(f"Generating answer for user_id: {user_id} with query: '{query}'")

    try:
        # Initialize agent
        agent = initialize_agent_and_tools(user_id, model_name)

        # Use the agent to process the query
        response = agent.run(query)
        return response

    except Exception as e:
        logger.error(f"Error generating answer: {e}", exc_info=True)
        return f"An error occurred while generating the answer: {str(e)}"

# Example usage
if __name__ == "__main__":
    user_id = "user123"
    query = "Czy wiesz, jakie są korzyści z korzystania z architektury Astute RAG?"

    answer = agent_response(user_id, query)
    print("Answer:")
    print(answer)