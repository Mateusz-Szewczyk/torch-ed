import os
import hmac
import hashlib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from flask import Request, jsonify, request
import smtplib

from flask.cli import load_dotenv
from werkzeug.security import check_password_hash
from functools import wraps
from typing import Callable
from .models import User
from . import session
from .config import Config

load_dotenv()

FRONTEND: str = os.getenv('FRONTEND', 'https://torched.pl')
COOKIE_AUTH: str = 'TorchED_AUTH'
EMAIL: str | None = os.getenv('EMAIL')
EMAIL_PASSWORD: str | None = os.getenv('EMAIL_PASSWORD')


class Misconfiguration(Exception):
    pass


def data_check(request: Request, method: str) -> tuple | dict:
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
        # print(expected_signature)
        if not hmac.compare_digest(signature, expected_signature):
            return jsonify({'error': 'Unauthorized'}), 401
        
        return func(*args, **kwargs)
    
    return wraper


def send_email(to: str, subject: str, message: str, html: bool = False) -> None:
    """
    Wysyła e-mail za pomocą Gmaila.

    :param to: Adres e-mail odbiorcy
    :param subject: Temat wiadomości
    :param message: Treść wiadomości
    :param html: Czy wiadomość jest w formacie HTML (domyślnie False)
    """
    try:
        # Sprawdzenie konfiguracji e-maila
        if not EMAIL or not EMAIL_PASSWORD:
            raise ValueError("Email or password not provided.")

        # Utworzenie wiadomości MIME
        msg = MIMEMultipart()
        msg['From'] = EMAIL
        msg['To'] = to
        msg['Subject'] = subject

        # Dołączenie treści wiadomości w odpowiednim formacie
        msg.attach(MIMEText(message, 'html' if html else 'plain'))

        # Połączenie z serwerem SMTP
        with smtplib.SMTP('smtp.gmail.com', 587) as connection:
            connection.starttls()  # Rozpoczęcie szyfrowanego połączenia
            connection.login(EMAIL, EMAIL_PASSWORD)  # Logowanie do konta
            connection.send_message(msg)  # Wysłanie wiadomości

        print(f"Email sent successfully to {to}")

    except smtplib.SMTPAuthenticationError:
        print("Error: Authentication failed. Check your email and password.")
    except smtplib.SMTPConnectError:
        print("Error: Unable to connect to the SMTP server.")
    except ValueError as ve:
        print(f"Configuration error: {ve}")
    except Exception as e:
        print(f"An unexpected error occurred while sending email to {to}: {e}")
