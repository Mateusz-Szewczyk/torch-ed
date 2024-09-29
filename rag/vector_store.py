# vector_store.py
import os
from langchain_chroma import Chroma
from langchain_community.embeddings import GPT4AllEmbeddings

# Create a vector store with ChromaDB and GPT4All embeddings
def create_vector_store(persist_directory="./chroma_langchain_db", collection_name="text_collection"):
    vector_store = Chroma(
        collection_name=collection_name,
        embedding_function=GPT4AllEmbeddings(),
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
        raise FileNotFoundError(f"Directory {persist_directory} not found! You must add documents first.")
    return create_vector_store(persist_directory, collection_name)
