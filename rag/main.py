# main.py
import os
from document_processor import read_text_file, split_text_into_documents, add_documents_to_vector_store
from vector_store import create_vector_store, load_vector_store, similarity_search
from langchain_community.embeddings import GPT4AllEmbeddings
import subprocess

embedding = GPT4AllEmbeddings()

def rag_query(vector_store, model, query, k=5):
    similar_docs = similarity_search(vector_store, query, k=k)
    relevant_texts = "\n\n".join([doc.page_content for doc in similar_docs])

    prompt = f"Given the following documents:\n{relevant_texts}\n\nAnswer the question: {query}"
    response = model.invoke(prompt)

    return response

import subprocess

def run_ollama(model_name, prompt):
    command = ['ollama', 'run', model_name]
    print(f"Running Ollama with model: {model_name} and prompt: {prompt}")

    try:
        result = subprocess.run(command, input=prompt, capture_output=True, text=True, check=True)
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

    persist_directory = "./chroma_langchain_db"

    if not os.path.exists(persist_directory):
        vector_store = create_vector_store(persist_directory=persist_directory)
        add_documents_to_vector_store(vector_store, documents)
    else:
        vector_store = load_vector_store(persist_directory=persist_directory)

    model_name = "llama3.2:3b-instruct-fp16"

    query = "Co to python?"

    similar_docs = similarity_search(vector_store, query, k=5)
    retrieved_text = "\n\n".join([doc.page_content for doc in similar_docs])
    combined_prompt = f"Relevant Documents:\n{retrieved_text}\n\nAnswer the question: {query}"

    # Run the LLaMA 3.2 3B model via Ollama
    response = run_ollama(model_name, combined_prompt)

    # Step 6: Output the final response
    print(f"Generated Response:\n{response}")

if __name__ == "__main__":
    main()
