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

    template = f"""You are a helpful AI assistant that uses tools to help users learn and find information.
    You have access to the following tools:

    {tool_descriptions}

    For any question, first think about which tool would be most appropriate.

    - **Flashcard Generator**: Use this tool when the user wants to create flashcards. Pass the user's entire prompt directly as a single string in the action input. Ensure that the flashcards are detailed and returned in JSON format as specified.

    - **Tavily Search Tool**: [Description remains the same]

    - **RAG Tool**: [Description remains the same]

    If none of the tools are appropriate, you can have a direct conversation with the user.

    **Instructions**:

    When responding, use the following format (without deviation):

    Question: the user's question Thought: your reasoning about which tool to use Action: the action to take, must be one of [{', '.join([tool.name for tool in tools])}] Action Input: the input to the action Observation: the result of the action ... (this Thought/Action/Action Input/Observation can repeat N times) Thought: I now know the final answer Final Answer: the final answer to the user's question (if generating flashcards, return them in JSON format)

    Always explain your reasoning before providing the final answer.

    {{agent_scratchpad}}"""

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
    query = "Create flashcards for each element with the name, symbol, and atomic number on one side, and additional information like properties, uses, and position on the table on the other side."

    answer = agent_response(user_id, query)
    print("Answer:")
    print(answer)
