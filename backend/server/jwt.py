import os
from authlib.jose import jwt, JWTClaims
from authlib.jose.errors import ExpiredTokenError, InvalidTokenError
from datetime import datetime, timedelta, timezone


def generate_token(user_id: int, role: str, iss: str, path: str) -> bytes:
    header: dict[str, str] = {'alg': 'RS512'}
    payload: dict[str, str | int] = {
        'iss': iss,
        'iat': int(datetime.now(timezone.utc).timestamp()),
        'exp': int((datetime.now(timezone.utc) + timedelta(hours=24)).timestamp()),
        # 'exp': int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()),
        'aud': user_id,
        'pre': role,
        }
    
    with open(path, 'r') as key:
        private_key: str = key.read()
        
    if not private_key:
        raise ValueError('Private key not found')
    
    token: bytes = jwt.encode(header, payload, private_key)
    return token


def decode_token(token: bytes, path: str) -> JWTClaims | None:
    data: None | JWTClaims = None
    with open(path, 'r') as key:
        public_key: str = key.read()
    try:
        data = jwt.decode(token, public_key)
        data.validate()
        # data.validate_exp(int(datetime.now(timezone.utc).timestamp()), 0)
    except ExpiredTokenError as e:
        print('Token verification failed: ', e)
    except InvalidTokenError:
        print('Invalid token')
    else:
        return data
    return None
    

# test
if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()
    token: bytes = generate_token(1, 'admin', 'me', path=os.getenv('PUP_PATH', ''))
    print(token)
    data: dict | None = decode_token(token, path=os.getenv('PRP_PATH', ''))
    print(data)