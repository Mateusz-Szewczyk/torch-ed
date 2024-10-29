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
        self.data = [1, 2, 3]
        self.basic_token_1: JsonWebToken = generate_token(
            data=self.data,
            scope='read',
            )
        self.basic_token_2: JsonWebToken = generate_token(
            data=self.data,
            scope='write',
        )
        self.expired_token: JsonWebToken = generate_token(
            data=self.data,
            scope='read',
            expired=True
        )
        self.wrong_scope_token: JsonWebToken = generate_token(
            self.data,
            scope='smell'
        )
        self.missing_exp_token: JsonWebToken = jwt.encode(
            header={'alg': 'HS256'},
            payload={
                'iss': 'torched-user-interface',
                'data': [1, 2],
                'scope': 'read',
                },
            key=os.getenv('AUTH_KEY')
        )
        self.missing_data_token: JsonWebToken = jwt.encode(
            header={'alg': 'HS256'},
            payload={
                'iss': 'torched-user-interface',
                'scope': 'read',
                'exp': timedelta(days=1) + datetime.now()
                },
            key=os.getenv('AUTH_KEY')
        )
        self.missing_scope_token: JsonWebToken = jwt.encode(
            header={'alg': 'HS256'},
            payload={
                'iss': 'torched-user-interface',
                'data': [1, 2],
                'exp': timedelta(days=1) + datetime.now()
                },
            key=os.getenv('AUTH_KEY')
        )
        self.wrong_issuer_token: JsonWebToken = generate_token(
            data=self.data,
            iss='me'
        )
        
    def test_decode_token(self) -> None:
        
        claims: JWTClaims = decode_token(self.basic_token_1)
        self.assertEqual(claims['iss'], 'torched-user-interface', 'iss')
        self.assertEqual(claims['data'], self.data, 'data')
    
    def test_decode_token2(self) -> None:
        
        claims: JWTClaims = decode_token(self.basic_token_2)
        self.assertEqual(claims['iss'], 'torched-user-interface', 'iss')
        self.assertEqual(claims['data'], self.data, 'data')
    
    def test_expired_token(self) -> None:
        try:
            decode_token(self.expired_token)
        except FailedTokenAuthentication as e:
            self.assertEqual(str(e), "Token has expired")
        else:
            self.assertEqual(
                1, 0,
                'Expected FailedTokenAuthorization: Expired but got nothing')
    def test_wrong_scope_token(self) -> None:
        try:
            decode_token(self.wrong_scope_token)
        except FailedTokenAuthentication as e:
            self.assertIn('Failed to decode token:', str(e))
        else:
            self.assertEqual(
                1, 0,
                'Expected FailedTokenAuthorization: Wrong Scope but got nothing')
    
    def test_wrong_iss_token(self) -> None:
        try:
            decode_token(self.wrong_issuer_token)
        except FailedTokenAuthentication as e:
            self.assertIn('Failed to decode token:', str(e))
        else:
            self.assertEqual(
                1, 0,
                'Expected FailedTokenAuthorization: Invalid iss but got nothing')
    def test_missing_exp_token(self) -> None:
        try:
            decode_token(self.missing_exp_token)
        except FailedTokenAuthentication as e:
            self.assertIn('Failed to decode token:', str(e))
        else:
            self.assertEqual(
                1, 0,
                'Expected FailedTokenAuthorization: Missing claim but got nothing')
    
    def test_missing_data_token(self) -> None:
        try:
            decode_token(self.missing_data_token)
        except FailedTokenAuthentication as e:
            self.assertIn('Failed to decode token:', str(e))
        else:
            self.assertEqual(
                1, 0,
                'Expected FailedTokenAuthorization: Missing claim but got nothing')
    
    def test_missing_scope_token(self) -> None:
        try:
            decode_token(self.missing_scope_token)
        except FailedTokenAuthentication as e:
            self.assertIn('Failed to decode token:', str(e))
        else:
            self.assertEqual(
                1, 0,
                'Expected FailedTokenAuthorization: Missing claim but got nothing')
                
            