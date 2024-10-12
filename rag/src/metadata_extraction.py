import json
import ollama


def extract_metadata_using_llm(chunk, category):
    """
    Extracts metadata from a text chunk using a language model.

    Args:
        chunk (str): The text chunk to extract metadata from.
        category (str): The category of the text.

    Returns:
        dict: A dictionary containing extracted metadata.
    """
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

    model_name = "llama3.2:3b-instruct-fp16"
    output = ollama.chat(
        model=model_name,
        messages=[
            {'role': 'system', 'content': 'You are a smart assistant tasked with extracting metadata from a text.'},
            {'role': 'user', 'content': prompt}
        ],
        format='json',
        stream=False
    )

    metadata_str = output['message']['content']
    try:
        metadata = json.loads(metadata_str)
    except json.JSONDecodeError as e:
        print("Błąd dekodowania JSON:", e)
        print("Otrzymany metadata_str:", metadata_str)
        # Możesz zdecydować, co zrobić w przypadku błędu - np. pominąć ten fragment
        metadata = {
            "names": [],
            "locations": [],
            "dates": [],
            "key_terms": []
        }
    return metadata
