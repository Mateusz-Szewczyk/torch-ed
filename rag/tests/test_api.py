# tests/test_api.py

import os
import pytest
from fastapi.testclient import TestClient
import sys

# Add the parent directory to sys.path to allow module imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from rag.main import app

client = TestClient(app)

def test_upload_pdf():
    """
    Test uploading a PDF file with specified start and end pages.
    """
    user_id = "test_user"
    file_description = "Test PDF file"
    category = "Test Category"
    start_page = "0"  # 0-based index
    end_page = "3"    # Exclusive (process up to page 3)

    test_pdf_path = 'tests/test_files/test.pdf'
    os.makedirs('tests/test_files', exist_ok=True)

    # Create a valid PDF file for testing if it doesn't exist
    if not os.path.exists(test_pdf_path):
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        c = canvas.Canvas(test_pdf_path, pagesize=letter)
        c.drawString(100, 750, "This is page 1 of the test PDF.")
        c.showPage()
        c.drawString(100, 750, "This is page 2 of the test PDF.")
        c.showPage()
        c.drawString(100, 750, "This is page 3 of the test PDF.")
        c.save()

    # Clean the uploads directory before the test to avoid conflicts
    upload_pdf_path = 'uploads/test.pdf'
    if os.path.exists(upload_pdf_path):
        os.remove(upload_pdf_path)

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
    assert response.status_code == 200, f"Response body: {response.text}"
    assert response.json()['message'].startswith("File processed successfully")

def test_query_knowledge():
    """
    Test querying the knowledge base for a specific question.
    """
    user_id = "user123"
    query = "Who is Amos Tversky?"
    response = client.post(
        "/query/",
        data={
            'user_id': user_id,
            'query': query
        }
    )
    assert response.status_code == 200, f"Response body: {response.text}"
    assert 'answer' in response.json(), "Response JSON does not contain 'answer' key."
    assert response.json()['answer'] != "", "The 'answer' field is empty."
    print(f"Answer received: {response.json()['answer']}")


def test_upload_unsupported_file():
    """
    Test uploading an unsupported file type (e.g., .txt file).
    """
    user_id = "test_user"
    file_description = "Test Unsupported File"
    category = "Test Category"
    test_txt_path = 'tests/test_files/test.txt'

    # Create a simple text file for testing
    os.makedirs('tests/test_files', exist_ok=True)
    with open(test_txt_path, 'w') as f:
        f.write("This is a test text file.")

    with open(test_txt_path, 'rb') as f:
        response = client.post(
            "/upload/",
            data={
                'user_id': user_id,
                'file_description': file_description,
                'category': category
            },
            files={'file': ('test.txt', f, 'text/plain')}
        )
    assert response.status_code == 400, f"Response body: {response.text}"
    assert response.json()['message'].startswith("Unsupported file type")
