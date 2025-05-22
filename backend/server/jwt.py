from authlib.jose import jwt, JWTClaims
from authlib.jose.errors import ExpiredTokenError, InvalidTokenError
from datetime import datetime, timedelta, timezone
from itsdangerous import URLSafeSerializer, BadSignature, SignatureExpired
from .config import Config
import logging

# Configure logging for debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def generate_token(user_id: int, role: str, iss: str, path: str) -> bytes:
    """
    Generate a JWT token for user authentication.

    :param user_id: The user ID
    :param role: The user's role
    :param iss: Issuer of the token
    :param path: Path to the private key file
    :return: Encoded JWT token
    """
    header = {'alg': 'RS512'}
    payload = {
        'iss': iss,
        'iat': int(datetime.now(timezone.utc).timestamp()),
        'exp': int((datetime.now(timezone.utc) + timedelta(hours=24 * 5)).timestamp()),
        'aud': user_id,
        'pre': role,
    }
    print(f"DEBUG: Generating token with user_id: {user_id}")

    with open(path, 'r') as key_file:
        private_key = key_file.read()

    if not private_key:
        raise ValueError('Private key not found')

    token = jwt.encode(header, payload, private_key)
    return token


def decode_token(token: bytes, path: str) -> JWTClaims | None:
    """
    Decode and validate a JWT token.

    :param token: The JWT token to decode
    :param path: Path to the public key file
    :return: Decoded JWT claims or None if invalid
    """
    with open(path, 'r') as key_file:
        public_key = key_file.read()
    try:
        data = jwt.decode(token, public_key)
        data.validate()
    except ExpiredTokenError as e:
        logger.warning('Token verification failed: %s', e)
    except InvalidTokenError:
        logger.warning('Invalid token')
    else:
        return data
    return None


def generate_confirmation_token(email: str) -> str | None:
    """
    Generate a confirmation token for email verification.

    :param email: The email address to encode
    :return: The generated token or None if configuration is missing
    """
    if not Config.SALT or not Config.SECRET_KEY:
        logger.error('SALT or SECRET_KEY not configured')
        return None

    try:
        serializer = URLSafeSerializer(Config.SECRET_KEY)
        token = serializer.dumps(email, salt=Config.SALT)
        logger.debug('Generated confirmation token for email %s: %s', email, token)
        return token
    except Exception as e:
        logger.error('Failed to generate confirmation token for email %s: %s', email, e)
        return None


def confirm_token(token: str, expiration: int = 60 * 60 * 10) -> tuple[bool, str | None]:
    """
    Decode and validate a confirmation token.

    :param token: The confirmation token to decode
    :param expiration: Token expiration time in seconds (default: 10 hours)
    :return: Tuple (is_valid, email) where is_valid is a boolean and email is a string or None
    """
    if not Config.SALT or not Config.SECRET_KEY:
        logger.error('SALT or SECRET_KEY not configured')
        return False, None

    serializer = URLSafeSerializer(Config.SECRET_KEY)
    try:
        email = serializer.loads(token, salt=Config.SALT, max_age=expiration)
        logger.debug('Token decoded successfully for email: %s', email)
        return True, email
    except SignatureExpired:
        logger.warning('Token expired: %s', token)
        return False, None
    except BadSignature:
        logger.warning('Invalid token: %s', token)
        return False, None
    except Exception as e:
        logger.error('Unexpected error decoding token %s: %s', token, e)
        return False, None


# Test
if __name__ == '__main__':
    from .config import load_private_keys

    load_private_keys()
    token = generate_token(1, 'admin', 'me', path=Config.PRP_PATH)
    print(token)
    data = decode_token(token, path=Config.PRP_PATH)  # Assuming PRP_PATH is public key
    print(data)