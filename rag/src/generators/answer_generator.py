# answer_generator.py

"""
Answer Generator Module
=======================
This module provides functions to generate answers to user queries using retrieved chunks and the Ollama Llama model.

Functions:
- `generate_answer`: Main function to generate an answer for a given user and query.
- `create_prompt`: Creates a prompt for the Llama model.
- `generate_answer_with_ollama`: Generates an answer using the Ollama Llama model via direct HTTP requests.
"""

import os
import json
import logging
from typing import List
from sentence_transformers import SentenceTransformer
from ..search_engine import search_and_rerank
import requests  # Replacing ollama library with requests for direct HTTP communication
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Set to DEBUG for more detailed logs

# You can add handlers if needed, for example:
# handler = logging.StreamHandler()
# formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# handler.setFormatter(formatter)
# logger.addHandler(handler)

# Initialize the embedding model once at module level for performance
EMBEDDING_MODEL_NAME = os.getenv('EMBEDDING_MODEL_NAME', 'all-MiniLM-L6-v2')
try:
    embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    logger.info(f"Initialized embedding model: {EMBEDDING_MODEL_NAME}")
except Exception as e:
    logger.error(f"Failed to initialize embedding model '{EMBEDDING_MODEL_NAME}': {e}")
    raise

def generate_answer(user_id: str, query: str) -> str:
    """
    Generates an answer based on retrieved chunks for the given user and query using Ollama's Llama model.

    Args:
        user_id (str): The ID of the user.
        query (str): The user's query.

    Returns:
        str: Generated answer.
    """
    logger.info(f"Generating answer for user_id: {user_id} with query: '{query}'")

    # Retrieve relevant chunks for the user
    try:
        results = search_and_rerank(query, embedding_model, user_id, n_results=5)
    except Exception as e:
        logger.error(f"Error during search and rerank for user_id: {user_id}, query: '{query}': {e}", exc_info=True)
        return "An error occurred while retrieving information."

    if not results:
        logger.warning(f"No relevant information found for user_id: {user_id} with query: '{query}'")
        return "No relevant information found."

    # Extract the content from the results
    chunks = [result.get('content', '') for result in results]
    logger.info(f"Retrieved {len(chunks)} chunks for user_id: {user_id}")

    # Create the prompt for the Llama model
    try:
        prompt = create_prompt(query, chunks)
        logger.debug(f"Generated prompt: {prompt}")
    except Exception as e:
        logger.error(f"Error creating prompt for user_id: {user_id}, query: '{query}': {e}", exc_info=True)
        return "An error occurred while generating the prompt."

    # Generate the answer using the Llama model via Ollama
    try:
        answer = generate_answer_with_ollama(prompt)
        logger.info(f"Generated answer for user_id: {user_id}")
    except Exception as e:
        logger.error(f"Error generating answer for user_id: {user_id}: {e}", exc_info=True)
        return "An error occurred while generating the answer."

    return answer

def create_prompt(query: str, chunks: List[str]) -> str:
    """
    Creates a prompt for the Llama model using the query and retrieved chunks.

    Args:
        query (str): The user's query.
        chunks (List[str]): List of relevant text chunks.

    Returns:
        str: The prompt to be sent to the Llama model.
    """
    # Combine the chunks into a context
    context = "\n\n".join(chunks)

    # Create the prompt with instructions
    prompt = f"""You are an AI assistant that provides helpful and accurate answers to the user's questions based on the provided context.

Context:
{context}

Question:
{query}

Answer:"""

    return prompt

def generate_answer_with_ollama(prompt: str) -> str:
    """
    Generates an answer using the Llama model via the Ollama service.

    Args:
        prompt (str): The prompt to send to the model.

    Returns:
        str: The generated answer.

    Raises:
        Exception: If communication with Ollama fails or invalid responses are received.
    """
    # Configuration via environment variables
    OLLAMA_API_URL = os.getenv('OLLAMA_API_URL', 'http://localhost:11434/api/generate')
    OLLAMA_MODEL_NAME = os.getenv('OLLAMA_MODEL_NAME', "llama2:13b")

    if not OLLAMA_API_URL:
        logger.error("OLLAMA_API_URL environment variable not set.")
        raise EnvironmentError("OLLAMA_API_URL environment variable not set.")

    headers = {'Content-Type': 'application/json'}

    payload = {
        'model': OLLAMA_MODEL_NAME,
        'prompt': prompt
    }

    # Set up a session with retries
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=0.3,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    try:
        logger.debug(f"Sending request to Ollama: {OLLAMA_API_URL}")
        response = session.post(OLLAMA_API_URL, json=payload, headers=headers, timeout=60)
        response.raise_for_status()

        # Read the response line by line
        answer_parts = []
        for line in response.text.strip().split('\n'):
            if line:
                try:
                    data = json.loads(line)
                    content = data.get('response', '')
                    if content:
                        answer_parts.append(content)
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error on line: {line} Error: {e}")
                    continue  # Skip lines that can't be parsed

        answer = ''.join(answer_parts).strip()

        if not answer:
            logger.warning("Received empty answer from Ollama.")
            return "I'm sorry, I couldn't generate an answer at this time."

        logger.debug(f"Received answer from Ollama: {answer}")
        return answer

    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error occurred while communicating with Ollama: {http_err}", exc_info=True)
        raise Exception(f"HTTP error occurred: {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        logger.error(f"Connection error occurred while communicating with Ollama: {conn_err}", exc_info=True)
        raise Exception(f"Connection error occurred: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        logger.error(f"Timeout error occurred while communicating with Ollama: {timeout_err}", exc_info=True)
        raise Exception(f"Timeout error occurred: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        logger.error(f"Request exception occurred while communicating with Ollama: {req_err}. Response text: {response.text}", exc_info=True)
        raise Exception(f"An error occurred: {req_err}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while communicating with Ollama: {e}", exc_info=True)
        raise Exception(f"An unexpected error occurred: {e}")


