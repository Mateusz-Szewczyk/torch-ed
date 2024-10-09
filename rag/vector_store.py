# vector_store.py
import os
import warnings
from langchain_chroma import Chroma
from langchain_community.embeddings import GPT4AllEmbeddings

# Optional: Suppress specific warnings
warnings.filterwarnings(
    "ignore",
    message="You may be able to resolve this warning by setting `model_config['protected_namespaces'] = ()`."
)


# Create a vector store with ChromaDB and GPT4All embeddings
def create_vector_store(persist_directory="./chroma_langchain_db", collection_name="text_collection"):
    # Configure GPT4AllEmbeddings for CPU
    embedding_function = GPT4AllEmbeddings(
        model="ggml-gpt4all-j-v1.3-groovy",  # Replace with a CPU-compatible model if necessary
        n_threads=4,  # Adjust based on your CPU cores
    )

    vector_store = Chroma(
        collection_name=collection_name,
        embedding_function=embedding_function,
        persist_directory=persist_directory
    )
    return vector_store


# Perform similarity search on the vector store
def similarity_search(vector_store, query, k=5):
    similar_docs = vector_store.similarity_search(query, k=k)
    return similar_docs


# Load the vector store from the persistent directory
def load_vector_store(persist_directory="./chroma_langchain_db", collection_name="text_collection"):
    if not os.path.exists(persist_directory):
        raise FileNotFoundError(
            f"Directory {persist_directory} not found! You must add documents first."
        )
    return create_vector_store(persist_directory, collection_name)


# Function to add Markdown files to the vector store
def add_markdown_files_to_vector_store(vector_store, markdown_dir='ocr_output_pix2text'):
    """
    Crawls the specified directory to find all Markdown files and adds their content to the vector store.

    Args:
        vector_store (Chroma): The Chroma vector store instance.
        markdown_dir (str): The directory to crawl for Markdown files.
    """
    if not os.path.isdir(markdown_dir):
        raise NotADirectoryError(f"The directory {markdown_dir} does not exist.")

    markdown_files = []
    # Walk through the directory to find all .md files
    for root, dirs, files in os.walk(markdown_dir):
        for file in files:
            if file.endswith('.md'):
                filepath = os.path.join(root, file)
                markdown_files.append(filepath)

    if not markdown_files:
        print(f"No Markdown files found in directory {markdown_dir}.")
        return

    documents = []
    metadata = []

    # Read the content of each Markdown file
    for filepath in markdown_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                documents.append(content)
                # Optional: Add metadata such as the file path
                metadata.append({"source": filepath})
        except Exception as e:
            print(f"Failed to read {filepath}: {e}")

    if documents:
        # Add documents to the vector store with optional metadata
        vector_store.add_texts(texts=documents, metadatas=metadata)
        # No need to call vector_store.persist() as Chroma handles persistence automatically
        print(f"Added {len(documents)} Markdown documents to the vector store.")
    else:
        print("No Markdown documents were added to the vector store.")


# New Function: Add Text Files to the Vector Store
def add_text_files_to_vector_store(vector_store, text_dir='text_files'):
    """
    Crawls the specified directory to find all text files and adds their content to the vector store.

    Args:
        vector_store (Chroma): The Chroma vector store instance.
        text_dir (str): The directory to crawl for text files.
    """
    if not os.path.isdir(text_dir):
        raise NotADirectoryError(f"The directory {text_dir} does not exist.")

    text_files = []
    # Walk through the directory to find all .txt files
    for root, dirs, files in os.walk(text_dir):
        for file in files:
            if file.endswith('.txt'):
                filepath = os.path.join(root, file)
                text_files.append(filepath)

    if not text_files:
        print(f"No text files found in directory {text_dir}.")
        return

    documents = []
    metadata = []

    # Read the content of each text file
    for filepath in text_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                documents.append(content)
                # Optional: Add metadata such as the file path
                metadata.append({"source": filepath})
        except Exception as e:
            print(f"Failed to read {filepath}: {e}")

    if documents:
        # Add documents to the vector store with optional metadata
        vector_store.add_texts(texts=documents, metadatas=metadata)
        # No need to call vector_store.persist() as Chroma handles persistence automatically
        print(f"Added {len(documents)} text documents to the vector store.")
    else:
        print("No text documents were added to the vector store.")


# Example usage
if __name__ == "__main__":
    # Define parameters
    persist_dir = "./chroma_langchain_db"
    collection = "text_collection"
    markdown_directory = "ocr_output_pix2text"  # Directory containing Markdown files
    text_directory = "text_files"  # Directory containing text files

    # Create or load the vector store
    if os.path.exists(persist_dir):
        vector_store = load_vector_store(persist_directory=persist_dir, collection_name=collection)
        print("Loaded existing vector store.")
    else:
        vector_store = create_vector_store(persist_directory=persist_dir, collection_name=collection)
        print("Created new vector store.")

    # Add Markdown files to the vector store
    add_markdown_files_to_vector_store(vector_store, markdown_dir=markdown_directory)

    # Add text files to the vector store
    add_text_files_to_vector_store(vector_store, text_dir=text_directory)

    # Example similarity search
    query = "Your search query here"
    results = similarity_search(vector_store, query, k=5)
    for idx, doc in enumerate(results):
        print(f"Result {idx + 1}:")
        print(f"Content: {doc.page_content}")
        print(f"Metadata: {doc.metadata}")
        print("-" * 40)
