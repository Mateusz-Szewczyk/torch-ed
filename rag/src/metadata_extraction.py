import json
import logging
from typing import Dict
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.messages import SystemMessage
from langchain_core.prompts import HumanMessagePromptTemplate
import os

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class MetadataExtractor:
    def __init__(self):
        # Initialize the Anthropic model
        self.model = ChatAnthropic(model_name="claude-3-haiku-20240307")

        # Define the prompt template
        self.prompt_template = ChatPromptTemplate.from_messages([
            SystemMessage(content="RETURN ONLY IN JSON FORMAT WITHOUT ADDITIONAL TEXT"),
            HumanMessagePromptTemplate.from_template("""
                Extract metadata from the following text. The text will be related to category:  {category}
                Focus on:
                - Names of people (MAKE SURE TO RETURN REAL NAMES!!!)(if any).
                - Locations (MAKE SURE TO RETURN REAL LOCATIONS!!!)(if any).
                - Dates or time periods (MAKE SURE TO RETURN REAL TIMES AND DATES!!!)(if any).
                - Key concepts or terms  (MAKE SURE TO RETURN REAL KEY CONCEPTS!! (There is an example list of concepts (you don't need to use them this is just an example): 
                "Calculus", "Probability", "Algebra", "Linear Algebra", "Geometry", "Topology", "Number Theory", "Set Theory", "Differential Equations", "Game Theory", "Quantum Mechanics", 
                "Evolution", "Entropy", "Relativity", "The Scientific Method", "Photosynthesis", "Plate Tectonics", "Newton's Laws", "DNA Replication", "The Big Bang Theory", 
                "Cognitive Dissonance", "Classical Conditioning", "Operant Conditioning", "Attachment Theory", "Maslow's Hierarchy of Needs", "Heuristics", "Confirmation Bias", 
                "Social Learning Theory", "The Unconscious Mind", "Neuroplasticity"))(if any).

                Provide the output in this exact JSON format:
                {{
                    "names": ["Name1", "Name2"],
                    "locations": ["Location1", "Location2"],
                    "dates": ["Date1", "Date2"],
                    "key_terms": ["Term1", "Term2"]
                }}

                Text:
                {text}
                """)
        ])

        self.output_parser = JsonOutputParser()

    def extract_metadata(self, chunk: str, category: str) -> Dict:
        """
        Extracts metadata from a text chunk using Anthropic's Claude model.

        Args:
            chunk (str): The text chunk to extract metadata from.
            category (str): The category of the text.

        Returns:
            dict: Extracted metadata in JSON format.
        """
        # Prepare the prompt with context
        prompt_with_context = self.prompt_template | self.model | self.output_parser

        try:
            # Generate metadata
            response = prompt_with_context.invoke({
                "text": chunk,
                "category": category
            })

            # Log the generated metadata
            logger.info("Metadata extraction successful.")
            logger.debug(f"Extracted Metadata: {response}")

            return response

        except Exception as e:
            logger.error(f"Error during metadata extraction: {str(e)}", exc_info=True)
            # Return an empty response in case of failure
            return {
                "names": [],
                "locations": [],
                "dates": [],
                "key_terms": []
            }
