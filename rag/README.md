
# RAG (Retrieval-Augmented Generation) Module

This module provides a **Retrieval-Augmented Generation (RAG)** system that allows users to upload documents (PDFs, DOCX, ODT, etc.), process them, and later query a knowledge base built from the uploaded files. The knowledge base is built using vector embeddings and graph databases (Neo4j). The system is designed to generate answers using these stored documents via FastAPI.

## Table of Contents

- [Getting Started](#getting-started)
  - [Running the Application](#running-the-application)
  - [Requirements](#requirements)
- [API Endpoints](#api-endpoints)
  - [Upload File (`/upload/`)](#upload-file-upload)
  - [Query Knowledge (`/query/`)](#query-knowledge-query)
- [Sample Usage](#sample-usage)
  - [Upload a PDF](#upload-a-pdf)
  - [Query Knowledge](#query-knowledge)
- [Testing the API](#testing-the-api)

---

## Getting Started

### Running the Application

The `rag` module runs on **Docker**, and requires both a **FastAPI** app for handling file uploads and queries, and a **Neo4j** database to store extracted knowledge and relationships. To run the system, you need Docker installed on your machine.

1. **Clone the repository**:
   ```bash
   git clone <repo-url>
   cd rag
   ```

2. **Run the module using Docker Compose**:
   In your `docker-compose.yml` file, make sure the following services are defined:

   ```yaml
   rag:
     build: ./rag
     ports:
       - '8042:8042'
     volumes:
       - ./rag:/app

   neo4j:
     image: neo4j:latest
     ports:
       - "7474:7474"  # Neo4j Browser (Web Interface)
       - "7687:7687"  # Bolt protocol for Neo4j interactions
     environment:
       NEO4J_AUTH: "neo4j/password"
     volumes:
       - neo4j_data:/data
       - neo4j_logs:/logs
   ```

3. **Start the services**:
   ```bash
   docker-compose up
   ```

4. **Access the services**:
   - **RAG API**: The FastAPI app will be running at `http://localhost:8042`.
   - **Neo4j Database**: The Neo4j Browser is available at `http://localhost:7474`. You can log in using the credentials `neo4j/password`.

---

### Requirements

The `rag` module depends on the following services and packages:
- **FastAPI**: The web framework for handling file uploads and queries.
- **Neo4j**: A graph database used to store the relationships and knowledge extracted from the uploaded documents.
- **SentenceTransformers**: Used to generate vector embeddings for the text content.
- **PyMuPDF**: For processing and extracting text from PDF documents.
- **PyPDF2**: For text-based PDF extraction.

---

## API Endpoints

The `rag` module exposes two main endpoints: one for uploading documents and another for querying the knowledge base.

### Upload File (`/upload/`)

This endpoint allows users to upload a document (PDF, DOCX, ODT, RTF) and process it into chunks. The module will extract text, generate vector embeddings, and store knowledge and relationships in Neo4j.

#### Method: `POST`

#### Request Parameters (Form Data):
- `user_id` (required): The ID of the user uploading the document.
- `file_description` (optional): Description of the file being uploaded.
- `category` (optional): Category to help organize the uploaded document.
- `start_page` (optional): The starting page number for processing (for PDFs).
- `end_page` (optional): The ending page number for processing (for PDFs).
- `file` (required): The document file to be uploaded.

**`start_page` and `end_page` is used only for PDF files!!!**
#### Example Request:

```bash
curl -X 'POST'   'http://localhost:8042/upload/'   -F 'user_id=user123'   -F 'file_description=My test document'   -F 'category=Test'   -F 'start_page=1'   -F 'end_page=5'   -F 'file=@path_to_your_file.pdf'
```

#### Response:
- **200 OK**: If the file was processed successfully, it will return a success message and metadata about the file.
- **500 Internal Server Error**: If there was an error during the processing of the document.

### Query Knowledge (`/query/`)

This endpoint allows users to query the knowledge base for specific information. The query is processed by searching the chunks stored in the vector database, and an answer is generated using the retrieved chunks.

#### Method: `POST`

#### Request Parameters (Form Data):
- `user_id` (required): The ID of the user making the query.
- `query` (required): The user's query.

#### Example Request:

```bash
curl -X 'POST'   'http://localhost:8042/query/'   -F 'user_id=user123'   -F 'query=Who is Amos Tversky?'
```

**For testing purposes, please use** *user_id: user123* **, as there is already data uploaded as user123 in the vector store.**
#### Response:
- **200 OK**: Returns the generated answer based on the query and retrieved chunks.
- **500 Internal Server Error**: If there was an error while generating the answer.

---

## Sample Usage

### Upload a PDF

To upload a PDF file and process it, use the `/upload/` endpoint with the following sample request:

```bash
curl -X POST "http://localhost:8042/upload/"     -F "user_id=user123"     -F "file_description=Research Paper"     -F "category=Science"     -F "start_page=0"     -F "end_page=10"     -F "file=@/path/to/document.pdf"
```

### Query Knowledge

To query the knowledge base for information stored in the uploaded documents, use the `/query/` endpoint with a specific query:

```bash
curl -X POST "http://localhost:8042/query/"     -F "user_id=user123"     -F "query=Who is Amos Tversky?"
```

---

## Testing the API

To test the functionality of the RAG module, the following test cases are included:

### Upload PDF Test:

```python
def test_upload_pdf():
    user_id = "test_user"
    file_description = "Test PDF file"
    category = "Test Category"
    start_page = "1"
    end_page = "3"
    with open('tests/test_files/sample.pdf', 'rb') as f:
        response = client.post(
            "/upload/",
            data={
                'user_id': user_id,
                'file_description': file_description,
                'category': category,
                'start_page': start_page,
                'end_page': end_page
            },
            files={'file': ('sample.pdf', f, 'application/pdf')}
        )
    assert response.status_code == 200
```

### Query Knowledge Test:

```python
def test_query_knowledge():
    user_id = "user123"
    query = "Who is Amos Tversky?"
    response = client.post(
        "/query/",
        data={
            'user_id': user_id,
            'query': query
        }
    )
    assert response.status_code == 200
    assert 'answer' in response.json()
```

To run the tests, use `pytest`:

```bash
pytest tests/test_api.py
```

---

Now you're all set to use the **RAG Module** for uploading documents, processing them into a knowledge graph, and querying for answers!
