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

    def __init__(self, model_type: str = "Anthropic", model_name: str = "claude-3-haiku-20240307", api_key: str = None):
        """
        Inicjalizacja FlashcardGenerator z wybranym modelem AI.

        Args:
            model_type (str): Typ modelu AI do użycia ('Anthropic' lub 'OpenAI').
            model_name (str): Nazwa modelu AI.
            api_key (str): Klucz API dla wybranego modelu.
        """
        super().__init__()
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
                new_deck = Deck(name=topic, description=description)
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
    name: str = "RAGTool"
    description: str = """Uses the Retrieval-Augmented Generation pipeline to extract key information from internal and external knowledge sources.
The tool will recognize the user's language and will adapt to it. Its purpose is to extract facts and information relevant to the user's query, often to help with exam preparation or creating flashcards. It should focus strictly on the given passages and avoid fabrication."""
    user_id: str = Field(default=None)
    _model: Any = PrivateAttr()

    def __init__(self,
                 user_id: str,
                 model_type: str = "OpenAI",
                 model_name: str = "gpt-4o-mini-2024-07-18",
                 api_key: str = None):
        """
        Initialize the RAGTool with a chosen model (Anthropic or OpenAI).

        Args:
            user_id (str): ID of the user.
            model_type (str): 'Anthropic' or 'OpenAI'.
            model_name (str): Name of the model to use.
            api_key (str): The API key for the chosen model.
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

    def _run(self, query: str) -> str:
        return self.generate_answer_rag(query)

    async def _arun(self, query: str) -> str:
        return self.generate_answer_rag(query)

    def generate_answer_rag(self, query: str, max_iterations: int = 2, max_generated_passages: int = 5) -> str:
        """
        Generates factual information relevant to the query using the RAG pipeline.

        Steps:
        1. Generate internal passages from the model's internal knowledge.
        2. Retrieve external passages from the vector store.
        3. Combine them and run iterative consolidation to extract only relevant facts.
        4. Finalize the answer focusing on correctness and relevancy.

        Args:
            query (str): The user's query.
            max_iterations (int): Number of consolidation iterations.
            max_generated_passages (int): Max number of passages to generate from internal knowledge.

        Returns:
            str: The final extracted factual information.
        """
        logger.info(f"Generating RAG answer for query: '{query}'")

        # Step 1: Generate internal passages
        try:
            internal_passages = self.generate_internal_passages(query, max_generated_passages)
            logger.info(f"Generated {len(internal_passages)} internal passages.")
        except Exception as e:
            logger.error(f"Error generating internal passages: {e}", exc_info=True)
            internal_passages = []

        # Step 2: Retrieve external passages
        try:
            results = search_and_rerank(query, embedding_model, user_id=self.user_id, n_results=5)
            external_passages = [result.get('content', '') for result in results]
            logger.info(f"Retrieved {len(external_passages)} external passages.")
        except Exception as e:
            logger.error(f"Error during search and rerank: {e}", exc_info=True)
            external_passages = []

        logger.info(f"External passages: {external_passages}")

        if not internal_passages and not external_passages:
            logger.warning(f"No relevant information found for query: '{query}'")
            return "Przepraszam, nie znalazłem informacji na ten temat."

        # Combine passages
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

        logger.info("Generated RAG answer.")
        return answer

    def retrieve(self, query: str, steps: int = 1) -> List[str]:
        """
        Retrieves relevant passages based on the query.
        """
        logger.info(f"Retrieving passages for query: '{query}' with steps: {steps}")

        # Step 1: Internal
        try:
            internal_passages = self.generate_internal_passages(query, max_generated_passages=steps)
            logger.info(f"Retrieved {len(internal_passages)} internal passages.")
        except Exception as e:
            logger.error(f"Error generating internal passages during retrieval: {e}")
            internal_passages = []

        # Step 2: External
        try:
            results = search_and_rerank(query, embedding_model, user_id=self.user_id, n_results=5)
            external_passages = [result.get('content', '') for result in results]
            logger.info(f"Retrieved {len(external_passages)} external passages.\n {external_passages}")
            logger.info(10*"jakis tekst")
        except Exception as e:
            logger.error(f"Error during search and rerank during retrieval: {e}")
            external_passages = []

        combined_passages = external_passages + internal_passages

        if not combined_passages:
            logger.warning(f"No passages retrieved for query: '{query}'")
            return []

        logger.info(f"Combined passages: {combined_passages}")
        return combined_passages

    def generate_internal_passages(self, query: str, max_generated_passages: int) -> List[str]:
        """
        Generates internal passages from the LLM's internal knowledge based on the query.
        They should be factual, concise, and relevant.
        If no reliable information is available, returns fewer or no passages.
        """
        prompt_template = ChatPromptTemplate.from_messages([
            SystemMessage(content=(
                "You are a knowledgeable assistant focused on extracting relevant factual information. "
                "Adapt to the query language."
            )),
            HumanMessage(content=f"""
You have internal knowledge. Generate up to {max_generated_passages} concise, accurate, and factual passages related to the question below.
These passages should be directly useful for answering the question, often used for exam preparation or creating flashcards.
If you lack reliable info, return fewer or no passages.
Do not fabricate information.

Question:
{query}

Passages:
""")
        ])

        try:
            response = self._model.invoke(prompt_template.format(query=query))
            logger.info(f"Odpowiedź rag tool: \n{response}")
            if isinstance(response, list):
                response_text = response[-1].content if response else ""
            elif hasattr(response, 'content'):
                response_text = response.content
            else:
                response_text = str(response)

            passages = [p.strip() for p in response_text.strip().split('\n\n') if p.strip()]
            return passages
        except Exception as e:
            logger.error(f"Error generating internal passages: {e}", exc_info=True)
            return []

    def iterative_consolidation(self, query: str, passages: List[str], sources: List[str], max_iterations: int) -> Tuple[List[str], List[str]]:
        """
        Iteratively consolidates the information from passages.
        The goal: Identify and extract only relevant factual details that help answer the given question.
        Avoid adding or inventing info. Keep key details.
        """
        for iteration in range(max_iterations):
            logger.info(f"Consolidation iteration {iteration + 1}")
            prompt_template = ChatPromptTemplate.from_messages([
                SystemMessage(content=(
                    "You are an assistant that consolidates facts from different sources. "
                    "Focus solely on providing information directly related to answering the given question. "
                    "No hallucinations. If any passages contain critical details (like definitions, properties, data) that answer the question, retain them. "
                    "If some passages are irrelevant or repetitive, remove them. Ensure the final set of passages is as informative and factual as possible, "
                    "helpful for creating exam questions or flashcards."
                )),
                HumanMessage(content=f"""
Question:
{query}

Below are passages with their sources. Consolidate them by:
- Keeping only the information that helps answer the question.
- Removing irrelevant, repetitive, or conflicting parts.
- Ensuring not to lose key facts.

Passages and Sources:
{''.join([f"Source: {source}\nPassage: {passage}\n\n" for passage, source in zip(passages, sources)])}

Consolidated Passages:
""")
            ])

            try:
                response = self._model.invoke(prompt_template.format(query=query))
                if isinstance(response, list):
                    response_text = response[-1].content if response else ""
                elif hasattr(response, 'content'):
                    response_text = response.content
                else:
                    response_text = str(response)

                new_passages = []
                new_sources = []
                entries = response_text.strip().split('\n\n')
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
                break

        return passages, sources

    def finalize_answer(self, query: str, passages: List[str], sources: List[str]) -> str:
        """
        Generates the final factual extraction result.
        It should directly address the question without adding extraneous info.
        Useful for creating exam questions and flashcards. Do not fabricate unknown info.
        """
        prompt_template = ChatPromptTemplate.from_messages([
            SystemMessage(content=(
                "You are an AI assistant tasked with extracting the most factual and relevant information to answer the question. "
                "Do not add details not present in the passages. "
                "Focus on providing concise, accurate facts that help answer the query, suitable for exam preparation or flashcards. "
                "If a particular detail like a definition, property, date, color, name, etc. is relevant, include it."
            )),
            HumanMessage(content=f"""
Question:
{query}

Consolidated Passages and Sources:
{''.join([f"Source: {source}\nPassage: {passage}\n\n" for passage, source in zip(passages, sources)])}

Final Extracted Facts:
""")
        ])

        try:
            response = self._model.invoke(prompt_template.format(query=query))
            if isinstance(response, list):
                answer = response[-1].content if response else ""
            elif hasattr(response, 'content'):
                answer = response.content
            else:
                answer = str(response)

            return answer.strip()
        except Exception as e:
            logger.error(f"Error during answer finalization: {e}", exc_info=True)
            return "Przepraszam, wystąpił problem podczas generowania końcowej odpowiedzi."



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

    def __init__(self, model_name: str = "gpt-4o-mini-2024-07-18", openai_api_key: str = None):
        super().__init__()
        if not openai_api_key:
            raise ValueError("OpenAI API key is not set.")
        self._model = ChatOpenAI(model_name=model_name, openai_api_key=openai_api_key)
        self._output_parser = JsonOutputParser()

    def _run(self, input_str: str) -> str:
        """
        Generate exams based on the input string and save them to the database.

        Args:
            input_str: A JSON-formatted string containing 'description' and 'query'.

        Returns:
            A string confirming the operation in JSON format or an error message.
        """
        try:
            # Parsowanie wejścia JSON
            input_data = json.loads(input_str)
            description = input_data.get('description', 'Matematyka - Algebra').strip()
            query = input_data.get('query', 'Stwórz egzamin z algebry dla uczniów szkoły średniej, zawierający 10 pytań.').strip()

            # Konstruowanie prompta bezpośrednio w metodzie _run z przykładem poprawnego wyjścia
            system_prompt = "Zwróć tylko w formacie JSON bez dodatkowego tekstu. Odpowiedź napisz w odpowiednim języku!"
            user_prompt = f"""
Generate an exam based on the following context:
{description}

And execute the user's command: {query}
Please make the exact number of questions as specified by the user.

The generated exam should be in the user's language, which is the same language as the description and title.
Please generate exactly the number of questions as specified in the user's command.

Consider the best way to format the exam, the optimal combination of questions and answers.
Please also think about what the name of the exam should be and its description.

Provide the exam in the exact following JSON format with an example:

{{
    "topic": "Matematyka - Algebra",
    "description": "Egzamin z podstaw algebry dla uczniów szkół średnich.",
    "num_of_questions": 10,
    "questions": [
        {{
            "question": "Jakie jest rozwiązanie równania 2x + 3 = 7?",
            "answers": [
                {{"text": "x = 1", "is_correct": false}},
                {{"text": "x = 2", "is_correct": true}},
                {{"text": "x = 3", "is_correct": false}},
                {{"text": "x = 4", "is_correct": false}}
            ]
        }},
        {{
            "question": "Rozwiąż równanie kwadratowe x² - 5x + 6 = 0.",
            "answers": [
                {{"text": "x = 2 i x = 3", "is_correct": true}},
                {{"text": "x = 1 i x = 6", "is_correct": false}},
                {{"text": "x = -2 i x = -3", "is_correct": false}},
                {{"text": "x = 0 i x = 5", "is_correct": false}}
            ]
        }},
        // Dodaj więcej zadań w przykładzie, aż do liczby podanej przez użytkownika
        {{
            "question": "Oblicz pochodną funkcji f(x) = x^3 - 4x + 1.",
            "answers": [
                {{"text": "f'(x) = 3x^2 - 4", "is_correct": true}},
                {{"text": "f'(x) = 3x^2 - 4x", "is_correct": false}},
                {{"text": "f'(x) = x^2 - 4", "is_correct": false}},
                {{"text": "f'(x) = 3x - 4", "is_correct": false}}
            ]
        }}
        // ... kontynuuj aż do liczby zadań podanej przez użytkownika
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

            # Sprawdzenie, czy `parsed_response` jest słownikiem
            if not isinstance(parsed_response, dict):
                logger.error("Parsed response is not a dictionary.")
                return json.dumps({
                    "error": "Nieprawidłowa odpowiedź modelu. Oczekiwano formatu JSON."
                }, ensure_ascii=False)

            # Walidacja struktury egzaminu
            requested_num_questions = parsed_response.get('num_of_questions', 10)
            questions = parsed_response.get('questions', [])
            topic = parsed_response.get('topic', f'exam_{uuid.uuid4().hex[:8]}')
            exam_description = parsed_response.get('description', 'Brak opisu egzaminu.')

            # Sprawdzenie, czy liczba pytań jest zgodna z żądaniem
            if len(questions) != requested_num_questions:
                logger.error(f"Oczekiwano {requested_num_questions} pytań, ale otrzymano {len(questions)}.")
                return json.dumps({
                    "error": f"Oczekiwano {requested_num_questions} pytań, ale otrzymano {len(questions)}."
                }, ensure_ascii=False)

            # Konwersja odpowiedzi do stringa JSON
            exam_json = json.dumps({
                "topic": topic,
                "description": exam_description,
                "num_of_questions": requested_num_questions,
                "questions": questions
            }, ensure_ascii=False)

            # Zapis egzaminu do bazy danych
            db: Session = SessionLocal()
            try:
                # Tworzenie nowego egzaminu
                new_exam = Exam(name=topic, description=exam_description)
                db.add(new_exam)
                db.commit()
                db.refresh(new_exam)

                # Tworzenie pytań i odpowiedzi związanych z egzaminem
                for q in questions:
                    new_question = ExamQuestion(
                        text=q.get('question', '').strip(),
                        exam_id=new_exam.id
                    )
                    db.add(new_question)
                    db.commit()
                    db.refresh(new_question)

                    for a in q.get('answers', []):
                        new_answer = ExamAnswer(
                            text=a.get('text', '').strip(),
                            is_correct=a.get('is_correct', False),
                            question_id=new_question.id
                        )
                        db.add(new_answer)
                    db.commit()

                logger.info(f"Successfully created exam with ID {new_exam.id} and saved {len(questions)} questions.")

                # Formułowanie odpowiedzi do zwrócenia
                formatted_response = f"""Topic: "{topic}"
Description: "{exam_description}"
Requested Number of Questions: {requested_num_questions}
Questions:
"""
                for idx, question in enumerate(questions, start=1):
                    formatted_response += f'{idx}. Q: "{question.get("question", "")}"\n'
                    for a_idx, answer in enumerate(question.get('answers', []), start=1):
                        correct_marker = " (Correct)" if answer.get("is_correct") else ""
                        formatted_response += f'   {a_idx}. A: "{answer.get("text", "")}"{correct_marker}\n'
                    formatted_response += '\n'

                return formatted_response

            except Exception as e:
                db.rollback()
                logger.error(f"Database error: {e}")
                return json.dumps({
                    "error": f"Błąd zapisu do bazy danych: {str(e)}"
                }, ensure_ascii=False)
            finally:
                db.close()
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            return json.dumps({
                "error": "Przepraszam, wystąpił problem z generowaniem egzaminu."
            }, ensure_ascii=False)


    async def _arun(self, input_str: str) -> str:
        """Asynchronous version of the run method."""
        return self._run(input_str)