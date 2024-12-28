from authlib.jose import jwt, JWTClaims
from authlib.jose.errors import ExpiredTokenError, InvalidTokenError
from datetime import datetime, timedelta, timezone


def get_token(user_id: int, role: str, iss: str, path: str) -> bytes:
    header: dict[str, str] = {'alg': 'RS512'}
    payload: dict[str, str | int] = {
        'iss': iss,
        'iat': int(datetime.now(timezone.utc).timestamp()),
        'exp': int((datetime.now(timezone.utc) + timedelta(hours=24)).timestamp()),
        'aud': user_id,
        'pre': role,
        }
    
    with open(path, 'r') as key:
        private_key: str = key.read()
        
    if not private_key:
        raise ValueError('Private key not found')
    
    token: bytes = jwt.encode(header, payload, private_key)
    return token


def decode_token(token: bytes, path: str) -> dict | None:
    data: None | JWTClaims = None
    with open(path, 'r') as key:
        public_key: str = key.read()
    try:
        data = jwt.decode(token, public_key)
        # TODO: check if this is validating
        data.validate()
    except ExpiredTokenError as e:
        print('Token verification failed: ', e)
    except InvalidTokenError:
        print('Invalid token')
    
    return data

    
# test
if __name__ == '__main__':
    token: bytes = get_token(1, 'admin', 'me', path='/home/adam/Vronst/Programming/TORCHed/private_key.pem')
    print(token)
    data: dict | None = decode_token(token, path='/home/adam/Vronst/Programming/TORCHed/private_key.pem')
    print(data)