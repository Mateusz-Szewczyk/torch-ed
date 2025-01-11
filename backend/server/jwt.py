
from authlib.jose import jwt, JWTClaims
from authlib.jose.errors import ExpiredTokenError, InvalidTokenError
from datetime import datetime, timedelta, timezone
from itsdangerous import URLSafeSerializer, BadSignature, SignatureExpired
from .config import Config

def generate_token(user_id: int, role: str, iss: str, path: str) -> bytes:
    header = {'alg': 'RS512'}
    payload = {
        'iss': iss,
        'iat': int(datetime.now(timezone.utc).timestamp()),
        'exp': int((datetime.now(timezone.utc) + timedelta(hours=24)).timestamp()),
        'aud': user_id,
        'pre': role,
    }

    with open(path, 'r') as key_file:
        private_key = key_file.read()

    if not private_key:
        raise ValueError('Private key not found')

    token = jwt.encode(header, payload, private_key)
    return token

def decode_token(token: bytes, path: str) -> JWTClaims | None:
    data = None
    with open(path, 'r') as key_file:
        public_key = key_file.read()
    try:
        data = jwt.decode(token, public_key)
        data.validate()
    except ExpiredTokenError as e:
        print('Token verification failed: ', e)
    except InvalidTokenError:
        print('Invalid token')
    else:
        return data
    return None

def generate_confirmation_token(email: str) -> str | None:
    if not Config.SALT or not Config.SECRET_KEY:
        return None

    serializer = URLSafeSerializer(Config.SECRET_KEY)
    token = serializer.dumps(email, salt=Config.SALT)
    return token

def confirm_token(token: str, expiration: int = 60*60*10) -> bool | str:
    if not Config.SALT or not Config.SECRET_KEY:
        raise ValueError('SALT and SECRET_KEY must be defined!')
    serializer = URLSafeSerializer(Config.SECRET_KEY)
    try:
        email = serializer.loads(
            token,
            salt=Config.SALT,
            max_age=expiration
        )
    except (BadSignature, SignatureExpired):
        return False
    return email

# test
if __name__ == '__main__':
    from .config import load_private_keys
    load_private_keys()
    token = generate_token(1, 'admin', 'me', path=Config.PRP_PATH)
    print(token)
    data = decode_token(token, path=Config.PRP_PATH)  # Assuming PRP_PATH is public key
    print(data)
