import os
import logging
from typing import List, Tuple
from sentence_transformers import SentenceTransformer
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage
from langchain_core.prompts import HumanMessagePromptTemplate
from ..search_engine import search_and_rerank

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Set to DEBUG for more detailed logs

# Initialize the embedding model once at module level for performance
EMBEDDING_MODEL_NAME = os.getenv('EMBEDDING_MODEL_NAME', 'all-MiniLM-L6-v2')
try:
    embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    logger.info(f"Initialized embedding model: {EMBEDDING_MODEL_NAME}")
except Exception as e:
    logger.error(f"Failed to initialize embedding model '{EMBEDDING_MODEL_NAME}': {e}")
    raise

# Initialize Anthropic model
try:
    anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
    if not anthropic_api_key:
        raise ValueError("Anthropic API key is not set. Please set the ANTHROPIC_API_KEY environment variable.")
    anthropic_model = ChatAnthropic(
        model_name="claude-3-5-haiku-latest",
        anthropic_api_key=anthropic_api_key
    )
    logger.info("Initialized Anthropic Claude model.")
except Exception as e:
    logger.error(f"Failed to initialize Anthropic model: {e}")
    raise

def generate_answer(user_id: str, query: str, max_iterations: int = 2, max_generated_passages: int = 5) -> str:
    """
    Generates an answer based on the Astute RAG algorithm for the given user and query.

    Args:
        user_id (str): The ID of the user.
        query (str): The user's query.
        max_iterations (int): Number of iterations for knowledge consolidation.
        max_generated_passages (int): Maximum number of passages to generate from internal knowledge.

    Returns:
        str: Generated answer.
    """
    logger.info(f"Generating answer for user_id: {user_id} with query: '{query}'")

    # Step 1: Adaptive Generation of Internal Knowledge
    try:
        internal_passages = generate_internal_passages(query, max_generated_passages)
        logger.info(f"Generated {len(internal_passages)} internal passages.")
    except Exception as e:
        logger.error(f"Error generating internal passages: {e}", exc_info=True)
        internal_passages = []

    # Step 2: Retrieve relevant external chunks for the user
    try:
        results = search_and_rerank(query, embedding_model, user_id, n_results=5)
        external_passages = [result.get('content', '') for result in results]
        logger.info(f"Retrieved {len(external_passages)} external passages for user_id: {user_id}")
    except Exception as e:
        logger.error(f"Error during search and rerank: {e}", exc_info=True)
        external_passages = []

    if not internal_passages and not external_passages:
        logger.warning(f"No relevant information found for user_id: {user_id} with query: '{query}'")
        return "No relevant information found."

    # Step 2 & 3: Combine Internal and External Passages and Assign Sources
    combined_passages = external_passages + internal_passages
    source_indicators = ['external'] * len(external_passages) + ['internal'] * len(internal_passages)

    print(combined_passages)

    # Step 4: Iterative Source-aware Knowledge Consolidation
    consolidated_passages, consolidated_sources = iterative_consolidation(
        query,
        combined_passages,
        source_indicators,
        max_iterations
    )

    # Step 5: Answer Finalization
    answer = finalize_answer(query, consolidated_passages, consolidated_sources)

    logger.info(f"Generated answer for user_id: {user_id}")
    return answer

def generate_internal_passages(query: str, max_generated_passages: int) -> List[str]:
    """
    Generates internal passages from the LLM's internal knowledge based on the query.

    Args:
        query (str): The user's query.
        max_generated_passages (int): Maximum number of passages to generate.

    Returns:
        List[str]: A list of generated internal passages.
    """
    # Prompt template for generating internal passages
    prompt_template = ChatPromptTemplate.from_messages([
        SystemMessage(content="You are a knowledgeable assistant helping to generate relevant information for a query."),
        HumanMessagePromptTemplate.from_template("""
        Based on your internal knowledge, generate up to {max_passages} accurate, relevant, and concise passages that answer the following question. Do not include any hallucinations or fabricated information. If you don't have enough reliable information, generate fewer passages or none.
        
        Question:
        {query}
        
        Passages:
        """)
    ])

    response = prompt_template | anthropic_model

    try:
        output = response.invoke({
            "query": query,
            "max_passages": max_generated_passages
        })

        # Access the content of the AIMessage
        output_text = output.content

        # Split the output into individual passages
        passages = [p.strip() for p in output_text.strip().split('\n\n') if p.strip()]
        print(f"Passages: {passages}")
        return passages

    except Exception as e:
        logger.error(f"Error generating internal passages: {e}", exc_info=True)
        return []

def iterative_consolidation(query: str, passages: List[str], sources: List[str], max_iterations: int) -> Tuple[List[str], List[str]]:
    """
    Iteratively consolidates the knowledge from passages considering their sources.

    Args:
        query (str): The user's query.
        passages (List[str]): List of passages.
        sources (List[str]): Corresponding list of sources ('internal' or 'external').
        max_iterations (int): Number of consolidation iterations.

    Returns:
        Tuple[List[str], List[str]]: Consolidated passages and their sources.
    """
    for iteration in range(max_iterations):
        logger.info(f"Consolidation iteration {iteration + 1}")
        prompt_template = ChatPromptTemplate.from_messages([
            SystemMessage(content="You are an assistant that consolidates information from different sources."),
            HumanMessagePromptTemplate.from_template("""
                Given the following passages and their sources, consolidate the information by identifying consistent details, resolving conflicts, and removing irrelevant content.
                
                Question:
                {query}
                
                Passages and Sources:
                {passages_and_sources}
                
                Consolidated Passages:
                """)
        ])

        # Prepare passages and sources for the prompt
        passages_and_sources = ""
        for passage, source in zip(passages, sources):
            passages_and_sources += f"Source: {source}\nPassage: {passage}\n\n"

        response = prompt_template | anthropic_model

        try:
            output = response.invoke({
                "query": query,
                "passages_and_sources": passages_and_sources
            })

            # Access the content of the AIMessage
            output_text = output.content

            # Parse the consolidated passages and sources from the output
            # Assuming the output is formatted as:
            # "Passage: ... \nSource: ... \n\n"
            new_passages = []
            new_sources = []
            entries = output_text.strip().split('\n\n')
            for entry in entries:
                lines = entry.strip().split('\n')
                passage_text = ''
                source_text = ''
                for line in lines:
                    if line.startswith("Passage:"):
                        passage_text = line[len("Passage:"):].strip()
                    elif line.startswith("Source:"):
                        source_text = line[len("Source:"):].strip()
                if passage_text and source_text:
                    new_passages.append(passage_text)
                    new_sources.append(source_text)
            passages = new_passages
            sources = new_sources

        except Exception as e:
            logger.error(f"Error during consolidation iteration {iteration + 1}: {e}", exc_info=True)
            break  # Exit the loop if consolidation fails
    print(f"Sources: {sources}")
    return passages, sources

def finalize_answer(query: str, passages: List[str], sources: List[str]) -> str:
    """
    Generates the final answer based on the consolidated passages and their sources.

    Args:
        query (str): The user's query.
        passages (List[str]): Consolidated passages.
        sources (List[str]): Corresponding sources.

    Returns:
        str: The final answer.
    """
    prompt_template = ChatPromptTemplate.from_messages([
        SystemMessage(content="You are an AI assistant tasked with generating the most reliable answer based on consolidated information."),
        HumanMessagePromptTemplate.from_template("""
        Based on the following consolidated passages and their sources, generate the most accurate and reliable answer to the question. Consider the reliability of each source, cross-confirmation between sources, and the thoroughness of the information.
        
        Question:
        {query}
        
        Consolidated Passages and Sources:
        {passages_and_sources}
        
        Final Answer:
        """)
    ])

    # Prepare passages and sources for the prompt
    passages_and_sources = ""
    for passage, source in zip(passages, sources):
        passages_and_sources += f"Source: {source}\nPassage: {passage}\n\n"

    response = prompt_template | anthropic_model

    try:
        answer = response.invoke({
            "query": query,
            "passages_and_sources": passages_and_sources
        })
        return answer.content.strip()

    except Exception as e:
        logger.error(f"Error during answer finalization: {e}", exc_info=True)
        return "An error occurred while generating the final answer."
