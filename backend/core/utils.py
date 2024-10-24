import os
import requests
import uuid # for generating random string
from authlib.jose import jwt
from datetime import datetime, timedelta
from .models import Token
# from django.conf import settings


def generate_token(from_user: int, to_user: int, *, expires_in: int | None = None, scope: tuple[str]=('read',), edit: bool = False) -> str:
    '''
    Generates a token containing id of user that created it and who will recive it. Its purpose
    is to allow user to share their resources (like chat with our bot) with other users through hiss id.
    '''
    jti: str = str(uuid.uuid4()) # generating random str
    for x in scope:
        if x not in ('read', 'write'):
            raise ValueError('Invalid scope')

    exp = None
    if expires_in:
        exp = timedelta(expires_in) + datetime.now() 

    payload = {
        'jti': jti,
        'user_id': from_user,
        'reciver': to_user,
        'exp': exp.timestamp(),
        'scope': scope
    }
    header: dict[str, str] = {'alg': 'HS256'}
    private_key: str = os.getenv('AUTH_KEY')
    token = jwt.encode(header, payload, private_key)
    
    if not edit:
        Token.objects.create(
            user_id=from_user,
            owner=to_user,
            jti=jti,
            token=token,
            is_active=True,
            created_at=datetime.now(),
            expires_at = exp
        )

    return token


def decode_token(token: bytes) -> dict | None:
    scopes: list[str] = ['read', 'write']
    private_key: str = os.getenv('AUTH_KEY')

    claims = jwt.decode(token, private_key)
    #validation
    if claims['exp'] and datetime.now().timestamp() > claims['exp']:

        raise jwt.ExpiredTokenError('Token expired')
        
    return claims


def chatbot_get_answer(user_id: int, query: str, token: bytes) -> dict | str:
    payload = {
        'user_id':  user_id,
        'query': query,
        'token': token
    }
    url = 'http://localhost:8042/query/'

    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            return response.json()
        else:
            return 'An error occurred. Please try again later'
    except requests.RequestException as e:
        return f"An error occured: {e}"


def generate_flashcards(context, prompt="Generate flashcards based on the following context:"):
    """
    Generuje fiszki na podstawie dostarczonego kontekstu.

    :param context: Tekst kontekstu do generowania fiszek.
    :param prompt: Polecenie do modelu AI.
    :return: Tekst wygenerowanych fiszek.
    """
    # try:
    #     response = openai.Completion.create(
    #         engine="text-davinci-003",  # Możesz użyć nowszego modelu, jeśli jest dostępny
    #         prompt=f"{prompt}\n\n{context}",
    #         max_tokens=150,
    #         n=1,
    #         stop=None,
    #         temperature=0.7,
    #     )
    #     flashcards = response.choices[0].text.strip()
    #     return flashcards
    # except Exception as e:
    #     print(f"Error generating flashcards: {e}")
    #     return ""
    pass


def generate_exam(context, prompt="Generate an exam based on the following context:"):
    """
    Generuje egzamin na podstawie dostarczonego kontekstu.

    :param context: Tekst kontekstu do generowania egzaminu.
    :param prompt: Polecenie do modelu AI.
    :return: Tekst wygenerowanego egzaminu.
    """
    # try:
    #     response = openai.Completion.create(
    #         engine="text-davinci-003",
    #         prompt=f"{prompt}\n\n{context}",
    #         max_tokens=300,
    #         n=1,
    #         stop=None,
    #         temperature=0.7,
    #     )
    #     exam = response.choices[0].text.strip()
    #     return exam
    # except Exception as e:
    #     print(f"Error generating exam: {e}")
    #     return ""
    pass


