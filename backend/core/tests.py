# core/tests.py
import os
from rest_framework.test import APIClient
from rest_framework import status
from django.test import TestCase
from .utils import generate_token, decode_token


class ConnectionToRag(TestCase):
    def setUp(self):
        self.url = 'http://localhost:8042/query/'
        self.user_id = 'user123'
        self.query = 'Who is Amos Tversky?'
        self.payload = {
            'user_id': self.user_id,
            'query': self.query,
        }
    
        self.client = APIClient()

    def test_query(self):
        response = self.client.post(self.url, self.payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TokenTest(TestCase):
    def setUp(self):
        self.secret = os.getenv('AUTH_KEY')
        self.from_user = 1
        self.to_user = 2
        
    def test_generate_token(self):
        token = generate_token(
            self.from_user,
            self.to_user,
            expires_in=1,
            scope=('read', 'write')
            )
        claims = decode_token(token)
        self.assertEqual(claims['user_id'], self.from_user)
        self.assertEqual(claims['reciver'], self.to_user)