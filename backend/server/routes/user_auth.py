from dotenv import load_dotenv
from flask import request, redirect, Blueprint, jsonify, url_for
from werkzeug.security import generate_password_hash
from werkzeug import Response
from ..utils import FRONTEND, COOKIE_AUTH, data_check, send_email, signature_check
from ..jwt import generate_token, decode_token, generate_confirmation_token, confirm_token
from ..models import User
from .. import session, blacklist
from ..config import Config
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
load_dotenv()
user_auth: Blueprint = Blueprint('auth', __name__)


@user_auth.route('/login', methods=['POST', 'GET'])
def login() -> Response | tuple:
    """
    Creates token and puts it in cookie.
    Function takes incoming request and looks for:
      - 'user_name'
      - 'password'
    Then checks if user with these credentials exists in our database.
    If so, creates a cookie with the token used for authorization.
    """
    is_logged = request.cookies.get(COOKIE_AUTH, None)

    if is_logged:
        return jsonify({'success': True, 'message': 'Logged in'})

    data = data_check(request, 'login')
    if isinstance(data, tuple):
        return data

    user = data.get('user')
    path = data.get('path')
    if not user or not path:
        return jsonify({'error': 'Misconfiguration "user_auth | def login"'}), 500

    token_bytes = generate_token(user_id=user.id_, role=user.role, iss='TorchED_BACKEND_AUTH', path=path)
    token = token_bytes.decode('utf-8')
    resp = jsonify({'success': True, 'message': 'Logged in'})
    resp.set_cookie(
        COOKIE_AUTH,
        token,
        samesite='None',
        max_age=60 * 60 * 24 * 5,
        httponly=True,
        secure=Config.IS_SECURE,
        path='/',
        domain=Config.DOMAIN
    )
    return resp


@user_auth.route('/register', methods=['POST'])
def register() -> Response | str | tuple:
    """
    Add new user to database.
    Request must include:
      - user_name,
      - password,
      - password2,
      - email,
      - age (optional),
      - role (optional, default 'user')
    After verification, user is created and a confirmation email is sent.
    """
    data = data_check(request, 'register')
    if isinstance(data, tuple):
        return data

    key_words = ['user_name', 'password', 'email', 'age', 'role']
    if not isinstance(data, dict) or not all(key in data for key in key_words):
        return jsonify({'error': 'Misconfiguration "user_auth | def register"'}), 400

    password = data.get('password')
    if not password or not isinstance(password, str):
        return jsonify({'error': 'Please provide password'}), 400

    email = data.get('email')
    if not isinstance(email, str):
        return jsonify({'error': 'Invalid email'}), 400

    user = User(
        user_name=data.get('user_name'),
        password=generate_password_hash(password, salt_length=24),
        email=email,
        role=data.get('role'),
        age=data.get('age')
    )

    token = generate_confirmation_token(email)
    if not token:
        return jsonify({'error': 'Something went wrong while generating confirmation email, please try again later'}), 500

    session.add(user)
    session.commit()
    link = url_for('auth.confirm_email', token=token, _external=True)

    # HTML email content
    message = f"""
    <html>
      <head>
        <style>
          body {{ font-family: Arial, sans-serif; color: #333; line-height: 1.6; background-color: #f4f4f4; padding: 20px; }}
          .container {{ max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
          .header {{ text-align: center; padding: 20px 0; }}
          .header img {{ max-width: 150px; }}
          .content {{ padding: 20px; }}
          .button {{ display: inline-block; padding: 12px 24px; background-color: #007bff; color: #ffffff; text-decoration: none; border-radius: 5px; font-weight: bold; }}
          .button:hover {{ background-color: #0056b3; }}
          .footer {{ text-align: center; font-size: 12px; color: #777; margin-top: 20px; }}
        </style>
      </head>
      <body>
        <div class="container">
          <div class="header">
            <h1>Witaj w TorchED!</h1>
          </div>
          <div class="content">
            <p>Dziękujemy za rejestrację w TorchED! Jesteśmy podekscytowani, że dołączasz do naszej społeczności.</p>
            <p>Aby aktywować swoje konto, kliknij w poniższy przycisk:</p>
            <p style="text-align: center;">
              <a href="{link}" class="button">Potwierdź swoje konto</a>
            </p>
            <p>Jeśli przycisk nie działa, skopiuj i wklej ten link do przeglądarki:</p>
            <p><a href="{link}">{link}</a></p>
            <p>Jeśli nie rejestrowałeś się w TorchED, możesz zignorować tę wiadomość.</p>
            <p>Cieszymy się na współpracę z Tobą i mamy nadzieję, że pokochasz korzystanie z naszej aplikacji!</p>
            <p>Zespół TorchED</p>
          </div>
          <div class="footer">
            <p>Masz pytania? Skontaktuj się ze mną: <a href="mailto:mateusz.szewczyk000@gmail.com">mateusz.szewczyk000@gmail.com</a></p>
            <p>&copy; 2025 TorchED. Wszystkie prawa zastrzeżone.</p>
          </div>
        </div>
      </body>
    </html>
    """

    send_email(email, "Potwierdź rejestrację w TorchED", message, html=True)
    return jsonify({'Success': 'User has been successfully created!'}), 201

@user_auth.route('/logout', methods=['GET'])
def logout() -> Response | tuple:
    """
    Deletes cookie and puts token from it into blacklist.
    The token is blacklisted for 24 hours.
    """
    token = request.cookies.get(COOKIE_AUTH, None)
    if not token:
        return jsonify({'error': 'User not logged in'}), 400

    path = Config.PUP_PATH
    if not path:
        return jsonify({'error': 'Misconfiguration: user_auth | def logout'}), 500

    token_data = decode_token(token.encode('utf-8'), path)
    if not token_data:
        return jsonify({'error': 'Could not decode token'}), 406

    try:
        user_id = token_data['aud']
        iss = token_data['iss']
    except KeyError as e:
        return jsonify({'error': f"Token doesn't contain {e} field"}), 400

    # Check if token is already blacklisted under the user's hash key.
    if not blacklist.hexists(user_id, token):
        blacklist.hset(user_id, token, iss)
        blacklist.expire(user_id, 60 * 60 * 24)
    print(blacklist.ttl(user_id))

    resp = jsonify({'success': True, 'message': 'Successfully logged out'})
    resp.delete_cookie(
        COOKIE_AUTH,
        samesite='None',
        httponly=True,
        secure=Config.IS_SECURE,
        path='/',
        domain=Config.DOMAIN,
    )
    return resp


@user_auth.route('/confirm_email/<token>')
def confirm_email(token):
    """
    Confirm a user's email using the provided token.
    """
    try:
        valid, email = confirm_token(token)  # No token[:-3]
        if not valid or not email:
            logger.warning("Invalid or expired token: %s", token)
            return jsonify({'error': 'Invalid or expired confirmation token'}), 400

        user = session.query(User).filter_by(email=email).first()
        if not user:
            logger.warning("No user found for email: %s", email)
            return jsonify({'error': 'User not found'}), 404

        if user.confirmed:
            logger.info("User already confirmed: %s", email)
            return jsonify({'success': 'Email already confirmed'}), 200

        user.confirmed = True
        session.commit()
        logger.info("Email confirmed successfully for: %s", email)
        return jsonify({'success': 'Email confirmed successfully!'}), 200

    except Exception as e:
        logger.error("Error processing confirmation token: %s", e)
        return jsonify({'error': 'An unexpected error occurred'}), 500


@signature_check
@user_auth.route('/unregister/<int:iden>')
def delete_user(iden: int) -> Response:
    # Implementacja usuwania użytkownika
    ...
    return redirect(FRONTEND)
