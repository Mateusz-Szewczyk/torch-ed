from dotenv import load_dotenv
from flask import request, redirect, Blueprint, jsonify, url_for
from werkzeug.security import generate_password_hash
from werkzeug import Response
from ..utils import FRONTEND, COOKIE_AUTH, data_check, send_email, signature_check
from ..jwt import generate_token, decode_token
from ..models import User
from .. import session, blacklist
from ..jwt import generate_confirmation_token, confirm_token
from ..config import Config

load_dotenv()
user_auth: Blueprint = Blueprint('auth', __name__)


@user_auth.route('/me', methods=['GET'])
def me():
    """
    Check if user is logged in.
    :return: JSON with logged_in status
    """
    token = request.cookies.get(COOKIE_AUTH)
    if not token:
        return jsonify({"logged_in": False}), 401

    token_data = decode_token(token.encode('utf-8'), path=Config.PRP_PATH)
    if not token_data:
        return jsonify({"logged_in": False}), 401

    # If decode is successful
    return jsonify({
        "logged_in": True,
        "user_id": token_data["aud"],
    })


@user_auth.route('/login', methods=['POST'])
def login() -> Response | tuple:
    '''
    Creates token and puts it in cookie.

    Function takes incoming request and looks for
    - 'user_name'
    and
    - 'password'.
    Then checks if user with these credentials is in our database, if he is then,
    it creates cookie with token that is used by frontend for authorization.

    Returns:
        - Response with redirection and cookie
    '''
    if request.cookies.get(COOKIE_AUTH, None):
        return jsonify({'error': 'To log in you must first logout'}), 423
    data = data_check(request, 'login')
    if isinstance(data, tuple):
        return data

    user = data.get('user')
    path = data.get('path')
    if not user or not path:
        return jsonify({'error': 'Misconfiguration "user_auth | def login"'}), 500
    token_bytes = generate_token(user_id=user.id_, role=user.role, iss='TorchED_BACKEND_AUTH', path=path)
    token = token_bytes.decode('utf-8')
    response = jsonify({'success': True, 'message': 'Logged in'})
    response.set_cookie(COOKIE_AUTH, token, samesite='None',  max_age=60 * 60 * 24, httponly=True, secure=False)

    return response


@user_auth.route('/register', methods=['POST'])
def register() -> Response | str | tuple:
    '''
    Add new user to database.

    To add new user, the request must have:
         - user_name,
         - password,
         - password2,
         - email,
         - age (optional)
         - role (optional, by default 'user')
    After verification user is created and verifying email is sent.

    Returns
    Tuple with information about what happened and html status code

    '''
    data = data_check(request, 'register')
    if isinstance(data, tuple):
        return data
    key_words = ['user_name', 'password', 'email', 'age', 'role']
    if not isinstance(data, dict) or not all(key in data for key in key_words):
        return jsonify({'error': 'Misconfiguration "user_auth | def register"'}), 400
    if not (password := data.get('password')) or not isinstance(password, str):
        return jsonify({'error': 'Please provide password'}), 400
    if not isinstance(email := data.get('email'), str):
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
        return jsonify(
            {'error': 'Something went wrong while generating confirmation email, please try again later'}), 500

    session.add(user)
    session.commit()
    link = url_for('auth.confirm_email', token=token, _external=True)

    message = f"Subject: Confirm your email\n\n" \
              f"Click this link to confirm your email {link}." \
              f"If you didn't register for our website please ignore this email." \
              f"\nBest regards,\nTorchED team"

    send_email(email, message)

    return jsonify({'Success': 'User has been successfully created!'}), 201


@user_auth.route('/logout', methods=['GET'])
def logout() -> Response | tuple:
    '''
    Deletes cookie and puts token from it to blacklist.

    Function deletes cookie that should contain authorization token.
    Then for 24h (basic life of token), puts it on blacklist maintained in redis

    Returns:
        Response with redirection that deletes cookie
        And
        Adds token in format:
        {token: {user_id: iss}}
        to the redis blacklist database.
    '''
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
        return jsonify({'error': f'Token does\'t contain {e} field'}), 400

    if not blacklist.hexists(user_id, 'tokens'):
        blacklist.hset(
            token,
            user_id,
            iss
        )
        blacklist.expire(token, 60 * 60 * 24)
    print(blacklist.ttl(token))
    response = jsonify({'success': True, 'message': 'Successfully logged out'})
    response.set_cookie(COOKIE_AUTH, max_age=0)

    return response


# TODO: Delete user
@user_auth.route('/confirm_email/<string:token>', methods=['GET'])
def confirm_email(token: str) -> tuple | Response:
    '''
    Confirms user account with token within url.

    Returns:
        - tuple containing json response and html status code
        - response that redirects to FRONTEND (contained in utils.py)
    '''
    try:
        # Remove the extra '.if' from the token
        email = confirm_token(token[:-3])
        if not email:
            return jsonify({'error': 'Invalid token'}), 400
    except ValueError:
        return jsonify({'error': 'Server misconfigured: Missing salt or key'}), 500

    user: User | None = session.query(User).filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'Account you are trying to confirm doesn\'t exist'}), 400

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