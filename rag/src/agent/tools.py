# tools.py
from typing import List, Tuple, Dict, Any
from langchain.tools import BaseTool
from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage
from langchain_core.prompts import HumanMessagePromptTemplate
import logging
import os
from pydantic import Field
import json

# Import your search engine function
from ..search_engine import search_and_rerank

# Database imports
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models import Deck, Flashcard

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize the embedding model
from sentence_transformers import SentenceTransformer

EMBEDDING_MODEL_NAME = os.getenv('EMBEDDING_MODEL_NAME', 'all-MiniLM-L6-v2')
try:
    embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    logger.info(f"Initialized embedding model: {EMBEDDING_MODEL_NAME}")
except Exception as e:
    logger.error(f"Failed to initialize embedding model '{EMBEDDING_MODEL_NAME}': {e}")
    raise

# Initialize Anthropic API key
anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
if not anthropic_api_key:
    raise ValueError("Anthropic API key is not set. Please set the ANTHROPIC_API_KEY environment variable.")



class FlashcardGenerator(BaseTool):
    name: str = "flashcard_generator"
    description: str = """To narzędzie generuje fiszki na podstawie dostarczonych danych.
    Jeżeli użytkownik podał konkretną ilość fiszek w zapytaniu, poproś o konkretną ilość fiszek.
    Narzędzie generuje fiszki w formacie JSON, które zawierają pytanie i odpowiedź.
    Narzędzie adaptuje się do języka użytkownika i dostarcza jak najlepszą odpowiedź.
    Z tego narzędzia można skorzystać tylko raz, jeżeli to narzędzie było wcześniej użyte, proszę nie korzystaj z niego.
    Przykładowe Wejścia:
    -Proszę wygeneruj 18 fiszek do nauki pierwiastków układu okresowego
    -Proszę wygeneruj fiszki do nauki najczęściej używanych stwierdzeń w języku hiszpańskim
    """

    model: ChatAnthropic = Field(default=None)
    flashcard_prompt: ChatPromptTemplate = Field(default=None)
    output_parser: JsonOutputParser = Field(default=None)

    def __init__(self, model_name: str = "claude-3-haiku-20240307", anthropic_api_key: str = None):
        super().__init__()
        if not anthropic_api_key:
            raise ValueError("Anthropic API key is not set.")
        self.model = ChatAnthropic(model_name=model_name, anthropic_api_key=anthropic_api_key)

        # Define the prompt template for flashcard generation
        self.flashcard_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="Zwróć tylko w formacie JSON bez dodatkowego tekstu. Odpowiedź napisz w odpowiednim języku!"),
            HumanMessagePromptTemplate.from_template("""
            Wygeneruj fiszki na temat {topic} na podstawie następującego opisu:
            {description}

            Wygenerowane fiszki powinny być w języku użytkownika, czyli w tym języku, w którym jest napisany opis i tytuł.
            Jeśli użytkownik nie podał liczby fiszek do stworzenia, proszę zdecyduj, ile fiszek powinno zostać utworzonych.
            Jeśli opis dotyczy tłumaczenia i język znajduje się na tej liście:
            {{
                "japanese": "romaji",
                "chinese": "pinyin",
                "korean": "romanization",
                "russian": "transliteration",
                "arabic": "transliteration",
                "thai": "transliteration",
                "hindi": "transliteration"
            }},
            uwzględnij podaną romanizację/transliterację w pytaniu.

            Pomyśl o najlepszym sposobie sformatowania tych fiszek, jaka będzie najlepsza kombinacja pytań i odpowiedzi.

            Zwróć fiszki w dokładnie takim formacie JSON:
            [
                {{
                    "question": "string", 
                    "answer": "string"    
                }}
            ]
            """)

        ])
        self.output_parser = JsonOutputParser()

    def _run(self, input_str: str) -> str:
        """
        Generate flashcards based on the input string and save them to the database.

        Args:
            input_str: A string containing the topic and/or description.

        Returns:
            A string confirming the operation.
        """

        # Extract topic and description from input_str
        # Możesz dodać logikę parsowania, jeśli potrzebujesz
        topic = ""  # Możesz zmodyfikować to, aby wyodrębnić temat z input_str, jeśli jest dostępny
        description = input_str

        # Generate flashcards
        prompt_with_context = self.flashcard_prompt | self.model | self.output_parser

        try:
            response = prompt_with_context.invoke({
                "description": description,
                "topic": topic
            })
            flashcards = response  # Zakładam, że odpowiedź to lista słowników z 'question' i 'answer'

            # Konwersja odpowiedzi do stringa JSON do zwrócenia
            flashcards_json = json.dumps(flashcards, ensure_ascii=False)

            # Zapis fiszek do bazy danych
            db: Session = SessionLocal()
            try:
                # Utworzenie nowego zestawu
                new_deck = Deck(name=topic, description=description)
                db.add(new_deck)
                db.commit()
                db.refresh(new_deck)

                # Utworzenie fiszek z unikalnymi ID powiązanymi z zestawem
                for card in flashcards:
                    new_flashcard = Flashcard(
                        question=card.get('question', ''),
                        answer=card.get('answer', ''),
                        deck_id=new_deck.id
                    )
                    db.add(new_flashcard)

                db.commit()

                logger.info(f"Successfully created deck with ID {new_deck.id} and saved {len(flashcards)} flashcards.")
                return flashcards_json

            except Exception as e:
                db.rollback()
                logger.error(f"An error occurred while saving flashcards to the database: {e}")
                raise e
            finally:
                db.close()

        except Exception as e:
            logger.error(f"An error occurred during flashcard generation: {e}")
            raise e

    async def _arun(self, input_str: str) -> str:
        """Asynchronous version of the run method."""
        # Dla uproszczenia używamy synchronicznej metody _run w kontekście asynchronicznym
        # W rzeczywistości rozważ użycie asynchronicznych sesji bazy danych
        return self._run(input_str)


class RAGTool(BaseTool):
    name: str = "rag_tool"
    description: str = (
        "Uses the Retrieval-Augmented Generation pipeline to answer queries using internal and external knowledge.",
        "The tool will recognize the user's language and will adapt to it"
    )
    user_id: str = Field(default=None)
    model: ChatAnthropic = Field(default=None)

    def __init__(self, user_id: str, model_name: str = "claude-3-haiku-20240307", anthropic_api_key: str = None):
        super().__init__()
        self.user_id = user_id
        if not anthropic_api_key:
            raise ValueError("Anthropic API key is not set.")
        self.model = ChatAnthropic(model_name=model_name, anthropic_api_key=anthropic_api_key)

    def _run(self, query: str) -> str:
        return self.generate_answer_rag(query)

    async def _arun(self, query: str) -> str:
        return self.generate_answer_rag(query)

    def generate_answer_rag(self, query: str, max_iterations: int = 2, max_generated_passages: int = 5) -> str:
        """
        Generates an answer using the RAG pipeline for the given query.

        Args:
            query (str): The user's query.
            max_iterations (int): Number of iterations for knowledge consolidation.
            max_generated_passages (int): Maximum number of passages to generate from internal knowledge.

        Returns:
            str: Generated answer.
        """
        logger.info(f"Generating RAG answer for query: '{query}'")

        # Step 1: Adaptive Generation of Internal Knowledge
        try:
            internal_passages = self.generate_internal_passages(query, max_generated_passages)
            logger.info(f"Generated {len(internal_passages)} internal passages.")
        except Exception as e:
            logger.error(f"Error generating internal passages: {e}", exc_info=True)
            internal_passages = []

        # Step 2: Retrieve relevant external chunks
        try:
            results = search_and_rerank(query, embedding_model, user_id=self.user_id, n_results=5)
            external_passages = [result.get('content', '') for result in results]
            logger.info(f"Retrieved {len(external_passages)} external passages.")
        except Exception as e:
            logger.error(f"Error during search and rerank: {e}", exc_info=True)
            external_passages = []

        if not internal_passages and not external_passages:
            logger.warning(f"No relevant information found for query: '{query}'")
            return "No relevant information found."

        # Step 2 & 3: Combine Internal and External Passages and Assign Sources
        combined_passages = external_passages + internal_passages
        source_indicators = ['external'] * len(external_passages) + ['internal'] * len(internal_passages)

        # Step 4: Iterative Source-aware Knowledge Consolidation
        consolidated_passages, consolidated_sources = self.iterative_consolidation(
            query,
            combined_passages,
            source_indicators,
            max_iterations
        )

        # Step 5: Answer Finalization
        answer = self.finalize_answer(query, consolidated_passages, consolidated_sources)

        logger.info(f"Generated RAG answer.")
        return answer

    def generate_internal_passages(self, query: str, max_generated_passages: int) -> List[str]:
        """
        Generates internal passages from the LLM's internal knowledge based on the query.

        Args:
            query (str): The user's query.
            max_generated_passages (int): Maximum number of passages to generate.

        Returns:
            List[str]: A list of generated internal passages.
        """
        # Prompt template for generating internal passages
        prompt_template = ChatPromptTemplate.from_messages([
            SystemMessage(
                content="You are a knowledgeable assistant helping to generate relevant information for a query. You will recognize query and passages language and adapt to it."),
            HumanMessagePromptTemplate.from_template("""
Based on your internal knowledge, generate up to {max_passages} accurate, relevant, and concise passages that answer the following question. Do not include any hallucinations or fabricated information. If you don't have enough reliable information, generate fewer passages or none.

Question:
{query}

Passages:
""")
        ])

        response = prompt_template | self.model

        try:
            output = response.invoke({
                "query": query,
                "max_passages": max_generated_passages
            })

            # Access the content of the AIMessage
            output_text = output.content

            # Split the output into individual passages
            passages = [p.strip() for p in output_text.strip().split('\n\n') if p.strip()]
            return passages

        except Exception as e:
            logger.error(f"Error generating internal passages: {e}", exc_info=True)
            return []

    def iterative_consolidation(self, query: str, passages: List[str], sources: List[str], max_iterations: int) -> \
    Tuple[List[str], List[str]]:
        """
        Iteratively consolidates the knowledge from passages considering their sources.

        Args:
            query (str): The user's query.
            passages (List[str]): List of passages.
            sources (List[str]): Corresponding list of sources ('internal' or 'external').
            max_iterations (int): Number of consolidation iterations.

        Returns:
            Tuple[List[str], List[str]]: Consolidated passages and their sources.
        """
        for iteration in range(max_iterations):
            logger.info(f"Consolidation iteration {iteration + 1}")
            prompt_template = ChatPromptTemplate.from_messages([
                SystemMessage(content="You are an assistant that consolidates information from different sources. You will recognize query and passages language and adapt to it."),
                HumanMessagePromptTemplate.from_template("""
Given the following passages and their sources, consolidate the information by identifying consistent details, resolving conflicts, and removing irrelevant content.

Question:
{query}

Passages and Sources:
{passages_and_sources}

Consolidated Passages:
""")
            ])

            # Prepare passages and sources for the prompt
            passages_and_sources = ""
            for passage, source in zip(passages, sources):
                passages_and_sources += f"Source: {source}\nPassage: {passage}\n\n"

            response = prompt_template | self.model

            try:
                output = response.invoke({
                    "query": query,
                    "passages_and_sources": passages_and_sources
                })

                # Access the content of the AIMessage
                output_text = output.content

                # Parse the consolidated passages and sources from the output
                # Assuming the output is formatted as:
                # "Passage: ... \nSource: ... \n\n"
                new_passages = []
                new_sources = []
                entries = output_text.strip().split('\n\n')
                for entry in entries:
                    lines = entry.strip().split('\n')
                    passage_text = ''
                    source_text = ''
                    for line in lines:
                        if line.startswith("Passage:"):
                            passage_text = line[len("Passage:"):].strip()
                        elif line.startswith("Source:"):
                            source_text = line[len("Source:"):].strip()
                    if passage_text and source_text:
                        new_passages.append(passage_text)
                        new_sources.append(source_text)
                passages = new_passages
                sources = new_sources

            except Exception as e:
                logger.error(f"Error during consolidation iteration {iteration + 1}: {e}", exc_info=True)
                break  # Exit the loop if consolidation fails

        return passages, sources

    def finalize_answer(self, query: str, passages: List[str], sources: List[str]) -> str:
        """
        Generates the final answer based on the consolidated passages and their sources.

        Args:
            query (str): The user's query.
            passages (List[str]): Consolidated passages.
            sources (List[str]): Corresponding sources.

        Returns:
            str: The final answer.
        """
        prompt_template = ChatPromptTemplate.from_messages([
            SystemMessage(
                content="You are an AI assistant tasked with generating the most reliable answer based on consolidated information. You will recognize query and passages language and adapt to it."),
            HumanMessagePromptTemplate.from_template("""
Based on the following consolidated passages and their sources, generate the most accurate and reliable answer to the question. Consider the reliability of each source, cross-confirmation between sources, and the thoroughness of the information.

Question:
{query}

Consolidated Passages and Sources:
{passages_and_sources}

Final Answer:
""")
        ])

        # Prepare passages and sources for the prompt
        passages_and_sources = ""
        for passage, source in zip(passages, sources):
            passages_and_sources += f"Source: {source}\nPassage: {passage}\n\n"

        response = prompt_template | self.model

        try:
            answer = response.invoke({
                "query": query,
                "passages_and_sources": passages_and_sources
            })
            return answer.content.strip()

        except Exception as e:
            logger.error(f"Error during answer finalization: {e}", exc_info=True)
            return "An error occurred while generating the final answer."
