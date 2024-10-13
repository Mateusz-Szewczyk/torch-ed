# tests/test_api.py

import os
import pytest
from fastapi.testclient import TestClient
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from rag.main_api import app

client = TestClient(app)

def test_upload_pdf():
    user_id = "test_user"
    file_description = "Test PDF file"
    category = "Test Category"
    start_page = "7"
    end_page = "8"
    # Ensure that the test PDF file exists
    test_pdf_path = 'tests/test_files/test.pdf'
    os.makedirs('tests/test_files', exist_ok=True)
    # Create a dummy PDF file for testing if it doesn't exist
    if not os.path.exists(test_pdf_path):
        with open(test_pdf_path, 'wb') as f:
            f.write(b'%PDF-1.4 test pdf content')
    with open(test_pdf_path, 'rb') as f:
        response = client.post(
            "/upload/",
            data={
                'user_id': user_id,
                'file_description': file_description,
                'category': category,
                'start_page': start_page,
                'end_page': end_page
            },
            files={'file': ('test.pdf', f, 'application/pdf')}
        )
    assert response.status_code == 200
    assert response.json()['message'].startswith("File processed successfully")

def test_query_knowledge():
    user_id = "test_user"
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
    assert response.json()['answer'] != ""

def test_upload_unsupported_file():
    user_id = "test_user"
    file_description = "Test Unsupported File"
    category = "Test Category"
    with open('tests/test_files/test.txt', 'w') as f:
        f.write("This is a test text file.")
    with open('tests/test_files/test.txt', 'rb') as f:
        response = client.post(
            "/upload/",
            data={
                'user_id': user_id,
                'file_description': file_description,
                'category': category
            },
            files={'file': ('test.txt', f, 'text/plain')}
        )
    assert response.status_code == 400
    assert response.json()['message'].startswith("Unsupported file type")
