# document_processor.py
import os
from langchain_core.documents import Document
from uuid import uuid4

# Load and split text into chunks (documents)
def read_text_file(filename):
    with open(filename, "r", encoding="utf-8") as file:
        return file.read()

def split_text_into_documents(text, chunk_size=400, chunk_overlap=20):
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        document = Document(page_content=chunk)
        chunks.append(document)
        start += chunk_size - chunk_overlap

    return chunks


# Add documents to the vector store
def add_documents_to_vector_store(vector_store, documents):
    uuids = [str(uuid4()) for _ in documents]
    vector_store.add_documents(documents=documents, ids=uuids)
    print(f"Added {len(documents)} documents to the vector store.")
