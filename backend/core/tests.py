# core/tests.py
import os
from rest_framework.test import APIClient
from rest_framework import status
from django.test import TestCase
from datetime import datetime, timedelta
from .utils import generate_token, decode_token, FailedTokenAuthentication
from authlib.jose import JWTClaims, JsonWebToken, jwt


class ConnectionToRag(TestCase):
    def setUp(self):
        self.url = 'http://127.0.0.1:8042/query/'
        self.user_id = 'user123'
        self.query = 'Who is Amos Tversky?'
        self.payload = {
            'user_id': self.user_id,
            'query': self.query,
        }
    
        self.client = APIClient()

    def test_query(self):
        response = self.client.post(self.url, self.payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content.decode('utf-8'))


class TokenTest(TestCase):
    def setUp(self) -> None:
        self.secret = os.getenv('AUTH_KEY')
        self.basic_token_1: JsonWebToken = generate_token(
            scope='read',
            )
        self.basic_token_2: JsonWebToken = generate_token(
            scope='write',
        )
        self.expired_token: JsonWebToken = generate_token(
            scope='read',
            expired=True
        )
        self.wrong_scope_token: JsonWebToken = generate_token(
            scope='smell'
        )
        self.missing_exp_token: JsonWebToken = jwt.encode(
            header={'alg': 'HS256'},
            payload={
                'iss': 'torched-user-interface',
                'scope': 'read',
                },
            key=os.getenv('AUTH_KEY')
        )
        self.missing_scope_token: JsonWebToken = jwt.encode(
            header={'alg': 'HS256'},
            payload={
                'iss': 'torched-user-interface',
                'exp': timedelta(days=1) + datetime.now()
                },
            key=os.getenv('AUTH_KEY')
        )
        self.wrong_issuer_token: JsonWebToken = generate_token(
            iss='me'
        )
        
    def test_decode_token(self) -> None:
        claims: JWTClaims = decode_token(self.basic_token_1, debug=True)
        self.assertEqual(claims['iss'], 'torched-user-interface', 'iss')
    
    def test_decode_token2(self) -> None:
        claims: JWTClaims = decode_token(self.basic_token_2, debug=True)
        self.assertEqual(claims['iss'], 'torched-user-interface', 'iss')
    
    def test_expired_token(self) -> None:
        result = decode_token(self.expired_token, debug=True)
        self.assertEqual(result, None)
        
    def test_wrong_scope_token(self) -> None:
        result = decode_token(self.wrong_scope_token, debug=True)
        self.assertEqual(result, None)
        
    def test_wrong_iss_token(self) -> None:
        result = decode_token(self.wrong_issuer_token, debug=True)
        self.assertEqual(result, None)  

    def test_missing_exp_token(self) -> None:
        result = decode_token(self.missing_exp_token, debug=True)
        self.assertEqual(result, None)    
        
    def test_missing_scope_token(self) -> None:
        result = decode_token(self.missing_scope_token, debug=True)
        self.assertEqual(result, None)                
            