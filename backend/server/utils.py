import datetime
import logging
import os
import hmac
import hashlib

from flask import Request, jsonify, request

from flask.cli import load_dotenv
from werkzeug.security import check_password_hash
from functools import wraps
from typing import Callable
from .models import User
from .config import Config


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
load_dotenv()

FRONTEND: str = os.getenv('FRONTEND', 'https://torched.pl')
COOKIE_AUTH: str = 'TorchED_AUTH'


class Misconfiguration(Exception):
    pass


def data_check(request: Request, method: str) -> tuple | dict:
    from . import session
    if method not in ['login', 'register']:
        return jsonify({'error': 'Wrong configuration (method)'}), 500
    
    if not (data := request.get_json()):
        return jsonify({'error': 'Empty body'}), 400

    path = Config.PRP_PATH

    user_name: str | None = data.get('user_name')
    user: User | None = User.get_user(session, user_name) if user_name else None

    password: str | None
    password2: str | None
    if method == 'login':
        if not user or not (password := data.get('password')):
            return jsonify({'error': 'Missing variable'}), 400
            
        if not check_password_hash(user.password, password):
            return jsonify({ 'error': 'Invalid credentials' }), 400
        
        if not user.confirmed:
            return jsonify({ 'error': 'User not confirmed'}), 423
        return {'user': user, 'path': path}
    
    elif method == 'register':
        if user:
            return jsonify({'error': 'User with this name already exists!'}), 400
        
        email: str | None = data.get('email')
        
        if not email or session.query(User).filter_by(email=email).first():
            return jsonify({'error': 'No email in body or email already taken!'}), 400
        
        if not (password := data.get('password')) or \
            not (password2 := data.get('password2')) or \
                not (password == password2):
            return jsonify({'error': 'Password not reapeated correctly'}), 400
        
        # return User(
        #     user_name=user_name,
        #     password=generate_password_hash(password, salt_length=24),
        #     email=email,
        #     age=data.get('age', None),
        #     role=data.get('role', 'user')
        # )
        return {
            'user_name': user_name,
            'password': password,
            'email': email,
            'role': data.get('role', 'user'),
            'age': data.get('age', None)}

    return jsonify({'error': 'Something went wrong'}), 500

    
def signature_check(func: Callable) -> Callable | tuple:
    @wraps(func)
    def wraper(*args, **kwargs) -> tuple | Callable:
        key: str | None = os.getenv('SIGNATURE')
        messege: str | None = os.getenv('MESSAGE')
        
        if not key or not messege:
            return jsonify({'error': 'Server misconfiguration'}), 500
        key_bytes: bytes = key.encode('utf-8')
        messege_bytes: bytes = messege.encode('utf-8')
        signature: str = request.headers.get('TorchED-S', '')
        expected_signature: str = hmac.new(key_bytes, messege_bytes, hashlib.sha256).hexdigest()

        if not hmac.compare_digest(signature, expected_signature):
            return jsonify({'error': 'Unauthorized'}), 401
        
        return func(*args, **kwargs)
    
    return wraper



def log_auth_attempt(action, email, ip, success, reason=None):
    """Log authentication attempt for audit purposes"""
    log_data = {
        'action': action,
        'email': email,
        'ip': ip,
        'success': success,
        'reason': reason,
        'timestamp': datetime.datetime.utcnow().isoformat()
    }
    logger.info(f"AUTH_AUDIT: {log_data}")


def add_security_headers(response):
    """Add security headers to response"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response
