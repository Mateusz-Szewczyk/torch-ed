# agent.py

import os
import logging
from typing import Callable, Dict, List, Optional
import json
import uuid

from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import JsonOutputParser
from langchain.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, validator
from typing import Literal
from langchain_community.tools.tavily_search.tool import TavilySearchResults
from dotenv import load_dotenv
from pathlib import Path

from ..models import Conversation
from .tools import FlashcardGenerator, RAGTool
from .agent_memory import (
    create_memory,
    get_latest_checkpoint,
    get_conversation_history,
)
from langchain.tools import BaseTool  # Ensure BaseTool is correctly imported
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

# ------------------------------
# 0. Load Environment Variables
# ------------------------------

# Set the path to the .env file located in the project directory
env_path = Path(__file__).resolve().parents[2] / '.env'  # Adjust the number of `parents` according to your actual structure
load_dotenv(dotenv_path=env_path)

# ------------------------------
# 1. Configure Logging
# ------------------------------

logger = logging.getLogger(__name__)


# ------------------------------
# 2. Define Routing Model
# ------------------------------

class RouteQuery(BaseModel):
    """Route a user query to the most relevant datasources."""

    datasources: List[Literal["FlashcardGenerator", "RAGTool", "TavilySearchResults", "DirectAnswer"]] = Field(
        ...,
        description="Given a user question, choose which datasources would be most relevant for answering it."
    )

    @validator('datasources', pre=True)
    def ensure_list(cls, v):
        if isinstance(v, str):
            return [v]
        return v

# ------------------------------
# 3. Define Tools with Descriptions
# ------------------------------

class DirectAnswer(BaseTool):
    name: str = "DirectAnswer"
    description: str = """This tool provides direct answers to user questions based on the conversation context.
It generates concise and accurate responses without relying on external data sources.
Keywords that trigger this tool include questions starting with "Cześć, czy wiesz", "Jak mam na imię", etc.
"""

    model: Optional[ChatAnthropic] = None

    def __init__(self, model: ChatAnthropic):
        super().__init__()
        self.model = model

    def _run(self, query: str, aggregated_context: str = "") -> str:
        logger.debug(f"DirectAnswer tool is processing query: {query}")
        if self.model is None:
            raise ValueError("ChatAnthropic model is not initialized")

        try:
            system_prompt = """You are a helpful assistant that provides direct answers to user questions based on the conversation context.
            You will use context as a helper to answer questions.
            Please answer directly to the user's question without referring to context.
            You will create a well-written and concise response that addresses the user's query."""

            # Combine context and query if context is available
            full_query = f"Context:\n{aggregated_context}\n\nQuestion: {query}" if aggregated_context else query

            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", "{question}")
            ])

            print(prompt)

            # Ensure the query is passed correctly
            messages = prompt.format_messages(question=full_query)
            logger.debug(f"Generating direct answer with messages: {messages}")
            print(messages)
            response = self.model.invoke(messages).content

            return response
        except Exception as e:
            logger.error(f"Error generating direct answer: {e}", exc_info=True)
            return "Przepraszam, wystąpił problem z generowaniem odpowiedzi."

    async def _arun(self, query: str) -> str:
        raise NotImplementedError("DirectAnswer does not support async operations.")

# ------------------------------
# 4. Implement Classification Chain
# ------------------------------
def create_classification_chain(model: ChatAnthropic, tools: List[BaseTool]) -> Callable[[str], RouteQuery]:
    """
    Creates a classification chain that routes user questions to appropriate datasources.

    Args:
        model (ChatAnthropic): The language model to use for classification.
        tools (List[BaseTool]): A list of available tools with their descriptions.

    Returns:
        Callable[[str], RouteQuery]: A function that takes a user question and returns the routed datasources.
    """
    # Generate tool descriptions
    tools_descriptions = "\n\n".join([
        f"{idx + 1}. {tool.name}\n   Description: {tool.description}"
        for idx, tool in enumerate(tools)
    ])

    # Define the system prompt with properly escaped curly braces
    system_prompt = f"""You are an expert at routing a user question to the appropriate datasource.

Based on the context and content of the user's question, determine which tools should be used to provide the most accurate and helpful response. Choose from the following options:

"{tools_descriptions}"

Provide your answer using the following JSON schema:
{{{{
    "datasources": []
}}}}
Here are some examples:

Question: "Jak korzystać z FlashcardGenerator do nauki języka Python?"
Response:
{{{{
    "datasources": ["FlashcardGenerator"]
}}}}

Question: "Stwórz proszę na podstawie danych które Ci wysłałem 20 fiszek do nauki przed egzaminem z programowania obiektowego."
Response:
{{{{
    "datasources": ["RAGTool", "FlashcardGenerator"]
}}}}

Question: "Cześć, czy wiesz jak mam na imię?"
Response:
{{{{
    "datasources": ["DirectAnswer"]
}}}}

MAKE SURE THAT YOUR RESPONSE IS IN CORRECT JSON FORMAT AND ONLY CONTAINS THE JSON OBJECT WITHOUT ANY ADDITIONAL TEXT.

DO NOT INCLUDE ANY EXPLANATIONS, COMMENTS, OR ADDITIONAL TEXT IN YOUR RESPONSE. ONLY RETURN THE JSON OBJECT.
"""

    # Define the human prompt
    human_prompt = "{question}"

    # Create the prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", human_prompt),
    ])

    # Create the JSON parser
    parser = JsonOutputParser()

    # Create the chain by composing prompt, model, and parser
    chain = (
        prompt
        | model
        | parser
    )

    def classify(question: str) -> RouteQuery:
        """
        Classifies a user question and routes it to the appropriate datasources.

        Args:
            question (str): The user's question.

        Returns:
            RouteQuery: An object containing the list of datasources to use.
        """
        try:
            logger.debug("Invoking classification chain with question.")
            response = chain.invoke({"question": question})
            logger.debug(f"Raw classification response: {response}")  # Log the full response from the model

            # Check if the response is a dictionary
            if not isinstance(response, dict):
                logger.error(f"Expected response to be a dict, but got: {type(response)}")
                raise ValueError("Invalid response format.")

            # Check if 'datasources' key is present
            if 'datasources' not in response:
                logger.error(f"'datasources' key missing in response: {response}")
                raise ValueError("Missing 'datasources' in response.")

            datasources = response['datasources']
            logger.debug(f"Extracted datasources: {datasources}")

            # Validate that all datasources are allowed
            allowed_datasources = {"FlashcardGenerator", "RAGTool", "TavilySearchResults", "DirectAnswer"}
            invalid_datasources = set(datasources) - allowed_datasources
            if invalid_datasources:
                logger.error(f"Invalid datasource(s) detected: {invalid_datasources}")
                raise ValueError(f"Invalid datasource(s): {', '.join(invalid_datasources)}")

            return RouteQuery(datasources=datasources)
        except ValueError as ve:
            logger.error(f"ValueError during classification: {ve}")
            # Fallback to 'DirectAnswer' datasource if parsing fails
            return RouteQuery(datasources=["DirectAnswer"])
        except Exception as e:
            logger.error(f"Error parsing classification response: {e}")
            # Fallback to 'DirectAnswer' datasource in case of other exceptions
            return RouteQuery(datasources=["DirectAnswer"])

    return classify

# ------------------------------
# 5. Implement Tool Chains
# ------------------------------

def create_tool_chains(flashcard_tool: FlashcardGenerator, rag_tool: RAGTool, tavily_tool: TavilySearchResults,
                       model: ChatAnthropic) -> Dict[str, Callable[[str], str]]:
    flashcard_chain = lambda input_text: flashcard_tool.run(input_text)
    rag_chain = lambda input_text: rag_tool.run(input_text)

    # Utworzenie DirectAnswer jako osobnego narzędzia
    direct_answer_tool = DirectAnswer(model=model)
    direct_answer_chain = lambda input_text: direct_answer_tool.run(input_text)

    def tavily_chain(input_text: str) -> str:
        """
        Processes the user's query using TavilySearchResults and returns the response as a string.

        Args:
            input_text (str): User query.

        Returns:
            str: Response from TavilySearchResults or an error message.
        """
        try:
            logger.debug(f"Invoking TavilySearchResults with query: {input_text}")
            results = tavily_tool.invoke({"query": input_text})
            logger.debug(f"TavilySearchResults response: {results}")

            # Check if results is a list of dictionaries
            if isinstance(results, list):
                contents = [result.get('content', '') for result in results if 'content' in result]
                return "\n".join(contents) if contents else "Przepraszam, nie mogę znaleźć odpowiedzi na to pytanie."

            # Check if results is a dictionary with 'answer' key
            elif isinstance(results, dict) and 'answer' in results:
                return results['answer']

            # Other response formats
            else:
                logger.error(f"Unexpected response format from TavilySearchResults: {results}")
                return "Przepraszam, nie mogę znaleźć odpowiedzi na to pytanie."

        except Exception as e:
            logger.error(f"Error invoking TavilySearchResults: {e}")
            return "Przepraszam, wystąpił problem z wyszukiwaniem."

    tool_chains = {
        "FlashcardGenerator": flashcard_chain,
        "RAGTool": rag_chain,
        "TavilySearchResults": tavily_chain,
        "DirectAnswer": direct_answer_chain
    }

    return tool_chains

# ------------------------------
# 6. Implement Router Chain
# ------------------------------

def create_router_chain(tool_chains: Dict[str, Callable[[str], str]]) -> Callable[[RouteQuery, str, str], str]:
    def routing_function(classification: RouteQuery, query: str, description: str) -> str:
        datasources = classification.datasources
        logger.info(f"Routing to datasources: {datasources}")

        context = ""  # Initialize empty context
        responses = []

        for datasource in datasources:
            tool_function = tool_chains.get(datasource, tool_chains["DirectAnswer"])
            try:
                if datasource == "TavilySearchResults":
                    current_query = query  # Original user query
                    response = tool_function(current_query)
                elif datasource == "FlashcardGenerator":
                    # Pass both description and query as a JSON string
                    input_data = json.dumps({"description": description, "query": query}, ensure_ascii=False)
                    response = tool_function(input_data)
                else:
                    # For other tools, augment the query with context if available
                    current_query = f"{context}\nQuestion: {query}" if context else query
                    response = tool_function(current_query)

                responses.append(response)
                # Update context with the tool's response if it's not an error message
                if not response.startswith("Przepraszam"):
                    context += f"\n{response}"
            except Exception as e:
                # Log the error and add a user-friendly message
                logger.error(f"Error using tool {datasource}: {e}")
                responses.append(f"Przepraszam, wystąpił problem z narzędziem {datasource}.")

        combined_response = "\n".join(responses) if responses else "Przepraszam, nie mogę odpowiedzieć na to pytanie."
        return combined_response

    return routing_function

# ------------------------------
# 7. Implement Final Answer Function
# ------------------------------

def final_answer(context: str, query: str, model: ChatAnthropic) -> str:
    """
    Finalizes the response by generating a well-formatted answer based on the collected context.

    Args:
        context (str): The aggregated context from various tools.
        query (str): The original user query.
        model (ChatAnthropic): The language model instance to generate the final answer.

    Returns:
        str: The finalized, well-formatted answer.
    """
    try:
        system_prompt = (
            "Jesteś pomocnym asystentem, który potrafi syntetyzować informacje z różnych źródeł i przedstawiać je w przejrzystej, zrozumiałej formie. "
            "Na podstawie poniższego kontekstu oraz pytania użytkownika, stwórz spójną i dobrze napisaną odpowiedź."
            "Użytkownik poda kontekst wiadomości z poprzednich wymian, a Ty masz za zadanie odpowiedzieć na pytanie w sposób zrozumiały i pomocny."
            "Kontekst pomoże w zrozumieniu pytania i dostarczeniu bardziej adekwatnej odpowiedzi."
            "Przeanalizuj kontekst, w odpowiedzi na pytanie nie odnoś się do kontektu, a jedynie do pytania."
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", context),
            ("human", "Pytanie: {question}")
        ])

        messages = prompt.format_messages(question=query, context=context)
        logger.debug(f"Generating final answer with messages: {messages}")
        response = model.invoke(messages)

        # Sprawdzenie typu odpowiedzi i ekstrakcja treści
        if isinstance(response, list):
            response_text = response[-1].content if response else "Przepraszam, wystąpił problem z generowaniem odpowiedzi."
        elif hasattr(response, 'content'):
            response_text = response.content
        else:
            response_text = str(response)

        formatted_response = response_text.strip()
        logger.debug(f"Finalized response: {formatted_response}")
        return formatted_response
    except Exception as e:
        logger.error(f"Error generating final answer: {e}")
        return "Przepraszam, wystąpił problem z generowaniem końcowej odpowiedzi."

# ------------------------------
# 8. Implement ChatAgent Class
# ------------------------------
class ChatAgent:
    MAX_HISTORY_LENGTH = 4  # Set maximum conversation history length

    def __init__(
            self,
            user_id: str,
            model: ChatAnthropic,
            tavily_api_key: str,
            anthropic_api_key: str,
            memory: Callable[[], Conversation],
            conversation_id: Optional[int] = None
    ):
        self.user_id = user_id
        self.model = model
        self.tavily_api_key = tavily_api_key
        self.anthropic_api_key = anthropic_api_key
        self.memory = memory
        self.conversation_id = conversation_id

        # Initialize tools
        self.flashcard_tool = FlashcardGenerator(
            model_name="claude-3-haiku-20240307",
            anthropic_api_key=anthropic_api_key
        )
        self.rag_tool = RAGTool(
            model_name="claude-3-haiku-20240307",
            user_id=self.user_id,
            anthropic_api_key=anthropic_api_key
        )
        self.tavily_tool = TavilySearchResults(
            name="TavilySearchResults",  # Ensure the name matches exactly in RouteQuery
            tavily_api_key=tavily_api_key,
            search_depth='advanced',  # Example value, adjust according to documentation
            max_results=5,
            include_answer=True,
            include_raw_content=True,
            include_images=True
        )

        self.direct_answer_tool = DirectAnswer(model=self.model)

        self.tools = [self.flashcard_tool, self.rag_tool, self.tavily_tool, self.direct_answer_tool]

        # Create chains
        self.classify = create_classification_chain(self.model, tools=self.tools)
        self.tool_chains = create_tool_chains(
            flashcard_tool=self.flashcard_tool,
            rag_tool=self.rag_tool,
            tavily_tool=self.tavily_tool,
            model=self.model
        )
        self.router = create_router_chain(self.tool_chains)

    def handle_query(self, query: str) -> str:
        logger.info(f"Handling query: '{query}'")

        # Retrieve the latest conversation checkpoint for the user
        try:
            conversation = get_latest_checkpoint(self.user_id, self.conversation_id)
            if not conversation:
                conversation = create_memory(user_id=self.user_id)
            conversation_id = conversation.id
            conversation_history = get_conversation_history(conversation_id, self.MAX_HISTORY_LENGTH)
            logger.debug(f"Found latest conversation: ID={conversation_id} for user {self.user_id}.")
            logger.debug(f"Retrieved conversation history for conversation ID={conversation_id}: {conversation_history}")
        except Exception as e:
            logger.error(f"Error retrieving latest conversation: {e}")
            return "Przepraszam, wystąpił problem z przetworzeniem Twojego zapytania."

        # Add conversation history to context
        if conversation_history:
            context = "\n".join(conversation_history)
        else:
            context = ""

        # Classification of the query
        try:
            classification = self.classify(query)
            logger.info(f"Classification result: {classification}")
        except ValueError as e:
            logger.error(f"Query classification failed: {e}")
            # Fallback to 'DirectAnswer' datasource
            classification = RouteQuery(datasources=["DirectAnswer"])

        # Routing to appropriate tools with passing both description and query
        try:
            aggregated_context = ""  # Initialize empty context for final_answer
            responses = []
            datasources = classification.datasources
            logger.info(f"Routing to datasources: {datasources}")

            for datasource in datasources:
                tool_function = self.tool_chains.get(datasource, self.tool_chains["DirectAnswer"])
                try:
                    if datasource == "TavilySearchResults":
                        current_query = query  # Original user query
                        response = tool_function(current_query)
                    elif datasource == "FlashcardGenerator":
                        # Pass both description and query as a JSON string
                        input_data = json.dumps({"description": context, "query": query}, ensure_ascii=False)
                        response = tool_function(input_data)
                    else:
                        # For other tools, augment the query with context if available
                        aggregated_context = context
                        current_query = f"Context:\n{aggregated_context}\nQuestion: {query}" if aggregated_context else query
                        response = tool_function(current_query)

                    responses.append(response)
                    # Update aggregated_context with the tool's response if it's not an error message
                    if not response.startswith("Przepraszam"):
                        aggregated_context += f"\n\nPrevious tool response:\n{response}"
                except Exception as e:
                    # Log the error and add a user-friendly message
                    logger.error(f"Error using tool {datasource}: {e}")
                    responses.append(f"Przepraszam, wystąpił problem z narzędziem {datasource}.")

            # Generate the final answer using the aggregated context
            final_response = final_answer(aggregated_context, query, self.model)
            logger.info(f"Finalized response: '{final_response}'")

        except Exception as e:
            logger.error(f"Query routing failed: {e}")
            return "Przepraszam, wystąpił problem podczas generowania odpowiedzi."

        return final_response

# ------------------------------
# 8. Implement ChatAgent Function
# ------------------------------

def agent_response(
        user_id: str,
        query: str,
        model_name: str = "claude-3-haiku-20240307",
        anthropic_api_key: str = None,
        tavily_api_key: str = None,
        conversation_id: int = None
) -> str:
    logger.info(f"Generating response for user_id: {user_id} with query: '{query}'")

    # Check API keys
    if not anthropic_api_key:
        anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        if not anthropic_api_key:
            raise ValueError("Anthropic API key is not set.")

    if not tavily_api_key:
        tavily_api_key = os.getenv('TAVILY_API_KEY')
        if not tavily_api_key:
            raise ValueError("Tavily API key is not set.")

    try:
        model = ChatAnthropic(
            anthropic_api_key=anthropic_api_key,
            model=model_name,
            temperature=0.0  # Set temperature to 0 for more deterministic responses
        )

        # Initialize the agent
        agent = ChatAgent(
            user_id=user_id,
            model=model,
            tavily_api_key=tavily_api_key,
            anthropic_api_key=anthropic_api_key,
            memory=create_memory,
            conversation_id=conversation_id
        )

        # Handle the query
        response = agent.handle_query(query)
        logger.info(f"Generated response: '{response}'")
        return response

    except Exception as e:
        logger.error(f"Error generating response: {e}", exc_info=True)
        return f"Wystąpił błąd podczas generowania odpowiedzi: {str(e)}"

# ------------------------------
# 9. Implement Test Function (Optional)
# ------------------------------

if __name__ == "__main__":
    # Example tools
    tools = [
        FlashcardGenerator(model_name="claude-3-haiku-20240307", anthropic_api_key=os.getenv('ANTHROPIC_API_KEY')),
        RAGTool(user_id="user-123", model_name="claude-3-haiku-20240307", anthropic_api_key=os.getenv('ANTHROPIC_API_KEY')),
        TavilySearchResults(
            name="TavilySearchResults",  # Ensure the name matches exactly in RouteQuery
            tavily_api_key=os.getenv('TAVILY_API_KEY'),
            search_depth='advanced',  # Example value, adjust according to documentation
            max_results=5,
            include_answer=True,
            include_raw_content=True,
            include_images=True
        ),
        DirectAnswer(model=ChatAnthropic(
            anthropic_api_key=os.getenv('ANTHROPIC_API_KEY'),
            model="claude-3-haiku-20240307",
            temperature=0.0
        ))
    ]

    # Initialize the model
    model = ChatAnthropic(
        anthropic_api_key=os.getenv('ANTHROPIC_API_KEY'),
        model="claude-3-haiku-20240307",
        temperature=0.0
    )

    # Create classification chain
    classify = create_classification_chain(model, tools)

    # Example question
    question = "Jaka jest dzisiaj pogoda w Warszawie?"

    # Classify the question
    route_query = classify(question)

    print(route_query)
