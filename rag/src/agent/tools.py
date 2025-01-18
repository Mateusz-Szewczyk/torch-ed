# tools.py

from typing import List, Tuple, Any, Dict
from langchain.tools import BaseTool
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
import logging
import os
from pydantic import Field, PrivateAttr
import json
import uuid
from ..models import Exam, ExamQuestion, ExamAnswer

# Import your search engine function
from ..search_engine import search_and_rerank

# Database imports
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models import Deck, Flashcard

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Dodaj handler tylko jeśli nie został dodany wcześniej
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Initialize the embedding model
from langchain_openai import OpenAIEmbeddings


try:
    embedding_model = OpenAIEmbeddings(model="text-embedding-3-large")
except Exception as e:
    raise

# Initialize Anthropic API key
anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
if not anthropic_api_key:
    raise ValueError("Anthropic API key is not set. Please set the ANTHROPIC_API_KEY environment variable.")


class FlashcardGenerator(BaseTool):
    name: str = "FlashcardGenerator"
    description: str = """This tool generates flashcards based on provided data.
                        The tool outputs flashcards in JSON format containing questions and answers.
                        If you want to use this tool please use it as the last tool in the pipeline.
                        This tool can only be used once; if it has been used before, please do not use it again.
                        Keywords that trigger this tool include requests containing: "fiszki", "wygeneruj", "stwórz", "utwórz".
                        """

    _model: Any = PrivateAttr()
    _output_parser: JsonOutputParser = PrivateAttr()
    user_id: str = Field(default=None)

    def __init__(self, user_id: str, model_type: str = "Anthropic", model_name: str = "claude-3-haiku-20240307", api_key: str = None):
        """
        Inicjalizacja FlashcardGenerator z wybranym modelem AI.

        Args:
            model_type (str): Typ modelu AI do użycia ('Anthropic' lub 'OpenAI').
            model_name (str): Nazwa modelu AI.
            api_key (str): Klucz API dla wybranego modelu.
        """
        super().__init__()
        self.user_id = user_id
        if model_type == "Anthropic":
            if not api_key:
                raise ValueError("Anthropic API key is not set.")
            self._model = ChatAnthropic(model_name=model_name, anthropic_api_key=api_key)
        elif model_type == "OpenAI":
            if not api_key:
                raise ValueError("OpenAI API key is not set.")
            self._model = ChatOpenAI(model_name=model_name, openai_api_key=api_key)
        else:
            raise ValueError("Unsupported model_type. Choose 'Anthropic' or 'OpenAI'.")

        self._output_parser = JsonOutputParser()

    def _run(self, input_str: str) -> str:
        """
        Generate flashcards based on the input string and save them to the database.

        Args:
            input_str: A JSON-formatted string containing 'description' and 'query'.

        Returns:
            A string confirming the operation in JSON format or an error message.
        """
        try:
            # Parsowanie wejścia JSON
            input_data = json.loads(input_str)
            description = input_data.get('description', 'Serial Arcane').strip()
            query = input_data.get('query', 'Stwórz fiszki o serialu Arcane').strip()

            # Konstruowanie prompta bezpośrednio w metodzie _run
            system_prompt = "Zwróć tylko w formacie JSON bez dodatkowego tekstu. Odpowiedź napisz w odpowiednim języku! Wygeneruj dokładną liczbę fiszek, jaką podał użytkownik."
            user_prompt = f"""
Wygeneruj fiszki na podstawie następującego kontekstu:
{description}

I wykonaj polecenie zadane przez użytkownika: {query}

Wygenerowane fiszki powinny być w języku użytkownika, czyli w tym języku, w którym jest napisany opis i tytuł.
Jeśli użytkownik nie podał liczby fiszek do stworzenia, proszę zdecyduj ile fiszek powinno zostać utworzonych.

Pomyśl o najlepszym sposobie sformatowania tych fiszek, jaka będzie najlepsza kombinacja pytań i odpowiedzi.
Proszę zastanów się również jaka powinna być nazwa zestawu fiszek oraz jego opis.
Create exact number of flashcards as specified by the user.
Zwróć fiszki w dokładnie takim formacie JSON:
{{
    "topic": "Your Deck Name",
    "description": "Description of the Deck",
    "flashcards": [
        {{"question": "Question 1", "answer": "Answer 1"}},
        {{"question": "Question 2", "answer": "Answer 2"}}
    ]
}}
"""

            # Formatowanie wiadomości
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            logger.debug(f"Formatted Messages:\n{messages}")

            # Inwokacja modelu z sformatowanymi wiadomościami
            response = self._model.invoke(messages)

            # Ekstrakcja tekstu odpowiedzi
            if isinstance(response, list):
                response_text = response[-1].content if response else ""
            elif hasattr(response, 'content'):
                response_text = response.content
            else:
                response_text = str(response)

            logger.debug(f"Model Response: {response_text}")

            # Parsowanie odpowiedzi JSON
            parsed_response = self._output_parser.parse(response_text)

            # Walidacja struktury fiszek
            flashcards = parsed_response.get('flashcards', [])
            topic = parsed_response.get('topic', f'deck_{uuid.uuid4().hex[:8]}')
            description = parsed_response.get('description', 'Brak opisu')

            # Konwersja odpowiedzi do stringa JSON
            flashcards_json = json.dumps({
                "topic": topic,
                "description": description,
                "flashcards": flashcards
            }, ensure_ascii=False)

            # Zapis fiszek do bazy danych
            db: Session = SessionLocal()
            try:
                # Tworzenie nowego zestawu
                new_deck = Deck(user_id=self.user_id, name=topic, description=description)
                db.add(new_deck)
                db.commit()
                db.refresh(new_deck)

                # Tworzenie fiszek związanych z zestawem
                for card in flashcards:
                    new_flashcard = Flashcard(
                        question=card.get('question', '').strip(),
                        answer=card.get('answer', '').strip(),
                        deck_id=new_deck.id
                    )
                    db.add(new_flashcard)

                db.commit()
                logger.info(f"Successfully created deck with ID {new_deck.id} and saved {len(flashcards)} flashcards.")

                # Formułowanie odpowiedzi do zwrócenia
                formatted_response = f"""Topic: "{topic}"
Description: "{description}"
Flashcards:
"""
                for idx, card in enumerate(flashcards, start=1):
                    formatted_response += f'{idx}. Q: "{card.get("question", "")}" A: "{card.get("answer", "")}"\n'

                return formatted_response

            except Exception as e:
                db.rollback()
                logger.error(f"Database error: {e}")
                return json.dumps({
                    "error": f"Błąd zapisu do bazy danych: {str(e)}"
                }, ensure_ascii=False)
            finally:
                db.close()

        except json.JSONDecodeError as jde:
            logger.error(f"JSON decode error: {jde}. Input string: {input_str}")
            return json.dumps({
                "error": "Nieprawidłowy format JSON w danych wejściowych."
            }, ensure_ascii=False)
        except ValueError as ve:
            logger.error(f"ValueError: {ve}. Input string: {input_str}")
            return json.dumps({
                "error": "Nieprawidłowa odpowiedź modelu."
            }, ensure_ascii=False)
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            return json.dumps({
                "error": "Przepraszam, wystąpił problem z generowaniem fiszek."
            }, ensure_ascii=False)

    async def _arun(self, input_str: str) -> str:
        """Asynchronous version of the run method."""
        return self._run(input_str)


class RAGTool(BaseTool):
    """
    Retrieval-Augmented Generation Tool for extracting key facts and information
    using both internal and external knowledge.
    """
    name: str = "RAGTool"
    description: str = (
        "Uses Retrieval-Augmented Generation to extract key facts from internal "
        "and external knowledge sources. Automatically adapts to the user's language."
    )
    user_id: str = Field(default=None)
    _model: Any = PrivateAttr()

    def __init__(
        self,
        user_id: str,
        model_type: str = "OpenAI",
        model_name: str = "gpt-4o-mini-2024-07-18",
        api_key: str = None
    ):
        super().__init__()
        self.user_id = user_id
        if model_type == "Anthropic":
            if not api_key:
                raise ValueError("Anthropic API key is required.")
            self._model = ChatAnthropic(model_name=model_name, anthropic_api_key=api_key)
        elif model_type == "OpenAI":
            if not api_key:
                raise ValueError("OpenAI API key is required.")
            self._model = ChatOpenAI(model_name=model_name, openai_api_key=api_key)
        else:
            raise ValueError("Supported models are 'Anthropic' or 'OpenAI'.")

    def _run(self, query: str) -> str:
        return self.generate_answer_rag(query)

    async def _arun(self, query: str) -> str:
        return self.generate_answer_rag(query)

    def generate_answer_rag(
        self,
        query: str,
    ) -> str:
        """
        Generates a factual and concise answer using external knowledge.
        """
        logger.info(f"Starting RAG for query: '{query}'")
        external_passages = []

        hyde_answer = self.generate_hyde_answer(query)

        # External Knowledge
        try:
            results = search_and_rerank(hyde_answer, user_id=self.user_id, n_results=5)
            external_passages = [doc.get('content', '') for doc in results]
            logger.info(f"Retrieved {len(external_passages)} external passages.")
        except Exception as e:
            logger.error(f"Error retrieving external passages: {e}", exc_info=True)

        # Finalization
        return self.finalize_answer(query, external_passages)

    def generate_hyde_answer(self, query: str) -> str:
        """
        Generates a factual and concise answer using the Hyde model.
        """
        system_prompt = (
            "You are an AI tasked with producing concise and factual one to two paragraph long answers. "
            "You will try to generate short but informative answers."
             )
        user_prompt = f"""
            Question: {query}

            Please generate a factual and concise answer using the provided query.
        """
        prompt_template = ChatPromptTemplate.from_messages([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        try:
            response = self._model.invoke(prompt_template.format(query=query))
            return response.content.strip()
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return "Nie udało się wygenerować odpowiedzi."

    def finalize_answer(self, query: str, passages: List[str]) -> str:
        """
        Produces the final factual answer from passages.
        """
        system_prompt = (
            "You are an AI tasked with producing concise and factual answers. Use the provided "
            "information. Highlight definitions, attributes, or key data relevant to the question."
        )
        user_prompt = f"""
            Question: {query}

            Passages:
            {''.join([f"Passage: {p}\n\n" for p in passages])}

            Final Answer:
        """
        prompt_template = ChatPromptTemplate.from_messages([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        try:
            response = self._model.invoke(prompt_template.format(query=query))
            return response.content.strip()
        except Exception as e:
            logger.error(f"Error finalizing answer: {e}")
            return "Nie udało się wygenerować końcowej odpowiedzi."


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExamGenerator(BaseTool):
    name: str = "ExamGenerator"
    description: str = """This tool generates exams based on provided data.
                        The tool outputs exams in JSON format containing topics, descriptions, questions, and answers.
                        If you want to use this tool please use it as the last tool in the pipeline.
                        This tool can only be used once; if it has been used before, please do not use it again.
                        Keywords that trigger this tool include requests containing: "egzamin", "wygeneruj", "stwórz", "utwórz", "test", "quiz".
                        """

    _model: ChatOpenAI = PrivateAttr()
    _output_parser: JsonOutputParser = PrivateAttr()
    user_id: str = Field(default=None)

    def __init__(self, user_id: str, model_name: str = "gpt-4o-mini-2024-07-18", openai_api_key: str = None):
        super().__init__()
        self.user_id = user_id
        if not openai_api_key:
            raise ValueError("OpenAI API key is not set.")
        self._model = ChatOpenAI(model_name=model_name, openai_api_key=openai_api_key)
        self._output_parser = JsonOutputParser()

    def validate_input(self, input_str: str) -> tuple[str, str]:
        """Validate input JSON and extract description and query."""
        try:
            input_data = json.loads(input_str)
            if not isinstance(input_data, dict):
                raise ValueError("Input must be a JSON object")

            description = input_data.get('description', '').strip()
            query = input_data.get('query', '').strip()

            if not description or not query:
                raise ValueError("Both description and query are required")

            return description, query
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON format")

    def _get_prompts(self, description: str, query: str) -> tuple[str, str]:
        """Generate system and user prompts for the exam generation."""
        system_prompt = """
        Return only in JSON format without additional text. Write the answer in the appropriate language! 
        RETURN EXACTLY AS MANY TASKS AS THE USER SPECIFIED.
        Do not include any explanations or additional text outside the JSON structure.
        """

        user_prompt = f"""
        Generate an exam based on the following context:
        {description}

        And execute the user's command: {query}
        Please make the exact number of questions as specified by the user.

        The generated exam should be in the user's language, which is the same language as the description and title.
        Please generate exactly the number of questions as specified in the user's command.

        Consider the best way to format the exam, the optimal combination of questions and answers.
        Please also think about what the name of the exam should be and its description.

        Requirements for the generated exam:
        1. Each question must have exactly 4 answer options
        2. Exactly one answer must be correct for each question
        3. All answers must be meaningful and relevant
        4. Questions should vary in difficulty
        5. Questions should cover different aspects of the topic
        6. Each question and answer should be clear and unambiguous

        Provide the exam in the exact following JSON format:

        {{
            "topic": "Example Topic",
            "description": "Detailed description of the exam's purpose and scope.",
            "num_of_questions": <number specified in query>,
            "questions": [
                {{
                    "question": "Clear, well-formed question text?",
                    "answers": [
                        {{"text": "First answer option", "is_correct": false}},
                        {{"text": "Second answer option", "is_correct": true}},
                        {{"text": "Third answer option", "is_correct": false}},
                        {{"text": "Fourth answer option", "is_correct": false}}
                    ]
                }},
                // Additional questions as needed
            ]
        }}

        Ensure that:
        - The topic accurately reflects the exam content
        - The description is informative and complete
        - Each question is unique and relevant
        - Answer options are distinct and plausible
        - The correct answer is clearly marked
        - The total number of questions matches exactly what was requested
        """

        return system_prompt.strip(), user_prompt.strip()

    def generate_exam(self, system_prompt: str, user_prompt: str) -> tuple[str, str, int, list[dict]]:
        """Generate exam using the language model."""
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]

        response = self._model.invoke(messages)
        response_text = response.content if hasattr(response, 'content') else str(response)

        try:
            parsed_response = self._output_parser.parse(response_text)
        except Exception as e:
            logger.error(f"Failed to parse model response: {e}")
            raise ValueError(f"Invalid model response format: {str(e)}")

        if not isinstance(parsed_response, dict):
            raise ValueError("Invalid model response format: not a dictionary")

        # Validate the response structure
        required_fields = ['topic', 'description', 'num_of_questions', 'questions']
        for field in required_fields:
            if field not in parsed_response:
                raise ValueError(f"Missing required field: {field}")

        # Validate questions structure
        questions = parsed_response.get('questions', [])
        for i, question in enumerate(questions):
            if 'question' not in question:
                raise ValueError(f"Question {i + 1} is missing question text")
            if 'answers' not in question:
                raise ValueError(f"Question {i + 1} is missing answers")
            if len(question['answers']) != 4:
                raise ValueError(f"Question {i + 1} must have exactly 4 answers")
            correct_answers = sum(1 for ans in question['answers'] if ans.get('is_correct'))
            if correct_answers != 1:
                raise ValueError(f"Question {i + 1} must have exactly 1 correct answer")

        return (
            parsed_response.get('topic'),
            parsed_response.get('description'),
            parsed_response.get('num_of_questions'),
            parsed_response.get('questions')
        )

    def save_to_database(self, topic: str, description: str, questions: list[dict]) -> int:
        """Save exam data to database."""
        db = SessionLocal()
        try:
            new_exam = Exam(
                user_id=self.user_id,
                name=topic,
                description=description
            )
            db.add(new_exam)
            db.commit()
            db.refresh(new_exam)

            for question in questions:
                new_question = ExamQuestion(
                    text=question.get('question', '').strip(),
                    exam_id=new_exam.id
                )
                db.add(new_question)
                db.commit()
                db.refresh(new_question)

                for answer in question.get('answers', []):
                    new_answer = ExamAnswer(
                        text=answer.get('text', '').strip(),
                        is_correct=answer.get('is_correct', False),
                        question_id=new_question.id
                    )
                    db.add(new_answer)
                db.commit()

            return new_exam.id
        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()

    def _run(self, input_str: str) -> str:
        """Generate exams based on the input string and save them to the database."""
        try:
            # Validate input and get description and query
            description, query = self.validate_input(input_str)

            # Get prompts for exam generation
            system_prompt, user_prompt = self._get_prompts(description, query)

            best_result = None
            max_attempts = 3

            # Try generating the exam up to max_attempts times
            for attempt in range(max_attempts):
                try:
                    logger.info(f"Attempting to generate exam (attempt {attempt + 1}/{max_attempts})")

                    topic, exam_description, requested_num_questions, questions = self.generate_exam(
                        system_prompt, user_prompt
                    )

                    # If we have at least 80% of requested questions, consider it good enough
                    if len(questions) >= (requested_num_questions * 0.8):
                        exam_id = self.save_to_database(topic, exam_description, questions)

                        return json.dumps({
                            "status": "success",
                            "exam_id": exam_id,
                            "topic": topic,
                            "description": exam_description,
                            "num_of_questions": len(questions),
                            "questions": questions
                        }, ensure_ascii=False)

                    # Store this result if it's the best so far
                    if not best_result or len(questions) > len(best_result[3]):
                        best_result = (topic, exam_description, requested_num_questions, questions)

                except Exception as e:
                    logger.error(f"Attempt {attempt + 1} failed: {str(e)}")
                    if attempt == max_attempts - 1:
                        raise

            # If we got here, use the best result we had
            if best_result:
                topic, exam_description, requested_num_questions, questions = best_result
                exam_id = self.save_to_database(topic, exam_description, questions)

                return json.dumps({
                    "status": "partial_success",
                    "exam_id": exam_id,
                    "topic": topic,
                    "description": exam_description,
                    "num_of_questions": len(questions),
                    "questions": questions,
                    "warning": f"Could only generate {len(questions)} out of {requested_num_questions} requested questions"
                }, ensure_ascii=False)

            raise ValueError("Failed to generate any valid exam")

        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            return json.dumps({
                "status": "error",
                "error": str(e)
            }, ensure_ascii=False)

    async def _arun(self, input_str: str) -> str:
        """Asynchronous version of the run method."""
        return self._run(input_str)