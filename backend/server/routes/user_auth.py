from dotenv import load_dotenv
from flask import request, redirect, Blueprint, jsonify, url_for
from werkzeug.security import generate_password_hash
from werkzeug import Response
from ..utils import FRONTEND, COOKIE_AUTH, data_check, send_email, signature_check
from ..jwt import generate_token, decode_token, generate_confirmation_token, confirm_token
from ..models import User
from .. import session, blacklist
from ..config import Config

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

    message = (
        f"Subject: Confirm your email\n\n"
        f"Click this link to confirm your email {link}."
        f"If you didn't register for our website please ignore this email."
        f"\nBest regards,\nTorchED team"
    )
    send_email(email, "Potwierdź rejestrację, TorchED", message)
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


@user_auth.route('/confirm_email/<string:token>', methods=['GET'])
def confirm_email(token: str) -> tuple | Response:
    """
    Confirms user account with token provided in URL.
    Returns either a JSON response with status code or redirects to FRONTEND.
    """
    try:
        valid, email = confirm_token(token[:-3])
        if not valid:
            return jsonify({'error': 'Invalid token'}), 400
    except ValueError:
        return jsonify({'error': 'Server misconfigured: Missing salt or key'}), 500

    user: User | None = session.query(User).filter_by(email=email).first()
    if not user:
        return jsonify({'error': "Account you are trying to confirm doesn't exist"}), 400

    if user.confirmed:
        return jsonify({'error': 'Account already confirmed'}), 400

    user.confirmed = True
    session.add(user)
    session.commit()
    return redirect(FRONTEND)


@signature_check
@user_auth.route('/unregister/<int:iden>')
def delete_user(iden: int) -> Response:
    # Implementacja usuwania użytkownika
    ...
    return redirect(FRONTEND)
