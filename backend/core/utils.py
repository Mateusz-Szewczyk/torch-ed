import os
import requests
from authlib.jose import jwt, JWTClaims, JsonWebToken
from datetime import datetime, timedelta
from authlib.jose.errors import MissingClaimError, InvalidClaimError, ExpiredTokenError
# from django.conf import settings

class FailedTokenAuthentication(Exception):
    pass


def generate_token(
    data: list[int],
    *,
    iss:str = 'torched-user-interface',
    scope: str = 'read',
    expired: bool = False,
    **kwargs
    ) -> JsonWebToken:
    """
    Generates jwt with help of (authlib.jose)[https://docs.authlib.org/en/latest/jose/jwt.html]
    Kwargs can contain: header, private_key.
    For details see link to authlib.jose
    _summary_

    Args:
        requested_data (list[int], optional): _description_. Defaults to None.
        iss (str, optional): _description_. Defaults to 'torched-user-interface'.
        scope (str, optional): _description_. Defaults to 'read'.
        expired (bool, optional): _description_. Defaults to False.

    Returns:
        JsonWebToken: _description_
    """

        
    exp = timedelta(days=1) + datetime.now() if not expired else 0
    
    payload: dict = {
        'iss': iss,
        'data': data,
        'scope': scope,
        'exp': exp
    }
    header: dict[str, str] = kwargs.get('header', {'alg': 'HS256'})
    private_key: str = kwargs.get('private_key', os.getenv('AUTH_KEY'))
    token: JsonWebToken = jwt.encode(header, payload, private_key)

    return token


def decode_token(token: bytes) -> dict | None:

    private_key: str = os.getenv('AUTH_KEY')

    # Decode the token first
    claims_option = {
        'iss': {
            'essential': True,
            'validate': lambda iss: iss in ['torched-user-interface', 'torched-backend-veryfication']
        },
        'data': {
            'essential': True,
        },
        'scope': {
            'essential': True,
            'validate': lambda scope: scope in ['read', 'write']
        },        
        'exp': {
            'essential': True,
            'validate': lambda exp_date:datetime.now().timestamp() > exp_date
        }
    }
    claims: JWTClaims = jwt.decode(token, private_key)
    claims.claims_option = claims_option

    try:
        claims.validate()
        
        # for some reason it won't validate it with .validate()
        essentials = ['exp', 'data', 'iss', 'scope']
        if not all(essential in claims for essential in essentials):
            raise Exception('Missing claim')
        if not claims_option['scope']['validate'](claims['scope']):
            raise Exception('Invalid scope')
        if not claims_option['iss']['validate'](claims['iss']):
            raise Exception('Invalid iss')
        
    except MissingClaimError as e:
        raise Exception(f"Missing claim: {str(e)}")
    except InvalidClaimError as e:
        raise FailedTokenAuthentication(f"Invalid claim")
    except ExpiredTokenError as e:
        raise FailedTokenAuthentication(f"Token has expired")
    except Exception as e:
        raise FailedTokenAuthentication(f"Failed to decode token: {str(e)}")

    # If all validations pass, return claims
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


