import os
import json
import logging
import requests
import subprocess
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import re
from functools import lru_cache
import time

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s:%(name)s:%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def run_shell_command(command, timeout=300):
    """
    Executes a shell command and returns the output.
    """
    logger.debug(f"Executing command: {' '.join(command)}")
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=True  # This will raise CalledProcessError if return code is non-zero
        )
        logger.debug(f"Command output: {result.stdout.strip()}")
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out after {timeout} seconds")
        raise
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with error: {e.stderr.strip()}")
        raise


@lru_cache(maxsize=128)
def is_model_available(model_name):
    """
    Checks if the specified Ollama model is available locally.
    """
    try:
        output = run_shell_command(['ollama', 'list'])
        available_models = [line.split()[0] for line in output.split('\n') if line.strip()]
        logger.debug(f"Available models: {available_models}")
        return model_name in available_models
    except Exception as e:
        logger.error(f"Error checking model availability: {e}")
        return False


def pull_model(model_name, max_retries=3, initial_timeout=600):
    """
    Pulls the specified Ollama model with retry logic.
    """
    for attempt in range(max_retries):
        try:
            timeout = initial_timeout * (attempt + 1)  # Increase timeout with each retry
            logger.info(f"Pulling model {model_name} (attempt {attempt + 1}/{max_retries})")
            run_shell_command(['ollama', 'pull', model_name], timeout=timeout)
            # Verify the model is now in the list
            if is_model_available(model_name):
                logger.info(f"Successfully pulled and verified model: {model_name}")
                return True
            else:
                logger.warning(f"Model pulled but not found in list, may need to retry")
                time.sleep(2)  # Give some time for the model to be registered
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff

    logger.error(f"Failed to pull model after {max_retries} attempts")
    return False


def ensure_model_available(model_name):
    """
    Ensures the specified model is available, with enhanced verification.
    """
    try:
        # First verify Ollama is running
        run_shell_command(['ollama', 'list'])
    except FileNotFoundError:
        raise RuntimeError("Ollama is not installed or not in PATH")
    except subprocess.CalledProcessError:
        raise RuntimeError("Ollama service is not running")

    # Clear the cache to ensure fresh check
    is_model_available.cache_clear()

    # Check if model exists locally
    if not is_model_available(model_name):
        logger.warning(f"Model '{model_name}' not found locally. Attempting to pull...")
        if not pull_model(model_name):
            raise RuntimeError(f"Failed to pull model '{model_name}'")

        # Double-check model availability after pulling
        is_model_available.cache_clear()  # Clear cache again
        if not is_model_available(model_name):
            raise RuntimeError(f"Model '{model_name}' still not available after pulling")
    else:
        logger.debug(f"Model '{model_name}' is available locally")


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
    api_url = os.getenv('OLLAMA_API_URL', 'http://localhost:11434/api/generate')  # Default URL
    model_name = os.getenv('OLLAMA_MODEL_NAME', 'llama3.2:3b-instruct-fp16')  # Default model

    # Validate essential configurations
    if not api_url:
        logger.error("OLLAMA_API_URL environment variable not set.")
        raise EnvironmentError("OLLAMA_API_URL environment variable not set.")

    logger.debug(f"Using API URL: {api_url}")
    logger.debug(f"Using Model Name: {model_name}")

    # Ensure the model is available
    try:
        ensure_model_available(model_name)
    except Exception as e:
        logger.error(f"Model availability check failed: {e}")
        return {
            "names": [],
            "locations": [],
            "dates": [],
            "key_terms": []
        }

    # Construct headers
    headers = {'Content-Type': 'application/json'}

    # Craft the prompt
    prompt = f"""
    Extract the following metadata from the provided text:

    1. Names of people (MAKE SURE TO RETURN REAL NAMES!!!)(if any).
    2. Locations mentioned (MAKE SURE TO RETURN REAL LOCATIONS!!!)(if any).
    3. Dates or time periods (MAKE SURE TO RETURN REAL DATES!!!)(if any).
    4. Important concepts or key terms (MAKE SURE TO RETURN REAL KEY CONCEPTS!! (There is an example list of concepts (you don't need to use them this is just an example): 
    "Calculus", "Probability", "Algebra", "Linear Algebra", "Geometry", "Topology", "Number Theory", "Set Theory", "Differential Equations", "Game Theory", "Quantum Mechanics", 
    "Evolution", "Entropy", "Relativity", "The Scientific Method", "Photosynthesis", "Plate Tectonics", "Newton's Laws", "DNA Replication", "The Big Bang Theory", 
    "Cognitive Dissonance", "Classical Conditioning", "Operant Conditioning", "Attachment Theory", "Maslow's Hierarchy of Needs", "Heuristics", "Confirmation Bias", 
    "Social Learning Theory", "The Unconscious Mind", "Neuroplasticity"))(if any).

    Category: {category}

    Text:
    {chunk}

    Return the metadata in the following JSON format only, without any additional text or explanations:

    {{
        "names": [ "Name1", "Name2" ],
        "locations": [ "Location1", "Location2" ],
        "dates": [ "Date1", "Date2" ],
        "key_terms": [ "Term1", "Term2" ]
    }}
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
        total=3,  # Total number of retries
        backoff_factor=0.3,  # Wait between retries: {backoff factor} * (2 ** (retry number - 1))
        status_forcelist=[429, 500, 502, 503, 504],  # HTTP status codes to retry on
        allowed_methods=["POST"]  # HTTP methods to retry
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    try:
        # Log the prompt (truncate if too long)
        logger.debug(f"Sending prompt to Ollama: {prompt[:200]}...")

        # Make the POST request to Ollama
        response = session.post(api_url, json=payload, headers=headers, timeout=60)  # Increased timeout if necessary
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Log the entire response
        logger.info(f"Full response from Ollama: {response.text}")

        # Extract content
        output = response.json()
        logger.debug(f"Parsed JSON response: {output}")
        print(f"Parsed JSON response: {output}")
        # Extract metadata_str based on response structure
        metadata_str = ''
        if 'message' in output and 'content' in output['message']:
            metadata_str = output['message']['content']
        elif 'choices' in output and len(output['choices']) > 0 and 'text' in output['choices'][0]:
            metadata_str = output['choices'][0]['text']
        else:
            logger.warning("Unexpected response structure from Ollama.")
            metadata_str = ''

        logger.debug(f"Extracted metadata string: {metadata_str}")

        if not metadata_str:
            logger.warning("Received empty metadata response from Ollama.")
            return {
                "names": [],
                "locations": [],
                "dates": [],
                "key_terms": []
            }

        # Clean the metadata string to ensure it's valid JSON
        metadata_str = metadata_str.strip()

        # Optionally, remove any extraneous text before and after JSON using regex
        json_match = re.search(r'\{.*\}', metadata_str, re.DOTALL)
        if json_match:
            metadata_str = json_match.group(0)
        else:
            logger.warning("No valid JSON found in the metadata response.")
            return {
                "names": [],
                "locations": [],
                "dates": [],
                "key_terms": []
            }

        logger.debug(f"Cleaned metadata string: {metadata_str}")

        # Parse JSON
        try:
            metadata = json.loads(metadata_str)
            logger.info("Successfully extracted metadata using Ollama.")
            logger.debug(f"Extracted Metadata: {metadata}")
            return metadata
        except json.JSONDecodeError as json_err:
            logger.error(f"JSON decode error: {json_err}. Received data: {metadata_str}", exc_info=True)
            return {
                "names": [],
                "locations": [],
                "dates": [],
                "key_terms": []
            }

    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error occurred while connecting to Ollama: {http_err}", exc_info=True)
    except requests.exceptions.ConnectionError as conn_err:
        logger.error(f"Connection error occurred while connecting to Ollama: {conn_err}", exc_info=True)
    except requests.exceptions.Timeout as timeout_err:
        logger.error(f"Timeout error occurred while connecting to Ollama: {timeout_err}", exc_info=True)
    except requests.exceptions.RequestException as req_err:
        logger.error(f"Request exception occurred while connecting to Ollama: {req_err}", exc_info=True)
    except json.JSONDecodeError as json_err:
        logger.error(f"JSON decode error: {json_err}. Received data: {response.text}", exc_info=True)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)

    # In case of any errors, return empty metadata
    return {
        "names": [],
        "locations": [],
        "dates": [],
        "key_terms": []
    }

