from typing import List, Tuple, Any, Dict
from langchain.tools import BaseTool
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import PrivateAttr
import logging
import json
import uuid
import asyncio

from pydantic.fields import Field
from redis.asyncio import Redis
from ..models import Exam, ExamQuestion, ExamAnswer, Deck, Flashcard
from ..database import SessionLocal
from ..search_engine import search_and_rerank
from langchain_openai import OpenAIEmbeddings
import os

logger = logging.getLogger(__name__)
redis_client = Redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))

embedding_model = OpenAIEmbeddings(model="text-embedding-3-large")


class FlashcardGenerator(BaseTool):
    name: str = "FlashcardGenerator"
    description: str = """Generates flashcards in JSON format with questions and answers."""
    user_id: str = Field(..., description="User ID for tracking flashcard ownership")
    model_type: str = Field(default="OpenAI", description="Type of LLM to use")
    model_name: str = Field(default="gpt-4o-mini-2024-07-18", description="Name of the LLM model")
    api_key: str = Field(..., description="API key for the LLM provider")
    _model: Any = PrivateAttr()
    _output_parser: JsonOutputParser = PrivateAttr()

    def __init__(self, user_id: str, model_type: str = "OpenAI", model_name: str = "gpt-4o-mini-2024-07-18", api_key: str = None):
        super().__init__(
            user_id=user_id,
            model_type=model_type,
            model_name=model_name,
            api_key=api_key
        )
        self.user_id = user_id
        if model_type == "OpenAI":
            if not api_key:
                raise ValueError("OpenAI API key is required.")
            self._model = ChatOpenAI(model_name=model_name, openai_api_key=api_key, temperature=0.2)
        else:
            raise ValueError("Only OpenAI model is supported.")
        self._output_parser = JsonOutputParser()

    async def _run(self, input_str: str) -> str:
        try:
            input_data = json.loads(input_str)
            description = input_data.get('description', 'Serial Arcane').strip()
            query = input_data.get('query', 'Stwórz 5 fiszek o serialu Arcane').strip()

            cache_key = f"flashcard:{self.user_id}:{hash(query)}"
            cached_result = await redis_client.get(cache_key)
            if cached_result:
                return cached_result.decode()

            system_prompt = "Return JSON with flashcards. Use user's language. Generate exact number specified."
            user_prompt = f"""
Generate {query} based on:
Context: {description}
Return JSON:
{{
  "topic": "Deck Name",
  "description": "Deck Description",
  "flashcards": [
    {{"question": "Q1", "answer": "A1"}},
    {{"question": "Q2", "answer": "A2"}}
  ]
}}
"""
            messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
            response = await self._model.ainvoke(messages)
            parsed_response = self._output_parser.parse(response.content)

            flashcards = parsed_response.get('flashcards', [])
            topic = parsed_response.get('topic', f'deck_{uuid.uuid4().hex[:8]}')
            description = parsed_response.get('description', 'No description')

            db = SessionLocal()
            try:
                new_deck = Deck(user_id=self.user_id, name=topic, description=description)
                db.add(new_deck)
                db.flush()
                flashcard_objects = [
                    Flashcard(question=card['question'], answer=card['answer'], deck_id=new_deck.id)
                    for card in flashcards
                ]
                db.bulk_save_objects(flashcard_objects)
                db.commit()
                result = json.dumps({
                    "topic": topic,
                    "description": description,
                    "flashcards": flashcards
                }, ensure_ascii=False)
                await redis_client.setex(cache_key, 3600, result)
                return result
            except Exception as e:
                db.rollback()
                logger.error(f"Database error: {e}")
                return json.dumps({"error": str(e)}, ensure_ascii=False)
            finally:
                db.close()
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid JSON input."}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error in FlashcardGenerator: {e}")
            return json.dumps({"error": "Failed to generate flashcards."}, ensure_ascii=False)

    async def _arun(self, input_str: str) -> str:
        return await self._run(input_str)


class RAGTool(BaseTool):
    name: str = "RAGTool"
    description: str = "Uses Retrieval-Augmented Generation for factual answers."
    user_id: str = Field(..., description="User ID for tracking")
    model_type: str = Field(default="OpenAI", description="Type of LLM to use")
    model_name: str = Field(default="gpt-4o-mini-2024-07-18", description="Name of the LLM model")
    api_key: str = Field(..., description="API key for the LLM provider")
    _model: Any = PrivateAttr()

    def __init__(self, user_id: str, model_type: str = "OpenAI", model_name: str = "gpt-4o-mini-2024-07-18", api_key: str = None):
        super().__init__(
            user_id=user_id,
            model_type=model_type,
            model_name=model_name,
            api_key=api_key
        )
        self.user_id = user_id
        if model_type == "OpenAI":
            if not api_key:
                raise ValueError("OpenAI API key is required.")
            self._model = ChatOpenAI(model_name=model_name, openai_api_key=api_key, temperature=0.2)
        else:
            raise ValueError("Only OpenAI model is supported.")

    async def _run(self, query: str) -> str:
        cache_key = f"rag:{self.user_id}:{hash(query)}"
        cached_result = await redis_client.get(cache_key)
        if cached_result:
            return cached_result.decode()

        hyde_answer = await self.generate_hyde_answer(query)
        try:
            results = await asyncio.to_thread(search_and_rerank, hyde_answer, user_id=self.user_id, n_results=5)
            external_passages = [doc.get('content', '') for doc in results]
            result = await self.finalize_answer(query, external_passages)
            await redis_client.setex(cache_key, 3600, result)
            return result
        except Exception as e:
            logger.error(f"Error in RAGTool: {e}")
            return "Nie udało się wygenerować odpowiedzi."

    async def generate_hyde_answer(self, query: str) -> str:
        system_prompt = "Generate a concise, hypothetical answer with key phrases."
        user_prompt = f"Question: {query}\nAnswer concisely."
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
        response = await self._model.ainvoke(messages)
        return response.content.strip()

    async def finalize_answer(self, query: str, passages: List[str]) -> str:
        system_prompt = "Produce a concise, factual answer using provided information."
        user_prompt = f"Question: {query}\nPassages:\n{''.join([f'Passage: {p}\n' for p in passages])}\nAnswer:"
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
        response = await self._model.ainvoke(messages)
        return response.content.strip()

    async def _arun(self, input_str: str) -> str:
        return await self._run(input_str)

class ExamGenerator(BaseTool):
    name: str = "ExamGenerator"
    description: str = """Generates exams in JSON format with topics, descriptions, questions, and answers."""
    user_id: str = Field(..., description="User ID for tracking")
    model_name: str = Field(default="gpt-4o-mini-2024-07-18", description="Name of the LLM model")
    openai_api_key: str = Field(..., description="API key for OpenAI")
    _model: ChatOpenAI = PrivateAttr()
    _output_parser: JsonOutputParser = PrivateAttr()

    def __init__(self, user_id: str, model_name: str = "gpt-4o-mini-2024-07-18", openai_api_key: str = None):
        super().__init__(
            user_id=user_id,
            model_name=model_name,
            openai_api_key=openai_api_key
        )
        self.user_id = user_id
        if not openai_api_key:
            raise ValueError("OpenAI API key is required.")
        self._model = ChatOpenAI(model_name=model_name, openai_api_key=openai_api_key, temperature=0.2)
        self._output_parser = JsonOutputParser()

    async def validate_input(self, input_str: str) -> Tuple[str, str]:
        try:
            input_data = json.loads(input_str)
            description = input_data.get('description', '').strip()
            query = input_data.get('query', '').strip()
            if not description or not query:
                raise ValueError("Both description and query are required")
            return description, query
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON format")

    async def _get_prompts(self, description: str, query: str) -> Tuple[str, str]:
        system_prompt = "Return JSON with exam details. Use user's language. Generate exact number of questions specified."
        user_prompt = f"""
Generate exam based on:
Context: {description}
Command: {query}
Requirements:
- 4 answers per question, 1 correct
- Vary difficulty and topic coverage
- Clear, unambiguous questions
JSON format:
{{
  "topic": "Example Topic",
  "description": "Exam description",
  "num_of_questions": <number>,
  "questions": [
    {{"question": "Q1", "answers": [
      {{"text": "A1", "is_correct": false}},
      {{"text": "A2", "is_correct": true}},
      {{"text": "A3", "is_correct": false}},
      {{"text": "A4", "is_correct": false}}
    ]}}
  ]
}}
"""
        return system_prompt, user_prompt

    async def generate_exam(self, system_prompt: str, user_prompt: str) -> Tuple[str, str, int, List[Dict]]:
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
        response = await self._model.ainvoke(messages)
        parsed_response = self._output_parser.parse(response.content)

        required_fields = ['topic', 'description', 'num_of_questions', 'questions']
        for field in required_fields:
            if field not in parsed_response:
                raise ValueError(f"Missing required field: {field}")

        questions = parsed_response.get('questions', [])
        for i, question in enumerate(questions):
            if len(question.get('answers', [])) != 4 or sum(
                    1 for ans in question['answers'] if ans.get('is_correct')) != 1:
                raise ValueError(f"Invalid question {i + 1} structure")

        return (
            parsed_response['topic'],
            parsed_response['description'],
            parsed_response['num_of_questions'],
            questions
        )

    async def save_to_database(self, topic: str, description: str, questions: List[Dict]) -> int:
        db = SessionLocal()
        try:
            new_exam = Exam(user_id=self.user_id, name=topic, description=description)
            db.add(new_exam)
            db.flush()

            exam_questions = []
            for question in questions:
                new_question = ExamQuestion(text=question['question'], exam_id=new_exam.id)
                db.add(new_question)
                db.flush()  # Flush to get the question ID
                exam_questions.append(new_question)

                for answer in question['answers']:
                    new_answer = ExamAnswer(
                        text=answer['text'],
                        is_correct=answer['is_correct'],
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

    async def _run(self, input_str: str) -> str:
        cache_key = f"exam:{self.user_id}:{hash(input_str)}"
        cached_result = await redis_client.get(cache_key)
        if cached_result:
            return cached_result.decode()

        max_attempts = 3
        best_result = None
        for attempt in range(max_attempts):
            try:
                description, query = await self.validate_input(input_str)
                system_prompt, user_prompt = await self._get_prompts(description, query)
                topic, exam_description, requested_num_questions, questions = await self.generate_exam(system_prompt,
                                                                                                       user_prompt)
                if len(questions) >= requested_num_questions * 0.8:
                    exam_id = await self.save_to_database(topic, exam_description, questions)
                    result = json.dumps({
                        "status": "success",
                        "exam_id": exam_id,
                        "topic": topic,
                        "description": exam_description,
                        "num_of_questions": len(questions),
                        "questions": questions
                    }, ensure_ascii=False)
                    await redis_client.setex(cache_key, 3600, result)
                    return result
                if not best_result or len(questions) > len(best_result[3]):
                    best_result = (topic, exam_description, requested_num_questions, questions)
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed: {e}")
                if attempt == max_attempts - 1 and best_result:
                    topic, exam_description, requested_num_questions, questions = best_result
                    exam_id = await self.save_to_database(topic, exam_description, questions)
                    result = json.dumps({
                        "status": "partial_success",
                        "exam_id": exam_id,
                        "topic": topic,
                        "description": exam_description,
                        "num_of_questions": len(questions),
                        "questions": questions,
                        "warning": f"Could only generate {len(questions)} out of {requested_num_questions} requested questions"
                    }, ensure_ascii=False)
                    await redis_client.setex(cache_key, 3600, result)
                    return result
        return json.dumps({"error": "Failed to generate exam."}, ensure_ascii=False)

    async def _arun(self, input_str: str) -> str:
        return await self._run(input_str)