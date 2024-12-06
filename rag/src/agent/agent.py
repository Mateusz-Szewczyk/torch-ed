import os
import logging
from langchain_anthropic import ChatAnthropic
from langchain.agents import AgentType, initialize_agent
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory

# Import narzędzi
from .tools import FlashcardGenerator
from .tools import RAGTool
from langchain_community.tools import TavilySearchResults  # Import narzędzia Tavily Search

# Konfiguracja logowania
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def initialize_agent_and_tools(user_id, model_name, anthropic_api_key, tavily_api_key):
    """Inicjalizuje agenta i narzędzia z odpowiednią konfiguracją."""

    # Inicjalizacja modelu językowego
    llm = ChatAnthropic(
        model_name=model_name,
        anthropic_api_key=anthropic_api_key,
        temperature=0
    )

    # Inicjalizacja narzędzi
    try:
        flashcard_tool = FlashcardGenerator(
            model_name=model_name,
            anthropic_api_key=anthropic_api_key
        )
        logger.info("Zainicjalizowano narzędzie FlashcardGenerator.")
    except Exception as e:
        logger.error(f"Nie udało się zainicjalizować narzędzia FlashcardGenerator: {e}")
        raise

    # Inicjalizacja narzędzia RAGTool
    rag_tool = RAGTool(
        user_id=user_id,
        model_name=model_name,
        anthropic_api_key=anthropic_api_key
    )

    # Inicjalizacja narzędzia Tavily Search
    tavily_tool = TavilySearchResults(
        tavily_api_key=tavily_api_key,
        max_results=5,
        search_depth="advanced",
        include_answer=True,
        include_raw_content=True,
        include_images=True,
    )
    logger.info("Zainicjalizowano narzędzie TavilySearchResults.")

    # Tworzenie listy narzędzi
    tools = [flashcard_tool, rag_tool, tavily_tool]

    # Tworzenie szablonu promptu
    tool_descriptions = "\n".join([f"{tool.name}: {tool.description}" for tool in tools])

    template = f"""Jesteś pomocnym asystentem AI, który używa narzędzi do pomocy użytkownikom w nauce i znajdowaniu informacji. Adaptujesz się do języka użytkownika (polskiego) i dostarczasz jak najlepszą odpowiedź, korzystając z dostępnych narzędzi.
            Na początku zaplanuj dokładnie swoje działania, pierwsza myśl powinna polegać na planie działania!!!
            Twoje myśli i wszystkie działania powinny być w języku użytkownika. Twoimi użytkownikami będą głównie ludzie polsko i angielkojęzyczni.
            Masz dostęp do następujących narzędzi:
            
            {tool_descriptions}
            
            Dla każdego pytania najpierw zastanów się, które narzędzie będzie najbardziej odpowiednie do zebrania niezbędnych informacji.
            
            Najpierw użyj odpowiednich narzędzi, aby zebrać wszystkie istotne dane potrzebne do odpowiedzi na prośbę użytkownika.
            
            **Z NARZĘDZIA flashcard_generator KORZYSTAJ TYLKO PO ZDOBYCIU INFORMACJI, NA SAMYM KOŃCU DZIAŁANIA!!!**
            
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

    # Inicjalizacja pamięci
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        input_key="input",
        return_messages=True
    )

    # Inicjalizacja agenta za pomocą initialize_agent
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

def agent_response(user_id: str, query: str, model_name="claude-3-haiku-20240307", anthropic_api_key=None, tavily_api_key=None) -> str:
    """
    Generuje odpowiedź na podstawie zapytania użytkownika.

    Args:
        user_id (str): ID użytkownika.
        query (str): Zapytanie użytkownika.
        model_name (str): Nazwa modelu do użycia.
        anthropic_api_key (str): Klucz API dla Anthropic.
        tavily_api_key (str): Klucz API dla Tavily.

    Returns:
        str: Wygenerowana odpowiedź.
    """
    logger.info(f"Generowanie odpowiedzi dla user_id: {user_id} z zapytaniem: '{query}'")

    # Sprawdzenie kluczy API
    if not anthropic_api_key:
        anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        if not anthropic_api_key:
            raise ValueError("Anthropic API key is not set. Please set the ANTHROPIC_API_KEY environment variable.")

    if not tavily_api_key:
        tavily_api_key = os.getenv('TAVILY_API_KEY')
        if not tavily_api_key:
            raise ValueError("Tavily API key is not set. Please set the TAVILY_API_KEY environment variable.")

    try:
        # Inicjalizacja agenta
        agent = initialize_agent_and_tools(user_id, model_name, anthropic_api_key, tavily_api_key)

        # Przetwarzanie zapytania za pomocą agenta
        response = agent.run(query)
        return response

    except Exception as e:
        logger.error(f"Błąd podczas generowania odpowiedzi: {e}", exc_info=True)
        return f"Wystąpił błąd podczas generowania odpowiedzi: {str(e)}"

# Przykład użycia
if __name__ == "__main__":
    user_id = "user123"
    query = "Czy wiesz, jakie są korzyści z korzystania z architektury Astute RAG?"

    # Pobierz klucze API z zmiennych środowiskowych
    anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
    tavily_api_key = os.getenv('TAVILY_API_KEY')

    answer = agent_response(user_id, query, anthropic_api_key=anthropic_api_key, tavily_api_key=tavily_api_key)
    print("Answer:")
    print(answer)
