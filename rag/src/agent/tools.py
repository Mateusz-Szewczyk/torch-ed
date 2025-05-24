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
            # Inicjalizuj klienta Redis
            redis_client = await init_redis()

            input_data = json.loads(input_str)
            context = input_data.get('description', '').strip()
            query = input_data.get('query', 'Stwórz 5 fiszek').strip()
            use_general_knowledge = input_data.get('use_general_knowledge', False)

            cache_key = f"flashcard:{self.user_id}:{hash(query + context)}"
            if cached_result := await redis_client.get(cache_key):
                print(f"[DEBUG] FlashcardGenerator found cached result, length: {len(cached_result.decode())}")
                return cached_result.decode()

            if use_general_knowledge:
                print(f"[DEBUG] FlashcardGenerator using general knowledge mode")
                system_prompt = """
You are a specialist in educational content creation. Your task is to generate flashcards based on your general knowledge about the requested topic.
- Your response must be a single, valid JSON object.
- Generate high-quality, educational flashcards on the requested topic using your training data.
- Use the user's language.
- Create the exact number of flashcards requested or a reasonable amount if not specified.
"""
                user_prompt = f"""
**User Request:** "{query}"

Create educational flashcards for this topic using your general knowledge.

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
            else:
                # Standardowy prompt dla kontekstu z plików
                if not context:
                    return json.dumps({
                        "error": "Cannot generate flashcards without context. Please ask a question about your files or the web first."
                    }, ensure_ascii=False)

                system_prompt = """
You are a specialist in educational content creation. Your task is to generate flashcards based *only* on the provided context.
- Your response must be a single, valid JSON object.
- **Anti-Hallucination Rule**: Do not use any information outside of the provided context. If the context is insufficient to create the requested flashcards, return an empty list for the 'flashcards' key.
- Generate the exact number of flashcards requested in the user's command.
- Use the user's language.
"""
                user_prompt = f"""
**Primary Command:** "{query}"

**Source Material (Context):**
---
{context}
---

**Your Task:**
Following the Primary Command, create a set of flashcards using *only* the Source Material above. The topic and description of the deck must also be derived from the source material.

**Required JSON Output Format:**
{{
  "topic": "Deck Name Related to the Context",
  "description": "A Brief Description of the Flashcard Deck's Content",
  "flashcards": [
    {{"question": "Question 1 about a key fact from the source material", "answer": "Concise answer from the source material"}},
    {{"question": "Question 2 about another key fact from the source material", "answer": "Concise answer from the source material"}}
  ]
}}
"""

            messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
            response = await self._model.ainvoke(messages)
            parsed_response = self._output_parser.parse(response.content)

            if not parsed_response.get('flashcards'):
                return json.dumps({
                    "error": "I could not find enough information in the provided text to generate flashcards for your query."
                }, ensure_ascii=False)

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
                return json.dumps({"error": str(e)}, ensure_ascii=False)
            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error in FlashcardGenerator: {e}")
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

    async def _run(self, query: str) -> str:
        print(f"[DEBUG] RAGTool._run - Starting with query: '{query}'")

        # Inicjalizuj klienta Redis
        redis_client = await init_redis()

        cache_key = f"rag:{self.user_id}:{hash(query)}"
        if cached_result := await redis_client.get(cache_key):
            print(f"[DEBUG] RAGTool._run - Found cached result, length: {len(cached_result.decode())}")
            return cached_result.decode()

        print(f"[DEBUG] RAGTool._run - Generating HyDE answer")
        hyde_answer = await self.generate_hyde_answer(query)
        print(f"[DEBUG] RAGTool._run - HyDE answer: '{hyde_answer}'")

        try:
            print(f"[DEBUG] RAGTool._run - Calling search_and_rerank with user_id: {self.user_id}")
            results = await asyncio.to_thread(search_and_rerank, hyde_answer, user_id=self.user_id, n_results=5)
            print(f"[DEBUG] RAGTool._run - Search results count: {len(results) if results else 0}")
            print(f"[DEBUG] RAGTool._run - Search results preview: {results[:2] if results else 'None'}")

            external_passages = [doc.get('content', '') for doc in results if doc.get('content', '').strip()]
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
        print(f"[DEBUG] RAGTool.generate_hyde_answer - Query: '{query}'")
        system_prompt = "Generate a concise, hypothetical answer containing key phrases relevant to the user's question."
        user_prompt = f"Question: {query}"
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
        response = await self._model.ainvoke(messages)
        print(f"[DEBUG] RAGTool.generate_hyde_answer - Generated: '{response.content.strip()}'")
        return response.content.strip()

    async def finalize_answer(self, query: str, passages: List[str]) -> str:
        print(f"[DEBUG] RAGTool.finalize_answer - Query: '{query}'")
        print(f"[DEBUG] RAGTool.finalize_answer - Number of passages: {len(passages)}")
        print(
            f"[DEBUG] RAGTool.finalize_answer - Passages preview: {[p[:100] + '...' if len(p) > 100 else p for p in passages[:2]]}")

        system_prompt = "You are a helpful assistant. Synthesize the provided passages into a single, cohesive, and concise answer to the user's question. Respond in the user's language."
        user_prompt = f"Question: {query}\n\nPassages:\n{''.join([f'Passage: {p}\n---\n' for p in passages])}\n\nAnswer:"
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

    async def _get_prompts(self, context: str, query: str, use_general_knowledge: bool = False) -> Tuple[str, str]:
        if use_general_knowledge:
            system_prompt = """
You are a professional educator and assessment designer. Your role is to create a fair and challenging exam based on your general knowledge.
- **Format Compliance**: Your output must be a single, valid JSON object conforming perfectly to the requested schema.
- **Language**: Use the same language as the user's command.
- **Quantity**: Fulfill the exact number of questions requested in the command. If not specified, create 5 questions.
"""
            user_prompt = f"""
**Primary Command:** "{query}"

**Your Task:**
Execute the Primary Command by designing an exam using your general knowledge about the requested topic.

**Detailed Requirements:**
1.  **Exam Metadata**: Generate a `topic` and `description` that accurately summarize the exam content.
2.  **Question Design**: Create clear, unambiguous questions testing key concepts.
3.  **Answer Design**: For each question, provide four answers: one that is correct, and three plausible but incorrect distractors.

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
        else:
            system_prompt = """
You are a professional educator and assessment designer. Your role is to create a fair and challenging exam.
- **Strict Anti-Hallucination Rule**: You must create all questions, correct answers, and incorrect distractors using *only* the provided Source Material. Never invent or use external information.
- **Format Compliance**: Your output must be a single, valid JSON object conforming perfectly to the requested schema.
- **Language**: Use the same language as the user's command.
- **Quantity**: Fulfill the exact number of questions requested in the command. If the material is insufficient, create as many as possible.
"""
            user_prompt = f"""
**Primary Command:** "{query}"

**Source Material (Context):**
---
{context}
---

**Your Task:**
Execute the Primary Command by designing an exam. All elements of the exam must be derived *exclusively* from the Source Material.

**Detailed Requirements:**
1.  **Exam Metadata**: Generate a `topic` and `description` that accurately summarize the Source Material.
2.  **Question Design**: Create clear, unambiguous questions testing key concepts from the text.
3.  **Answer Design**: For each question, provide four answers: one that is verifiably correct from the text, and three plausible but incorrect distractors also based on the text.

**Required JSON Output Format:**
{{
  "topic": "Exam Topic Derived from Source Material",
  "description": "A concise description of the exam's content.",
  "num_of_questions": <integer>,
  "questions": [
    {{
      "question": "A specific question based *only* on the source material.",
      "answers": [
        {{"text": "A plausible but incorrect answer (distractor).", "is_correct": false}},
        {{"text": "The single correct answer, directly from the source material.", "is_correct": true}},
        {{"text": "Another plausible but incorrect answer.", "is_correct": false}},
        {{"text": "A third plausible but incorrect answer.", "is_correct": false}}
      ]
    }}
  ]
}}
"""
        return system_prompt, user_prompt

    async def _run(self, input_str: str) -> str:
        try:
            # Inicjalizuj klienta Redis
            redis_client = await init_redis()

            input_data = json.loads(input_str)
            context = input_data.get('description', '').strip()
            query = input_data.get('query', '').strip()
            use_general_knowledge = input_data.get('use_general_knowledge', False)

            cache_key = f"exam:{self.user_id}:{hash(query + context)}"
            if cached_result := await redis_client.get(cache_key):
                print(f"[DEBUG] ExamGenerator found cached result, length: {len(cached_result.decode())}")
                return cached_result.decode()

            if not use_general_knowledge and not context:
                return json.dumps({
                    "error": "Cannot generate an exam without context. Please ask a question about your files or the web first."
                }, ensure_ascii=False)

            system_prompt, user_prompt = await self._get_prompts(context, query, use_general_knowledge)
            messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
            response = await self._model.ainvoke(messages)
            parsed_response = self._output_parser.parse(response.content)

            if not parsed_response.get('questions'):
                return json.dumps({
                    "error": "I could not find enough information in the provided text to generate an exam for your query."
                }, ensure_ascii=False)

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
                raise
            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error in ExamGenerator: {e}")
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
