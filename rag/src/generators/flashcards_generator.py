from typing import List, Dict
from langchain_anthropic import ChatAnthropic
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.messages import SystemMessage
from langchain_core.prompts import HumanMessagePromptTemplate
import os

class LanguageFlashcardGenerator:
    def __init__(self):
        self.model = ChatAnthropic(model_name="claude-3-haiku-20240307", )
        self.search = TavilySearchResults(max_results=3)

        # Define the prompt template for flashcard generation
        self.flashcard_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="RETURN ONLY IN JSON FORMAT WITHOUT ADDITIONAL TEXT"),
            HumanMessagePromptTemplate.from_template("""
                Generate the number of flashcards provided in description about {topic} based on the following description:
                {description}
                In case when the language is in this list: {{
                    "japanese": "romaji",
                    "chinese": "pinyin",
                    "korean": "romanization",
                    "russian": "transliteration",
                    "arabic": "transliteration",
                    "thai": "transliteration",
                    "hindi": "transliteration"
                }}
                add the provided romanization/transliteration to answer.
                
                Return the flashcards in this exact JSON format:
                [
                    {{
                        "question": "string", (original word, with added romanization/transliteration if applicable)
                        "answer": "string" (translated word)
                    }},
                    {{
                        "question": "string", (original word, with added romanization/transliteration if applicable)
                        "answer": "string" (translated word)
                    }},   
                    {{etc...}}            
                ]
                """)
            ]
        )

        self.output_parser = JsonOutputParser()

    def generate_flashcards(self, request: Dict) -> List[Dict]:
        """
        Generate flashcards based on the input request.

        Args:
            request: Dictionary containing:
                - description: str
                - topic: str

        Returns:
            List of flashcard dictionaries
        """
        # Search for relevant information if needed
        search_results = self.search.invoke(
            f"Information about {request['topic']} {request['description']}"
        )

        # Prepare the generation prompt with context
        prompt_with_context = self.flashcard_prompt | self.model | self.output_parser

        # Generate flashcards
        response = prompt_with_context.invoke({
            "description": request["description"],
            "topic": request["topic"]
        })

        return response


def main():
    # Example usage
    generator = LanguageFlashcardGenerator()

    request = {
        "description": "Proszę stwórz dla mnie fiszki do nauki hiragany, zawierające wszystkie znaki. Chciałbym aby pytaniem był znaczek hiragany z romaji a odpowiedzią znak w alfabecie normalnym.",
        "topic": "Japanese language basics"
    }

    try:
        flashcards = generator.generate_flashcards(request)
        print(flashcards)
        print("Generated Flashcards:")
        for flashcard in flashcards:
            print(f"Question: {flashcard['question']}")
            print(f"Answer: {flashcard['answer']}")
    except Exception as e:
        print(f"Error generating flashcards: {str(e)}")


if __name__ == "__main__":
    main()