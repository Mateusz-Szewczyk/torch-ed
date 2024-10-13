# answer_generator.py

"""
Answer Generator Module
=======================

This module provides functions to generate answers to user queries using retrieved chunks and the Ollama Llama model.

Functions:
- `generate_answer`: Main function to generate an answer for a given user and query.
- `create_prompt`: Creates a prompt for the Llama model.
- `generate_answer_with_ollama`: Generates an answer using the Ollama Llama model.
"""

from typing import List
from sentence_transformers import SentenceTransformer
from .search_engine import search_and_rerank
import ollama

def generate_answer(user_id: str, query: str) -> str:
    """
    Generates an answer based on retrieved chunks for the given user and query using Ollama's Llama model.

    Args:
        user_id (str): The ID of the user.
        query (str): The user's query.

    Returns:
        str: Generated answer.
    """
    # Initialize the embedding model
    print("tutaj dziala")
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    print("czy tutaj działa??")
    # Retrieve relevant chunks for the user
    results = search_and_rerank(query, embedding_model, user_id, n_results=5)
    print("a czy tutaj działa???")
    print(results)
    if not results:
        return "No relevant information found."

    # Extract the content from the results
    chunks = [result.get('content', '') for result in results]

    # Create the prompt for the Llama model
    prompt = create_prompt(query, chunks)

    # Generate the answer using the Llama model via Ollama
    answer = generate_answer_with_ollama(prompt)

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
    prompt = f"""You are an AI assistant that provides helpful answers to the user's questions based on the provided context.

                Context:
                {context}
                
                Question:
                {query}
                
                Answer:"""

    return prompt

def generate_answer_with_ollama(prompt: str) -> str:
    """
    Generates an answer using the Llama model via Ollama.

    Args:
        prompt (str): The prompt to send to the model.

    Returns:
        str: The generated answer.
    """
    # Define the model to use
    model = "llama3.2:3b-instruct-fp16"

    try:
        answer = ollama.chat(model=model, messages=[
            {"role": "system",
             "content": "You are an AI assistant that provides helpful answers to the user's questions.",},
            {"role": "assistant",
             "content": prompt},],
                             stream=True)
        return answer["content"]

    except Exception as e:
        return f"Error communicating with Ollama: {str(e)}"
