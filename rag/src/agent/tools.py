import json
import logging
import os
import re
import uuid
import asyncio
from typing import List, Tuple, Any, Dict, Optional

import redis.asyncio as redis
from dotenv import load_dotenv
from pydantic import PrivateAttr, Field

from langchain.tools import BaseTool
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.messages import SystemMessage, HumanMessage

# Zakładamy strukturę projektu, w której modele i search_engine są w katalogu nadrzędnym
from ..models import Exam, ExamQuestion, ExamAnswer, Deck, Flashcard
from ..database import SessionLocal
from ..search_engine import search_and_rerank

load_dotenv()
logger = logging.getLogger(__name__)
redis_client = None


# ================== UTILS ==================

async def init_redis():
    global redis_client
    if redis_client is None:
        redis_client = await redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))
    return redis_client


def parse_json_safely(text: str) -> Dict[str, Any]:
    """
    Wyciąga JSON z tekstu, nawet jeśli model dodał tekst przed/po lub znaczniki markdown.
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Szukaj wzorca JSON (wszystko między klamrami { } )
        match = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        raise ValueError(f"Nie udało się sparsować odpowiedzi JSON modelu: {text[:100]}...")


# ================== TOOLS ==================

class FlashcardGenerator(BaseTool):
    name: str = "FlashcardGenerator"
    description: str = "Generates high-quality, educational flashcards based on provided text context."
    user_id: str = Field(..., description="User ID for tracking ownership")
    api_key: str = Field(..., description="API key for OpenAI")
    _model: Any = PrivateAttr()
    _output_parser: JsonOutputParser = PrivateAttr()

    def __init__(self, user_id: str, api_key: str, model_name: str = "gpt-5-nano"):
        super().__init__(user_id=user_id, api_key=api_key)
        self.user_id = user_id
        # Note: gpt-5-nano only supports temperature=1, so we omit the parameter
        self._model = ChatOpenAI(
            model_name=model_name,
            openai_api_key=api_key,
            model_kwargs={"response_format": {"type": "json_object"}}
        )
        self._output_parser = JsonOutputParser()

    async def _run(self, input_str: str) -> str:
        try:
            redis_client = await init_redis()

            # Próba wyciągnięcia danych z wejścia (obsługa JSON od agenta lub czystego tekstu)
            try:
                input_data = json.loads(input_str)
                context = input_data.get('description', input_str).strip()
                query = input_data.get('query', 'Stwórz fiszki').strip()
            except json.JSONDecodeError:
                context = input_str
                query = "Stwórz zestaw fiszek do nauki"

            cache_key = f"flashcard:{self.user_id}:{hash(query + context)}"
            if cached_result := await redis_client.get(cache_key):
                return cached_result.decode()

            system_prompt = """You are a specialist in educational content. 
You MUST return a valid JSON object in the following format:
{
  "topic": "Name of the set",
  "description": "Short description",
  "flashcards": [
    {"question": "Question text", "answer": "Answer text"},
    ...
  ]
}
Use the user's language (default: Polish)."""

            user_prompt = f"Context:\n{context}\n\nTask: {query}"
            messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]

            response = await self._model.ainvoke(messages)
            parsed_response = parse_json_safely(response.content)

            if not parsed_response.get('flashcards'):
                return json.dumps({"error": "Model nie wygenerował żadnych fiszek."}, ensure_ascii=False)

            # Zapis do bazy danych
            db = SessionLocal()
            try:
                new_deck = Deck(
                    user_id=self.user_id,
                    name=parsed_response.get('topic', 'Nowy zestaw'),
                    description=parsed_response.get('description', '')
                )
                db.add(new_deck)
                db.flush()

                flashcards = [
                    Flashcard(question=f['question'], answer=f['answer'], deck_id=new_deck.id)
                    for f in parsed_response['flashcards']
                ]
                db.bulk_save_objects(flashcards)
                db.commit()

                # Dodaj metadane do odpowiedzi dla frontendu
                result_with_meta = {
                    **parsed_response,
                    "_metadata": {
                        "type": "flashcards",
                        "deck_id": new_deck.id,
                        "deck_name": new_deck.name,
                        "count": len(flashcards)
                    }
                }
                result = json.dumps(result_with_meta, ensure_ascii=False)
                await redis_client.setex(cache_key, 3600, result)
                return result
            except Exception as e:
                db.rollback()
                logger.error(f"Database error in FlashcardGenerator: {e}")
                return json.dumps({"error": f"Błąd bazy danych: {str(e)}"}, ensure_ascii=False)
            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error in FlashcardGenerator: {e}")
            return json.dumps({"error": f"Błąd generowania fiszek: {str(e)}"}, ensure_ascii=False)

    async def _arun(self, input_str: str) -> str:
        return await self._run(input_str)


class ExamGenerator(BaseTool):
    name: str = "ExamGenerator"
    description: str = "Generates a multi-question exam in JSON format based on provided context."
    user_id: str = Field(..., description="User ID")
    openai_api_key: str = Field(..., description="API key")
    _model: Any = PrivateAttr()

    def __init__(self, user_id: str, openai_api_key: str, model_name: str = "gpt-5-nano"):
        super().__init__(user_id=user_id, openai_api_key=openai_api_key)
        self.user_id = user_id
        # Note: gpt-5-nano only supports temperature=1, so we omit the parameter
        self._model = ChatOpenAI(
            model_name=model_name,
            openai_api_key=openai_api_key,
            model_kwargs={"response_format": {"type": "json_object"}}
        )

    async def _run(self, input_str: str) -> str:
        try:
            redis_client = await init_redis()

            try:
                input_data = json.loads(input_str)
                context = input_data.get('description', input_str).strip()
                query = input_data.get('query', 'Stwórz egzamin').strip()
            except json.JSONDecodeError:
                context = input_str
                query = "Stwórz egzamin testowy"

            cache_key = f"exam:{self.user_id}:{hash(query + context)}"
            if cached_result := await redis_client.get(cache_key):
                return cached_result.decode()

            system_prompt = """You are a professional assessment designer. Return ONLY a valid JSON object:
{
  "topic": "Exam Title",
  "description": "Description",
  "questions": [
    {
      "question": "Question text",
      "answers": [
        {"text": "Option 1", "is_correct": false},
        {"text": "Option 2", "is_correct": true}
      ],
      ...
    }
  ]
}"""
            user_prompt = f"Context:\n{context}\n\nTask: {query}"
            messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]

            response = await self._model.ainvoke(messages)
            parsed_response = parse_json_safely(response.content)

            db = SessionLocal()
            try:
                new_exam = Exam(
                    user_id=self.user_id,
                    name=parsed_response.get('topic', 'Nowy Egzamin'),
                    description=parsed_response.get('description', '')
                )
                db.add(new_exam)
                db.flush()

                question_count = 0
                for q_data in parsed_response['questions']:
                    new_q = ExamQuestion(text=q_data['question'], exam_id=new_exam.id)
                    db.add(new_q)
                    db.flush()
                    question_count += 1
                    for a_data in q_data['answers']:
                        db.add(ExamAnswer(text=a_data['text'], is_correct=a_data['is_correct'], question_id=new_q.id))

                db.commit()

                # Dodaj metadane do odpowiedzi dla frontendu
                result_with_meta = {
                    **parsed_response,
                    "_metadata": {
                        "type": "exam",
                        "exam_id": new_exam.id,
                        "exam_name": new_exam.name,
                        "count": question_count
                    }
                }
                result = json.dumps(result_with_meta, ensure_ascii=False)
                await redis_client.setex(cache_key, 3600, result)
                return result
            except Exception as e:
                db.rollback()
                return json.dumps({"error": f"Database error: {str(e)}"}, ensure_ascii=False)
            finally:
                db.close()
        except Exception as e:
            return json.dumps({"error": f"Exam generation failed: {str(e)}"}, ensure_ascii=False)

    async def _arun(self, input_str: str) -> str:
        return await self._run(input_str)


class RAGTool(BaseTool):
    name: str = "RAGTool"
    description: str = "Retrieves factual information from the user's uploaded documents."
    user_id: str = Field(..., description="User ID")
    api_key: str = Field(..., description="API key")
    _model: Any = PrivateAttr()

    def __init__(self, user_id: str, api_key: str, model_name: str = "gpt-5-nano"):
        super().__init__(user_id=user_id, api_key=api_key)
        self.user_id = user_id
        # Note: gpt-5-nano only supports temperature=1, so we omit the parameter
        self._model = ChatOpenAI(model_name=model_name, openai_api_key=api_key)

    async def _run(self, query: str) -> str:
        try:
            redis_client = await init_redis()
            cache_key = f"rag:{self.user_id}:{hash(query)}"
            if cached_result := await redis_client.get(cache_key):
                return cached_result.decode()

            results = await asyncio.to_thread(search_and_rerank, query, user_id=self.user_id, n_results=5)
            passages = [r.get('content', '') for r in results if r.get('content')]

            if not passages:
                return "Nie znalazłem żadnych informacji w Twoich plikach na ten temat."

            system_prompt = "Answer the question based ONLY on the provided passages. Use the same language as the query."
            formatted_passages = "\n\n".join([f"[Doc {i + 1}]: {p}" for i, p in enumerate(passages)])
            user_prompt = f"Question: {query}\n\nPassages:\n{formatted_passages}"

            response = await self._model.ainvoke(
                [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
            result = response.content.strip()

            await redis_client.setex(cache_key, 3600, result)
            return result
        except Exception as e:
            logger.error(f"RAG Error: {e}")
            return f"Wystąpił błąd podczas przeszukiwania plików."

    async def _arun(self, input_str: str) -> str:
        return await self._run(input_str)


class DirectAnswer(BaseTool):
    name: str = "DirectAnswer"
    description: str = "Provides direct conversational answers or routes to specific tools."
    model: ChatOpenAI

    class Config:
        arbitrary_types_allowed = True

    async def _run(self, query: str, aggregated_context: str = "") -> str:
        try:
            query_l = query.lower()
            if any(k in query_l for k in ["fiszki", "fiszek"]):
                return "Aby stworzyć fiszki, zaznacz narzędzie 'Generowanie fiszek' i sprecyzuj temat."
            if any(k in query_l for k in ["egzamin", "test", "quiz"]):
                return "Aby stworzyć egzamin, zaznacz narzędzie 'Generowanie egzaminu'."

            system_prompt = "You are a helpful education assistant. Use the provided context to answer concisely."
            prompt = f"Context:\n{aggregated_context}\n\nQuestion: {query}"

            response = await self.model.ainvoke([SystemMessage(content=system_prompt), HumanMessage(content=prompt)])
            return response.content.strip()
        except Exception as e:
            return "Wystąpił błąd podczas generowania odpowiedzi."

    async def _arun(self, query: str) -> str:
        return await self._run(query)
