import os
import requests
from authlib.jose import jwt, JWTClaims, JsonWebToken
from datetime import datetime, timedelta
from authlib.jose.errors import MissingClaimError, InvalidClaimError, ExpiredTokenError

class FailedTokenAuthentication(Exception):
    pass


def generate_token(
    *,
    iss:str = 'torched-user-interface',
    scope: str = 'read',
    expired: bool = False,
    **kwargs
    ) -> JsonWebToken:
    """
    
    """

        
    exp = timedelta(days=1) + datetime.now() if not expired else datetime.now() - timedelta(days=1)
    
    payload: dict = {
        'iss': iss,
        'scope': scope,
        'exp': exp
    }
    header: dict[str, str] = kwargs.get('header', {'alg': 'HS256'})
    private_key: str = kwargs.get('private_key', os.getenv('AUTH_KEY'))
    token: JsonWebToken = jwt.encode(header, payload, private_key)

    return token


def decode_token(token: bytes, debug: bool = False,) -> dict | None:
    """"""
    private_key: str = os.getenv('AUTH_KEY')

    # Decode the token first
    claims_option = {
        'iss': {
            'essential': True,
            'validate': lambda data, iss: iss in ['torched-user-interface', 'torched-backend-veryfication']
        },
        'scope': {
            'essential': True,
            'validate': lambda data, scope: scope in ['read', 'write', 'delete']
        },        
        'exp': {
        # jwt automatically checks this so validate is not required
            'essential': True,
        #     'validate': lambda exp_date: datetime.now().timestamp() >= exp_date
        }
    }
    # will not accept claims_option not any other arguments
    claims: JWTClaims = jwt.decode(token, private_key, claims_options=claims_option)

    def log(msg: str, debug=False) -> None:
        path = 'token_log.txt' if not debug else 'debug_token_log.txt'
        with open(path, 'a') as file:
            file.write(f'{datetime.now()} - {e}\n') 
        
    try:
        claims.validate()
        
        # for some reason it won't validate it with .validate()
        # essentials = ['exp', 'data', 'iss', 'scope']
        # if not all(essential in claims for essential in essentials):
        #     raise Exception('Missing claim')
        # if not claims_option['scope']['validate'](claims['scope']):
        #     raise Exception('Invalid scope')
        # if not claims_option['iss']['validate'](claims['iss']):
        #     raise Exception('Invalid iss')   
        
    except MissingClaimError as e:
        log(e, debug)
        
    except InvalidClaimError as e:
        log(e, debug)
        
    except ExpiredTokenError as e:
        log(e, debug)
    
    except Exception as e:
        log(e, debug)
        raise FailedTokenAuthentication(f"Failed to decode token: {str(e)}")
    
    else:
        # If all validations pass, return claims
        return claims
    return None



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


