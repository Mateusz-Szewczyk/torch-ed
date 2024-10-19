import os
import json
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Adjust as needed (DEBUG, WARNING, ERROR)


# You can add handlers here if needed, for example:
# handler = logging.StreamHandler()
# formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# handler.setFormatter(formatter)
# logger.addHandler(handler)

def extract_metadata_using_llm(chunk, category):
    """
    Extracts metadata from a text chunk using the Ollama LLM service.

    Args:
        chunk (str): The text chunk to extract metadata from.
        category (str): The category of the text.

    Returns:
        dict: A dictionary containing extracted metadata.
    """
    # Configuration via environment variables
    api_url = os.getenv('OLLAMA_API_URL', 'http://localhost:11434/extract')  # Default URL
    model_name = os.getenv('OLLAMA_MODEL_NAME', 'llama3.2:3b-instruct-fp16')  # Default model
    api_key = os.getenv('OLLAMA_API_KEY')  # Optional API key

    # Validate essential configurations
    if not api_url:
        logger.error("OLLAMA_API_URL environment variable not set.")
        raise EnvironmentError("OLLAMA_API_URL environment variable not set.")

    # Construct headers
    headers = {'Content-Type': 'application/json'}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'

    # Craft the prompt
    prompt = f"""
    Given the following text, extract:
    1. Names of people (MAKE SURE TO RETURN REAL NAMES!!!)(if any).
    2. Locations mentioned (MAKE SURE TO RETURN REAL LOCATIONS!!!)(if any).
    3. Dates or time periods (MAKE SURE TO RETURN REAL DATES!!!)(if any).
    4. Important concepts or key terms (MAKE SURE TO RETURN REAL KEY CONCEPTS!! (There is an example list of concepts (you don't need to use them this is just an example): 
    "Calculus", "Probability", "Algebra", "Linear Algebra", "Geometry", "Topology", "Number Theory", "Set Theory", "Differential Equations", "Game Theory", "Quantum Mechanics", 
    "Evolution", "Entropy", "Relativity", "The Scientific Method", "Photosynthesis", "Plate Tectonics", "Newton's Laws", "DNA Replication", "The Big Bang Theory", 
    "Cognitive Dissonance", "Classical Conditioning", "Operant Conditioning", "Attachment Theory", "Maslow's Hierarchy of Needs", "Heuristics", "Confirmation Bias", 
    "Social Learning Theory", "The Unconscious Mind", "Neuroplasticity"))(if any).

    The text is in category: {category}
    Text: {chunk}
    Provide the metadata in this format:
    {{
        "names": [list of names],
        "locations": [list of locations],
        "dates": [list of dates],
        "key_terms": [list of important concepts or key terms]
    }}

    Be sure to include **only** validated formatted JSON with no additional comments or text.    
    """

    # Prepare the payload
    payload = {
        'model': model_name,
        'messages': [
            {'role': 'system', 'content': 'You are a smart assistant tasked with extracting metadata from a text.'},
            {'role': 'user', 'content': prompt}
        ],
        'format': 'json',
        'stream': False
    }

    # Set up a session with retries
    session = requests.Session()
    retry_strategy = Retry(
        total=3,  # Number of total retries
        backoff_factor=0.3,  # Wait between retries: {backoff factor} * (2 ** (retry number - 1))
        status_forcelist=[429, 500, 502, 503, 504],  # HTTP status codes to retry on
        method_whitelist=["POST"]  # HTTP methods to retry
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    try:
        # Make the POST request to Ollama
        response = session.post(api_url, json=payload, headers=headers, timeout=20)  # Increased timeout if necessary
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Extract content
        output = response.json()

        # Assuming the response structure contains 'message' and 'content'
        metadata_str = output.get('message', {}).get('content', '')

        if not metadata_str:
            logger.warning("Received empty metadata response from Ollama.")
            return {
                "names": [],
                "locations": [],
                "dates": [],
                "key_terms": []
            }

        # Parse JSON
        metadata = json.loads(metadata_str)
        logger.info("Successfully extracted metadata using Ollama.")
        return metadata

    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error occurred while connecting to Ollama: {http_err}", exc_info=True)
    except requests.exceptions.ConnectionError as conn_err:
        logger.error(f"Connection error occurred while connecting to Ollama: {conn_err}", exc_info=True)
    except requests.exceptions.Timeout as timeout_err:
        logger.error(f"Timeout error occurred while connecting to Ollama: {timeout_err}", exc_info=True)
    except requests.exceptions.RequestException as req_err:
        logger.error(f"Request exception occurred while connecting to Ollama: {req_err}", exc_info=True)
    except json.JSONDecodeError as json_err:
        logger.error(f"JSON decode error: {json_err}. Received data: {metadata_str}", exc_info=True)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)

    # In case of any errors, return empty metadata
    return {
        "names": [],
        "locations": [],
        "dates": [],
        "key_terms": []
    }
