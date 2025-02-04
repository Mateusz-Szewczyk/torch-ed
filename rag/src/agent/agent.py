# agent.py

import os
import logging
from typing import Callable, Dict, List, Optional
import json
import uuid

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import JsonOutputParser
from langchain.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, validator
from typing import Literal
from langchain_community.tools.tavily_search.tool import TavilySearchResults
from dotenv import load_dotenv
from pathlib import Path

from .utils import set_conversation_title_if_needed
from ..models import Conversation
from .tools import FlashcardGenerator, RAGTool
from .agent_memory import (
    create_memory,
    get_latest_checkpoint,
    get_conversation_history,
)
from langchain.tools import BaseTool

# Importowanie klas ExamGenerator i modeli związanych z egzaminami
from .tools import ExamGenerator

logger = logging.getLogger(__name__)

env_path = Path(__file__).resolve().parents[2] / '.env'
load_dotenv(dotenv_path=env_path)


class RouteQuery(BaseModel):
    """Route a user query to the most relevant datasources."""

    datasources: List[Literal["FlashcardGenerator", "RAGTool", "TavilySearchResults", "DirectAnswer", "ExamGenerator"]] = Field(
        ...,
        description="Given a user question, choose which datasources would be most relevant."
    )

    @validator('datasources', pre=True)
    def ensure_list(cls, v):
        if isinstance(v, str):
            return [v]
        return v


class DirectAnswer(BaseTool):
    name: str = "DirectAnswer"
    description: str = (
        "This tool provides direct, concise answers to user questions based solely on the provided conversation context. "
        "Use this tool for questions that are simple, personal, or directly addressable without external data."
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
                "You are a helpful assistant that provides direct, concise answers to user questions using only the given context. "
                "Do not mention the context explicitly in the answer; just use it silently to improve your response. "
                "If you do not have enough information, answer as best you can with what is provided."
            )

            full_query = f"Context:\n{aggregated_context}\n\nQuestion: {query}" if aggregated_context else query

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
        raise NotImplementedError("DirectAnswer does not support async operations.")


def create_classification_chain(model: ChatAnthropic, tools: List[BaseTool]) -> Callable[[str], RouteQuery]:
    tools_descriptions = "\n\n".join([
        f"{idx + 1}. {tool.name}\n   Description: {tool.description}"
        for idx, tool in enumerate(tools)
    ])

    system_prompt = f"""You are an expert router selecting tools based on the user's question. Consider conversation context, requested tasks, and available tools.

                Tools: {tools_descriptions}

                Rules:

                If user requests simple context-based info: use "DirectAnswer".
                If user wants flashcards, always pair "FlashcardGenerator" with a retrieval tool first (e.g., "RAGTool") if external knowledge is needed.
                If user references previously stored knowledge: use "RAGTool".
                If user wants new, broad, or current info: use "TavilySearchResults".
                If user wants to create an exam or sample test: use "ExamGenerator".
                If unsure: use "DirectAnswer".
                Return only a JSON object with "datasources": [ ... ].
                No explanations outside JSON.
                Examples:

                "Create flashcards about OOP from provided knowledge": {{{{"datasources": ["RAGTool", "FlashcardGenerator"]}}}}

                "What's my name?": {{{{"datasources": ["DirectAnswer"]}}}}

                "Explain abstraction mentioned before": {{{{"datasources": ["RAGTool"]}}}}

                "Create flashcards about Python decorators": {{{{"datasources": ["RAGTool", "FlashcardGenerator"]}}}}

                "Explain Python generators": {{{{"datasources": ["DirectAnswer"]}}}}

                "Top trending JS framework now?": {{{{"datasources": ["TavilySearchResults"]}}}}

                "Create flashcards on latest web frameworks (need new info)": {{{{"datasources": ["TavilySearchResults", "FlashcardGenerator"]}}}}

                "Create an exam on calculus for high school students": {{{{"datasources": ["ExamGenerator"]}}}}

                "Generate a sample test on physics": {{{{"datasources": ["ExamGenerator"]}}}}
                """

    human_prompt = "{question}"

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", human_prompt),
    ])

    parser = JsonOutputParser()

    chain = (
            prompt
            | model
            | parser
    )

    def classify(question: str) -> RouteQuery:
        try:
            logger.debug("Invoking classification chain with question.")
            response = chain.invoke({"question": question})
            logger.debug(f"Raw classification response: {response}")

            if not isinstance(response, dict):
                logger.error(f"Expected response to be a dict, got: {type(response)}")
                raise ValueError("Invalid response format.")

            if 'datasources' not in response:
                logger.error(f"'datasources' key missing in response: {response}")
                raise ValueError("Missing 'datasources' in response.")

            datasources = response['datasources']
            logger.debug(f"Extracted datasources: {datasources}")

            allowed_datasources = {"FlashcardGenerator", "RAGTool", "TavilySearchResults", "DirectAnswer", "ExamGenerator"}
            invalid_datasources = set(datasources) - allowed_datasources
            if invalid_datasources:
                logger.error(f"Invalid datasource(s): {invalid_datasources}")
                raise ValueError(f"Invalid datasource(s): {', '.join(invalid_datasources)}")

            return RouteQuery(datasources=datasources)
        except ValueError as ve:
            logger.error(f"ValueError during classification: {ve}")
            return RouteQuery(datasources=["DirectAnswer"])
        except Exception as e:
            logger.error(f"Error parsing classification response: {e}")
            return RouteQuery(datasources=["DirectAnswer"])

    return classify


def create_tool_chains(flashcard_tool: FlashcardGenerator, rag_tool: RAGTool, tavily_tool: TavilySearchResults,
                       exam_tool: ExamGenerator, model: ChatAnthropic) -> Dict[str, Callable[[str], str]]:
    flashcard_chain = lambda input_text: flashcard_tool.run(input_text)
    rag_chain = lambda input_text: rag_tool.run(input_text)
    exam_chain = lambda input_text: exam_tool.run(input_text)

    direct_answer_tool = DirectAnswer(model=model)
    direct_answer_chain = lambda input_text: direct_answer_tool.run(input_text)

    def tavily_chain(input_text: str) -> str:
        logger.debug(f"Invoking TavilySearchResults with query: {input_text}")
        try:
            results = tavily_tool.invoke({"query": input_text})
            logger.debug(f"TavilySearchResults response: {results}")

            if isinstance(results, list):
                contents = [result.get('content', '') for result in results if 'content' in result]
                return "\n".join(contents) if contents else "Przepraszam, nie mogę znaleźć odpowiedzi."
            elif isinstance(results, dict) and 'answer' in results:
                return results['answer']
            else:
                logger.error(f"Unexpected format from TavilySearchResults: {results}")
                return "Przepraszam, nie mogę znaleźć odpowiedzi."
        except Exception as e:
            logger.error(f"Error invoking TavilySearchResults: {e}")
            return "Przepraszam, wystąpił problem z wyszukiwaniem."

    tool_chains = {
        "FlashcardGenerator": flashcard_chain,
        "RAGTool": rag_chain,
        "TavilySearchResults": tavily_chain,
        "ExamGenerator": exam_chain,
        "DirectAnswer": direct_answer_chain
    }

    return tool_chains


def create_router_chain(tool_chains: Dict[str, Callable[[str], str]]) -> Callable[[RouteQuery, str, str], str]:
    def routing_function(classification: RouteQuery, query: str, description: str) -> str:
        datasources = classification.datasources
        logger.info(f"Routing to datasources: {datasources}")

        context = ""
        responses = []

        for datasource in datasources:
            tool_function = tool_chains.get(datasource, tool_chains["DirectAnswer"])
            try:
                if datasource == "TavilySearchResults":
                    current_query = query
                    response = tool_function(current_query)
                elif datasource == "FlashcardGenerator":
                    input_data = json.dumps({"description": description, "query": query}, ensure_ascii=False)
                    response = tool_function(input_data)
                elif datasource == "ExamGenerator":
                    input_data = json.dumps({"description": description, "query": query}, ensure_ascii=False)
                    response = tool_function(input_data)
                else:
                    current_query = f"{context}\nQuestion: {query}" if context else query
                    response = tool_function(current_query)

                responses.append(response)
                if not response.startswith("Przepraszam"):
                    context += f"\n{response}"
            except Exception as e:
                logger.error(f"Error using tool {datasource}: {e}")
                responses.append(f"Przepraszam, wystąpił problem z narzędziem {datasource}.")

        combined_response = "\n".join(responses) if responses else "Przepraszam, nie mogę odpowiedzieć."
        return combined_response

    return routing_function


def final_answer(context: str, query: str) -> str:
    try:
        final_model = ChatOpenAI(
            model_name="gpt-4o-mini-2024-07-18",
            temperature=0.0
        )

        system_prompt = (
            "Jesteś pomocnym asystentem, który potrafi syntetyzować informacje z różnych źródeł i przedstawić je w przejrzystej, zrozumiałej formie. "
            "Na podstawie kontekstu i pytania użytkownika, stwórz spójną, dobrze napisaną odpowiedź w formacie **Markdown**, "
            "ładnie sformatowaną, zrozumiałą i estetyczną. Nie odnoś się explicite do kontekstu, ale wykorzystaj go do udzielenia pełnej odpowiedzi. "
            "Jeśli to możliwe, możesz użyć list, nagłówków lub wyróżnień, aby odpowiedź była czytelna."
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


def produce_conversation_name(query: str, model: ChatAnthropic) -> str:
    """
    Produce a concise conversation name based on the user's first query.
    The name should be a short phrase describing the topic.
    """
    system_prompt = (
        "You are an assistant that creates short, descriptive conversation titles based on the user's first query. "
        "Do not mention that you are generating a title. Just provide a concise title (up to 5 words) that summarizes what the user might want to talk about."
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{question}")
    ])

    messages = prompt.format_messages(question=query)
    logger.debug(f"Generating conversation title with messages: {messages}")
    try:
        response = model.invoke(messages).content
        title = response.strip()
        logger.info(f"Generated conversation title: {title}")
        return title
    except Exception as e:
        logger.error(f"Error generating conversation title: {e}", exc_info=True)
        return "New Conversation"


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
        self.memory = memory
        self.conversation_id = conversation_id

        self.flashcard_tool = FlashcardGenerator(
            model_type="OpenAI",
            model_name="gpt-4o-mini-2024-07-18",
            api_key=openai_api_key,
            user_id=self.user_id
        )
        self.rag_tool = RAGTool(
            model_name="gpt-4o-mini-2024-07-18",
            user_id=self.user_id,
            model_type="OpenAI",
            api_key=openai_api_key
        )
        self.tavily_tool = TavilySearchResults(
            name="TavilySearchResults",
            tavily_api_key=tavily_api_key,
            search_depth='advanced',
            max_results=5,
            include_answer=True,
            include_raw_content=True,
            include_images=True
        )
        self.exam_tool = ExamGenerator(
            model_name="gpt-4o-mini-2024-07-18",
            openai_api_key=openai_api_key,
            user_id=self.user_id
        )
        self.direct_answer_tool = DirectAnswer(model=self.model)

        self.tools = [self.flashcard_tool, self.rag_tool, self.tavily_tool, self.exam_tool, self.direct_answer_tool]

        self.classify = create_classification_chain(self.model, tools=self.tools)
        self.tool_chains = create_tool_chains(
            flashcard_tool=self.flashcard_tool,
            rag_tool=self.rag_tool,
            tavily_tool=self.tavily_tool,
            exam_tool=self.exam_tool,
            model=self.model
        )
        self.router = create_router_chain(self.tool_chains)

    def handle_query(self, query: str) -> str:
        logger.info(f"Handling query: '{query}'")

        try:
            conversation = get_latest_checkpoint(self.user_id, self.conversation_id)
            if not conversation:
                conversation = create_memory(user_id=self.user_id)
            conversation_id = conversation.id
            conversation_history = get_conversation_history(conversation_id, self.MAX_HISTORY_LENGTH)
            logger.debug(f"Found latest conversation: ID={conversation_id} for user {self.user_id}.")
            logger.debug(f"Conversation history: {conversation_history}")
        except Exception as e:
            logger.error(f"Error retrieving latest conversation: {e}")
            return "Przepraszam, wystąpił problem z przetworzeniem Twojego zapytania."

        # If conversation just started
        if len(conversation_history) <= 2:
            set_conversation_title_if_needed(conversation, query, self.model)

        context = "\n".join(conversation_history) if conversation_history else ""

        try:
            classification = self.classify(query)
            logger.info(f"Classification result: {classification}")
        except ValueError as e:
            logger.error(f"Query classification failed: {e}")
            classification = RouteQuery(datasources=["DirectAnswer"])

        try:
            aggregated_context = ""
            responses = []
            datasources = classification.datasources
            logger.info(f"Routing to datasources: {datasources}")

            for datasource in datasources:
                tool_function = self.tool_chains.get(datasource, self.tool_chains["DirectAnswer"])
                try:
                    if datasource == "TavilySearchResults":
                        current_query = query
                        response = tool_function(current_query)
                    elif datasource == "FlashcardGenerator":
                        input_data = json.dumps({"description": context, "query": query}, ensure_ascii=False)
                        response = tool_function(input_data)
                    elif datasource == "ExamGenerator":
                        input_data = json.dumps({"description": context, "query": query}, ensure_ascii=False)
                        response = tool_function(input_data)
                    else:
                        aggregated_context = context
                        current_query = f"Context:\n{aggregated_context}\nQuestion: {query}" if aggregated_context else query
                        response = tool_function(current_query)

                    responses.append(response)
                    if not response.startswith("Przepraszam"):
                        aggregated_context += f"\n\nPrevious tool response:\n{response}"
                except Exception as e:
                    logger.error(f"Error using tool {datasource}: {e}")
                    responses.append(f"Przepraszam, wystąpił problem z narzędziem {datasource}.")
            logger.info(f"Aggregated context: {aggregated_context}")
                # Poprawione wywołanie final_answer z dwoma argumentami
            final_response = final_answer(aggregated_context, query)
            logger.info(f"Finalized response: '{final_response}'")

        except Exception as e:
            logger.error(f"Query routing failed: {e}")
            return "Przepraszam, wystąpił problem podczas generowania odpowiedzi."

        return final_response


def agent_response(
        user_id: str,
        query: str,
        model_name: str = "claude-3-haiku-20240307",
        anthropic_api_key: str = None,
        tavily_api_key: str = None,
        conversation_id: int = None,
        openai_api_key: str = None
) -> str:
    logger.info(f"Generating response for user_id: {user_id} with query: '{query}'")

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
        model = ChatAnthropic(
            anthropic_api_key=anthropic_api_key,
            model=model_name,
            temperature=0.1
        )

        agent = ChatAgent(
            user_id=user_id,
            model=model,
            tavily_api_key=tavily_api_key,
            anthropic_api_key=anthropic_api_key,
            memory=create_memory,
            conversation_id=conversation_id,
            openai_api_key=openai_api_key
        )

        response = agent.handle_query(query)
        logger.info(f"Generated response: '{response}'")
        return response

    except Exception as e:
        logger.error(f"Error generating response: {e}", exc_info=True)
        return f"Wystąpił błąd podczas generowania odpowiedzi: {str(e)}"
