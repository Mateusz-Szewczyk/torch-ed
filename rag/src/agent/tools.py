from typing import List, Tuple, Any, Dict

from dotenv import load_dotenv
from langchain.tools import BaseTool
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import PrivateAttr, Field
import logging
import json
import uuid
import asyncio

import redis.asyncio as redis

# Assuming a project structure where models and search_engine are in a parent directory
from ..models import Exam, ExamQuestion, ExamAnswer, Deck, Flashcard
from ..database import SessionLocal
from ..search_engine import search_and_rerank
from langchain_openai import OpenAIEmbeddings
import os

load_dotenv()
logger = logging.getLogger(__name__)
redis_client = None


async def init_redis():
    global redis_client
    if redis_client is None:
        redis_client = await redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))
    return redis_client


async def cleanup_redis():
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None


async def clear_user_cache(user_id: str):
    """Clears all cache for user - for debugging purposes"""
    redis_client = await init_redis()
    pattern = f"*:{user_id}:*"
    keys = await redis_client.keys(pattern)
    if keys:
        await redis_client.delete(*keys)
        print(f"[DEBUG] Cleared {len(keys)} cache entries for user {user_id}")


embedding_model = OpenAIEmbeddings(model="text-embedding-3-large")


class FlashcardGenerator(BaseTool):
    name: str = "FlashcardGenerator"
    description: str = """Generates high-quality, educational flashcards in JSON format based on provided text."""
    user_id: str = Field(..., description="User ID for tracking flashcard ownership")
    api_key: str = Field(..., description="API key for the LLM provider")
    _model: Any = PrivateAttr()
    _output_parser: JsonOutputParser = PrivateAttr()

    def __init__(self, user_id: str, api_key: str, model_name: str = "gpt-4o-mini-2024-07-18"):
        super().__init__(user_id=user_id, api_key=api_key)
        self.user_id = user_id
        if not api_key:
            raise ValueError("OpenAI API key is required.")
        self._model = ChatOpenAI(model_name=model_name, openai_api_key=api_key, temperature=0.1)
        self._output_parser = JsonOutputParser()

    async def _run(self, input_str: str) -> str:
        try:
            print(f"[DEBUG] FlashcardGenerator._run - Input: {input_str[:200]}...")

            # Inicjalizuj klienta Redis
            redis_client = await init_redis()

            input_data = json.loads(input_str)
            context = input_data.get('description', '').strip()
            query = input_data.get('query', 'Stwórz 5 fiszek').strip()

            print(f"[DEBUG] FlashcardGenerator - Context length: {len(context)}")
            print(f"[DEBUG] FlashcardGenerator - Query: '{query}'")

            cache_key = f"flashcard:{self.user_id}:{hash(query + context)}"
            if cached_result := await redis_client.get(cache_key):
                print(f"[DEBUG] FlashcardGenerator found cached result, length: {len(cached_result.decode())}")

                # Walidacja cached result
                try:
                    cached_data = json.loads(cached_result.decode())
                    # Sprawdź czy cached result zawiera prawidłowe fiszki
                    if cached_data.get('flashcards') and len(cached_data.get('flashcards', [])) > 0:
                        print(
                            f"[DEBUG] FlashcardGenerator - Valid cached result with {len(cached_data['flashcards'])} flashcards")

                        # Sprawdź czy fiszki nie zostały już zapisane do bazy
                        # Jeśli nie, zapisz je teraz
                        db = SessionLocal()
                        try:
                            existing_deck = db.query(Deck).filter(
                                Deck.user_id == self.user_id,
                                Deck.name == cached_data['topic']
                            ).first()

                            if not existing_deck:
                                print(f"[DEBUG] FlashcardGenerator - Cached data not in DB, saving now")
                                new_deck = Deck(user_id=self.user_id, name=cached_data['topic'],
                                                description=cached_data['description'])
                                db.add(new_deck)
                                db.flush()
                                flashcard_objects = [
                                    Flashcard(question=card['question'], answer=card['answer'], deck_id=new_deck.id)
                                    for card in cached_data['flashcards']
                                ]
                                db.bulk_save_objects(flashcard_objects)
                                db.commit()
                                print(f"[DEBUG] FlashcardGenerator - Saved cached data to database")
                            else:
                                print(f"[DEBUG] FlashcardGenerator - Data already exists in database")
                        except Exception as e:
                            db.rollback()
                            print(f"[DEBUG] FlashcardGenerator - Error saving cached data: {e}")
                        finally:
                            db.close()

                        return cached_result.decode()
                    else:
                        print(f"[DEBUG] FlashcardGenerator - Cached result invalid (no flashcards), regenerating")
                        # Usuń nieprawidłowy cache
                        await redis_client.delete(cache_key)
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"[DEBUG] FlashcardGenerator - Cached result corrupted: {str(e)}, regenerating")
                    # Usuń zepsuty cache
                    await redis_client.delete(cache_key)

            # Uniwersalny prompt
            system_prompt = """
You are a specialist in educational content creation. Your task is to generate flashcards based on the provided information.
- Your response must be a single, valid JSON object.
- Create high-quality, educational flashcards based on the provided context and user request.
- Use the user's language (Polish if the request is in Polish).
- Generate the exact number of flashcards requested or a reasonable amount if not specified.
- If the context contains specific information, focus on that. If the context is minimal, use your knowledge about the topic mentioned in the user request.
- Each flashcard should have a clear question and a concise, accurate answer.
"""

            user_prompt = f"""
**Context/Information:**
---
{context}
---

**Your Task:**
Create educational flashcards based on the above information and context.

**Required JSON Output Format:**
{{
  "topic": "Appropriate topic name for the flashcards",
  "description": "Brief description of the flashcard set",
  "flashcards": [
    {{"question": "Question 1", "answer": "Answer 1"}},
    {{"question": "Question 2", "answer": "Answer 2"}}
  ]
}}
"""

            print(f"[DEBUG] FlashcardGenerator - Sending request to LLM")
            messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
            response = await self._model.ainvoke(messages)
            parsed_response = self._output_parser.parse(response.content)

            if not parsed_response.get('flashcards') or len(parsed_response.get('flashcards', [])) == 0:
                print(f"[DEBUG] FlashcardGenerator - No flashcards generated")
                return json.dumps({
                    "error": "I could not generate flashcards for your query. Please try rephrasing your request."
                }, ensure_ascii=False)

            print(f"[DEBUG] FlashcardGenerator - Generated {len(parsed_response.get('flashcards', []))} flashcards")

            # Zapisz do bazy danych
            db = SessionLocal()
            try:
                new_deck = Deck(user_id=self.user_id, name=parsed_response['topic'],
                                description=parsed_response['description'])
                db.add(new_deck)
                db.flush()
                flashcard_objects = [
                    Flashcard(question=card['question'], answer=card['answer'], deck_id=new_deck.id)
                    for card in parsed_response['flashcards']
                ]
                db.bulk_save_objects(flashcard_objects)
                db.commit()
                result = json.dumps(parsed_response, ensure_ascii=False)
                await redis_client.setex(cache_key, 3600, result)
                print(f"[DEBUG] FlashcardGenerator saved to database and cache")
                return result
            except Exception as e:
                db.rollback()
                logger.error(f"Database error in FlashcardGenerator: {e}")
                print(f"[ERROR] FlashcardGenerator database error: {str(e)}")
                return json.dumps({"error": str(e)}, ensure_ascii=False)
            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error in FlashcardGenerator: {e}")
            print(f"[ERROR] FlashcardGenerator exception: {str(e)}")
            return json.dumps({"error": "Failed to generate flashcards due to an internal error."}, ensure_ascii=False)

    async def _arun(self, input_str: str) -> str:
        return await self._run(input_str)


class RAGTool(BaseTool):
    name: str = "RAGTool"
    description: str = "Uses Retrieval-Augmented Generation for factual answers based on user's uploaded files."
    user_id: str = Field(..., description="User ID for tracking")
    api_key: str = Field(..., description="API key for the LLM provider")
    _model: Any = PrivateAttr()

    def __init__(self, user_id: str, api_key: str, model_name: str = "gpt-4o-mini-2024-07-18"):
        super().__init__(user_id=user_id, api_key=api_key)
        self.user_id = user_id
        if not api_key:
            raise ValueError("OpenAI API key is required.")
        self._model = ChatOpenAI(model_name=model_name, openai_api_key=api_key, temperature=0.1)

    async def generate_multi_queries(self, query: str, k: int = 3) -> List[str]:
        """
        Generates multiple reformulations of the user's question to improve document retrieval.
        This technique increases recall by covering different phrasings and aspects of the query.
        """
        print(f"[DEBUG] RAGTool.generate_multi_queries - Generating {k} query variations for: '{query}'")

        system_prompt = f"""Generate {k} different reformulations of the user's question to improve document retrieval.
Each reformulation should approach the question from a slightly different angle or use different key phrases.
Return one question per line, without enumeration or prefixes.
Use the same language as the original question."""

        user_prompt = f"Original question: {query}"
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]

        try:
            response = await self._model.ainvoke(messages)
            lines = [l.strip() for l in response.content.splitlines() if l.strip()]
            queries = lines[:k] if lines else [query]

            # Always include the original query
            if query not in queries:
                queries.insert(0, query)

            print(f"[DEBUG] RAGTool.generate_multi_queries - Generated queries: {queries}")
            return queries[:k+1]  # Original + k variations
        except Exception as e:
            logger.warning(f"Multi-query generation failed: {e}, using original query only")
            return [query]

    async def _run(self, query: str) -> str:
        print(f"[DEBUG] RAGTool._run - Starting with query: '{query}'")

        # Inicjalizuj klienta Redis
        redis_client = await init_redis()

        cache_key = f"rag:{self.user_id}:{hash(query)}"
        if cached_result := await redis_client.get(cache_key):
            print(f"[DEBUG] RAGTool._run - Found cached result, length: {len(cached_result.decode())}")
            return cached_result.decode()

        # Multi-Query RAG: generuj wiele reformulacji zapytania
        print(f"[DEBUG] RAGTool._run - Generating multiple query variations")
        queries = await self.generate_multi_queries(query, k=3)

        try:
            # Wykonaj wyszukiwanie dla każdej wersji zapytania
            all_results = []
            for q in queries:
                print(f"[DEBUG] RAGTool._run - Searching with query: '{q[:50]}...'")
                results = await asyncio.to_thread(
                    search_and_rerank,
                    q,
                    user_id=self.user_id,
                    n_results=5
                )
                if results:
                    all_results.extend(results)

            print(f"[DEBUG] RAGTool._run - Total results before dedup: {len(all_results)}")

            # Deduplikacja po _id
            seen = set()
            dedup_results = []
            for r in all_results:
                rid = r.get("_id") or r.get("metadata", {}).get("_id")
                if rid and rid not in seen:
                    seen.add(rid)
                    dedup_results.append(r)

            print(f"[DEBUG] RAGTool._run - Results after dedup: {len(dedup_results)}")

            # Sortuj po final_score (już obliczony w search_and_rerank)
            dedup_results.sort(key=lambda x: x.get("final_score", 0), reverse=True)
            top_docs = dedup_results[:5]

            print(f"[DEBUG] RAGTool._run - Top docs count: {len(top_docs)}")

            external_passages = [doc.get('content', '') for doc in top_docs if doc.get('content', '').strip()]
            print(f"[DEBUG] RAGTool._run - Valid passages count: {len(external_passages)}")
            print(f"[DEBUG] RAGTool._run - Passages lengths: {[len(p) for p in external_passages]}")

            if not external_passages:
                print(f"[DEBUG] RAGTool._run - No content found in passages")
                return ""

            result = await self.finalize_answer(query, external_passages)
            print(f"[DEBUG] RAGTool._run - Final result length: {len(result)}")

            await redis_client.setex(cache_key, 3600, result)
            return result
        except Exception as e:
            print(f"[ERROR] RAGTool._run - Exception: {str(e)}")
            logger.error(f"Error in RAGTool: {e}")
            return "Error: Could not retrieve an answer from your files."

    async def generate_hyde_answer(self, query: str) -> str:
        """Legacy method - kept for backward compatibility. Multi-query is now preferred."""
        print(f"[DEBUG] RAGTool.generate_hyde_answer - Query: '{query}'")
        system_prompt = "Generate a concise, hypothetical answer containing key phrases relevant to the user's question."
        user_prompt = f"Question: {query}"
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
        response = await self._model.ainvoke(messages)
        print(f"[DEBUG] RAGTool.generate_hyde_answer - Generated: '{response.content.strip()}'")
        return response.content.strip()

    async def finalize_answer(self, query: str, passages: List[str]) -> str:
        """
        Synthesizes the retrieved passages into a coherent answer.
        Uses an improved prompt that:
        - Forces the model to use ONLY the provided passages
        - Minimizes hallucinations
        - Implicitly cites relevant passages
        - Handles cases where info is not in passages
        """
        print(f"[DEBUG] RAGTool.finalize_answer - Query: '{query}'")
        print(f"[DEBUG] RAGTool.finalize_answer - Number of passages: {len(passages)}")
        print(
            f"[DEBUG] RAGTool.finalize_answer - Passages preview: {[p[:100] + '...' if len(p) > 100 else p for p in passages[:2]]}")

        # Improved RAG prompt v2
        system_prompt = """You are a precise assistant that answers questions based ONLY on the provided passages.

CRITICAL RULES:
1. Answer ONLY using information from the provided passages. Do not use external knowledge.
2. If the answer is not fully contained in the passages, explicitly say: "Based on the provided documents, I don't have complete information about this."
3. When possible, implicitly reference which passage the information comes from (e.g., "According to the document...").
4. Keep the answer concise but complete - aim for 2-4 paragraphs unless the question requires more detail.
5. Respond in the same language as the user's question.
6. If passages contain conflicting information, acknowledge this and present both perspectives.
7. Do not make up facts or extrapolate beyond what's in the passages."""

        # Format passages with numbers for better context
        formatted_passages = "\n\n".join([
            f"[Passage {i+1}]:\n{p}" for i, p in enumerate(passages)
        ])

        user_prompt = f"""**User Question:**
{query}

**Available Passages from User's Documents:**
---
{formatted_passages}
---

**Instructions:**
Using ONLY the information from the passages above, provide a clear and accurate answer to the user's question. If the passages don't contain enough information to fully answer the question, acknowledge this limitation."""

        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
        response = await self._model.ainvoke(messages)

        print(f"[DEBUG] RAGTool.finalize_answer - Generated answer length: {len(response.content)}")
        return response.content.strip()

    async def _arun(self, input_str: str) -> str:
        return await self._run(input_str)


class ExamGenerator(BaseTool):
    name: str = "ExamGenerator"
    description: str = """Generates a multi-question exam in JSON format from a given text context."""
    user_id: str = Field(..., description="User ID for tracking")
    openai_api_key: str = Field(..., description="API key for OpenAI")
    _model: ChatOpenAI = PrivateAttr()
    _output_parser: JsonOutputParser = PrivateAttr()

    def __init__(self, user_id: str, openai_api_key: str, model_name: str = "gpt-4o-mini-2024-07-18"):
        super().__init__(user_id=user_id, openai_api_key=openai_api_key)
        self.user_id = user_id
        if not openai_api_key:
            raise ValueError("OpenAI API key is required.")
        self._model = ChatOpenAI(model_name=model_name, openai_api_key=openai_api_key, temperature=0.15)
        self._output_parser = JsonOutputParser()

    async def _run(self, input_str: str) -> str:
        try:
            print(f"[DEBUG] ExamGenerator._run - Input: {input_str[:200]}...")

            # Inicjalizuj klienta Redis
            redis_client = await init_redis()

            input_data = json.loads(input_str)
            context = input_data.get('description', '').strip()
            query = input_data.get('query', '').strip()

            print(f"[DEBUG] ExamGenerator - Context length: {len(context)}")
            print(f"[DEBUG] ExamGenerator - Query: '{query}'")

            cache_key = f"exam:{self.user_id}:{hash(query + context)}"
            if cached_result := await redis_client.get(cache_key):
                print(f"[DEBUG] ExamGenerator found cached result, length: {len(cached_result.decode())}")

                # Walidacja cached result
                try:
                    cached_data = json.loads(cached_result.decode())
                    # Sprawdź czy cached result zawiera prawidłowe pytania
                    if cached_data.get('questions') and len(cached_data.get('questions', [])) > 0:
                        print(
                            f"[DEBUG] ExamGenerator - Valid cached result with {len(cached_data['questions'])} questions")

                        # Sprawdź czy egzamin nie został już zapisany do bazy
                        db = SessionLocal()
                        try:
                            existing_exam = db.query(Exam).filter(
                                Exam.user_id == self.user_id,
                                Exam.name == cached_data['topic']
                            ).first()

                            if not existing_exam:
                                print(f"[DEBUG] ExamGenerator - Cached data not in DB, saving now")
                                new_exam = Exam(user_id=self.user_id, name=cached_data['topic'],
                                                description=cached_data['description'])
                                db.add(new_exam)
                                db.flush()
                                for question_data in cached_data['questions']:
                                    new_question = ExamQuestion(text=question_data['question'], exam_id=new_exam.id)
                                    db.add(new_question)
                                    db.flush()
                                    answer_objects = [
                                        ExamAnswer(
                                            text=answer_data['text'],
                                            is_correct=answer_data['is_correct'],
                                            question_id=new_question.id
                                        ) for answer_data in question_data['answers']
                                    ]
                                    db.bulk_save_objects(answer_objects)
                                db.commit()
                                print(f"[DEBUG] ExamGenerator - Saved cached data to database")
                            else:
                                print(f"[DEBUG] ExamGenerator - Data already exists in database")
                        except Exception as e:
                            db.rollback()
                            print(f"[DEBUG] ExamGenerator - Error saving cached data: {e}")
                        finally:
                            db.close()

                        return cached_result.decode()
                    else:
                        print(f"[DEBUG] ExamGenerator - Cached result invalid (no questions), regenerating")
                        # Usuń nieprawidłowy cache
                        await redis_client.delete(cache_key)
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"[DEBUG] ExamGenerator - Cached result corrupted: {str(e)}, regenerating")
                    # Usuń zepsuty cache
                    await redis_client.delete(cache_key)

            # Uniwersalny prompt
            system_prompt = """
You are a professional educator and assessment designer. Your role is to create a fair and challenging exam.
- Your response must be a single, valid JSON object conforming perfectly to the requested schema.
- Create exam questions based on the provided context and user request.
- Use the user's language (Polish if the request is in Polish).
- Generate the exact number of questions requested or a reasonable amount if not specified.
- If the context contains specific information, focus on that. If the context is minimal, use your knowledge about the topic mentioned in the user request.
- Each question should have exactly 4 answers: one correct and three plausible distractors.
"""

            user_prompt = f"""
**Context/Information:**
---
{context}
---

**Your Task:**
Create an exam based on the above information and context.

**Required JSON Output Format:**
{{
  "topic": "Exam Topic",
  "description": "A concise description of the exam's content.",
  "num_of_questions": <integer>,
  "questions": [
    {{
      "question": "A specific question about the topic.",
      "answers": [
        {{"text": "A plausible but incorrect answer (distractor).", "is_correct": false}},
        {{"text": "The single correct answer.", "is_correct": true}},
        {{"text": "Another plausible but incorrect answer.", "is_correct": false}},
        {{"text": "A third plausible but incorrect answer.", "is_correct": false}}
      ]
    }}
  ]
}}
"""

            print(f"[DEBUG] ExamGenerator - Sending request to LLM")
            messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
            response = await self._model.ainvoke(messages)
            parsed_response = self._output_parser.parse(response.content)

            if not parsed_response.get('questions') or len(parsed_response.get('questions', [])) == 0:
                print(f"[DEBUG] ExamGenerator - No questions generated")
                return json.dumps({
                    "error": "I could not generate exam questions for your query. Please try rephrasing your request."
                }, ensure_ascii=False)

            print(f"[DEBUG] ExamGenerator - Generated {len(parsed_response.get('questions', []))} questions")

            # Zapisz do bazy danych
            db = SessionLocal()
            try:
                new_exam = Exam(user_id=self.user_id, name=parsed_response['topic'],
                                description=parsed_response['description'])
                db.add(new_exam)
                db.flush()
                for question_data in parsed_response['questions']:
                    new_question = ExamQuestion(text=question_data['question'], exam_id=new_exam.id)
                    db.add(new_question)
                    db.flush()
                    answer_objects = [
                        ExamAnswer(
                            text=answer_data['text'],
                            is_correct=answer_data['is_correct'],
                            question_id=new_question.id
                        ) for answer_data in question_data['answers']
                    ]
                    db.bulk_save_objects(answer_objects)
                db.commit()
                result = json.dumps(parsed_response, ensure_ascii=False)
                await redis_client.setex(cache_key, 3600, result)
                print(f"[DEBUG] ExamGenerator saved to database and cache")
                return result
            except Exception as e:
                db.rollback()
                logger.error(f"Database error during exam save: {e}")
                print(f"[ERROR] ExamGenerator database error: {str(e)}")
                return json.dumps({"error": str(e)}, ensure_ascii=False)
            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error in ExamGenerator: {e}")
            print(f"[ERROR] ExamGenerator exception: {str(e)}")
            return json.dumps({"error": "Failed to generate the exam due to an internal error."}, ensure_ascii=False)

    async def _arun(self, input_str: str) -> str:
        return await self._run(input_str)


class DirectAnswer(BaseTool):
    name: str = "DirectAnswer"
    description: str = "Provides direct answers and guides the user to the correct tool for their query."
    model: ChatOpenAI

    class Config:
        arbitrary_types_allowed = True

    async def _run(self, query: str, aggregated_context: str = "") -> str:
        logger.debug(f"DirectAnswer processing query: {query}")
        try:
            # Simple keyword-based routing for tool guidance
            query_lower = query.lower()
            if any(kw in query_lower for kw in ["fiszki", "flashcard"]):
                return "To create flashcards, please select the **'Generowanie fiszek'** tool and ask your question again."
            if any(kw in query_lower for kw in ["egzamin", "exam", "test", "quiz"]):
                return "To create an exam, please select the **'Generowanie egzaminu'** tool and ask your question again."

            # If no special tool is needed, proceed with generating a direct answer
            if not aggregated_context:
                return "I don't have any specific context to answer your question. Please try using the file or web search tools, or ask a general knowledge question."

            system_prompt = "You are a helpful AI assistant. Based on the provided context, give a clear and concise answer to the user's question. Respond in the user's language."
            final_prompt = f"""
**Context:**
---
{aggregated_context}
---

**Question:** {query}

**Answer:**
"""
            messages = [SystemMessage(content=system_prompt), HumanMessage(content=final_prompt)]
            response = await self.model.ainvoke(messages)
            return response.content.strip()
        except Exception as e:
            logger.error(f"Error in DirectAnswer: {e}", exc_info=True)
            return "Apologies, but I encountered a problem while generating an answer."
