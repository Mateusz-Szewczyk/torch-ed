# main.py
import os
from document_processor import read_text_file, split_text_into_documents, add_documents_to_vector_store
from vector_store import create_vector_store, load_vector_store, similarity_search
from langchain_community.embeddings import GPT4AllEmbeddings
import subprocess

embedding = GPT4AllEmbeddings(model_kwargs={"n_threads": 4})


def run_ollama(model_name, prompt):
    command = ['ollama', 'run', model_name]
    print(f"Running Ollama with model: {model_name} and prompt: {prompt}")

    try:
        result = subprocess.run(command, input=prompt, capture_output=True, text=True, check=True, encoding='utf-8')
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running Ollama: {e}")
        print(f"Standard Output: {e.stdout}")
        print(f"Standard Error: {e.stderr}")
        return ""

def main():
    filename = "python_docs_index.txt"

    if not os.path.exists(filename):
        print(f"File {filename} not found!")
        return

    text = read_text_file(filename)
    documents = split_text_into_documents(text)

    persist_directory = "./chroma_langchain_db_new"

    if not os.path.exists(persist_directory):
        vector_store = create_vector_store(persist_directory=persist_directory)
        add_documents_to_vector_store(vector_store, documents)
    else:
        vector_store = load_vector_store(persist_directory=persist_directory)

    model_name = "llama3.2:3b-instruct-fp16"

    query = "Jak tworzyć oprogramowanie wysokiej jakości?"

    similar_docs = similarity_search(vector_store, query, k=4)
    retrieved_text = "\n\n".join([doc.page_content for doc in similar_docs])
    combined_prompt = f"""
    You are an AI assistant with advanced analytical and communication skills. Your task is to provide accurate, insightful, and tailored responses based on the given information and query.

    Context:
    {retrieved_text}

    Query: {query}

    Response Guidelines:
    1. Analyze: Thoroughly examine the provided context, identifying key concepts, relationships, and relevant details.

    2. Synthesize: Combine insights from multiple sources to form a comprehensive understanding.

    3. Answer: 
       - Begin with a direct, concise answer to the query.
       - Elaborate with supporting details, examples, or explanations as needed.
       - If applicable, present multiple perspectives or interpretations.

    4. Clarity:
       - Use clear, jargon-free language unless technical terms are necessary.
       - Employ bullet points, numbered lists, or short paragraphs for easy readability.

    5. Credibility:
       - Seamlessly incorporate references to the provided context when relevant.
       - Clearly distinguish between information from the context and any inferences or general knowledge you're using.

    6. Completeness:
       - Address all aspects of the query.
       - If the context lacks sufficient information, clearly state this and provide the best possible answer with available data.

    7. Objectivity:
       - Present information impartially, especially for controversial topics.
       - Acknowledge limitations or uncertainties in the data or conclusions.

    8. Engagement:
       - Tailor your tone to suit the nature of the query (e.g., formal for academic questions, conversational for general inquiries).
       - When appropriate, pose thought-provoking questions or suggest areas for further exploration.

    Remember: Start your response directly and avoid repetitive or formulaic introductions. Your goal is to provide a helpful, informative, and engaging answer that directly addresses the user's needs.
    """

    # Run the LLaMA 3.2 3B model via Ollama
    response = run_ollama(model_name, combined_prompt)

    # Step 6: Output the final response
    print(f"Generated Response:\n{response}")

if __name__ == "__main__":
    main()


#TODO Przeczytaj o LoRA i Flexora zeby troche finetuningowac model w razie potrzeby