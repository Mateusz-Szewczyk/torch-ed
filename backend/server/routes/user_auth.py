import json
import os
from dotenv import load_dotenv
from flask import request, redirect, Blueprint, make_response, jsonify
from werkzeug.security import generate_password_hash
from werkzeug import Response
from ..utils import FRONTEND, COOKIE_AUTH, data_check
from ..jwt import generate_token, decode_token
from ..models import User
from .. import session, blacklist


load_dotenv()
auth: Blueprint = Blueprint('auth', __name__)


@auth.route('/login', methods=['POST'])
def login() -> Response | tuple:
    '''
    Creates token and puts it int cookie.
    
    Function takes incoming request and looks for
    - 'user_name'
    and 
    - 'password'.
    Then checks if user with these credentials is in our database, if he is then,
    it creates cookie with token that is used by frontend for authorization.
    
    Returns:
        - Response with redirection and cookie
    '''
    path: str | None
    # data: dict | None
    data: tuple | dict
    user: User | None 
    token: str
    token_bytes: bytes
    response: Response

    if request.cookies.get(COOKIE_AUTH, None):
        return jsonify({ 'error': 'To log in you must first logout' }), 423
    data = data_check(request, 'login')
    if isinstance(data, tuple):
        return data
    
    user = data.get('user')
    path = data.get('path')
    if not user or not path:
        return jsonify({'error': 'Misconfiguration "user_auth | def login"'}), 500
    token_bytes = generate_token(user_id=user.id_, role=user.role, iss='TorchED_BACKEND_AUTH', path=path)
    token = token_bytes.decode('utf-8')
    response = make_response(redirect(FRONTEND))
    response.set_cookie(COOKIE_AUTH, token, max_age=60*60*24, httponly=True, secure=True)
    
    return response
    

@auth.route('/register', methods=['POST'])
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
    After verifycation user is created.
    
    Returns
    Tuple with information about what happend and html status code
    '''
    data: dict | tuple
    user: User
  
    
    data = data_check(request, 'register')
    if isinstance(data, tuple):
        return data
    key_words: list[str] = ['user_name', 'password', 'email', 'age', 'role']
    if not isinstance(data, dict) or not all(key in data for key in key_words):
        return jsonify({'error': 'Misconfiguration "user_auth | def register"'})
    if not (password := data.get('password')) or not isinstance(password, str):
        return jsonify({'error': 'Please provide password'})
    user = User(
        user_name=data.get('user_name'),
        password=generate_password_hash(password, salt_length=24),
        email=data.get('email'),
        role=data.get('role'),
        age=data.get('age')
    )    
    session.add(user)
    session.commit()

    return jsonify({'Success': 'User has been successfuly created!'}), 201
    

@auth.route('/logout', methods=['GET'])
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
    token: None | str | bytes
    if not (token := request.cookies.get(COOKIE_AUTH, None)):
        return jsonify({'error': 'User not logged in'}), 400

    if not (path := os.getenv('PUP_PATH', None)):
        return jsonify({'error': 'Misconfiguration: user_auth | def logout'}), 500 
    
    token_data: dict | None = decode_token(token.encode('utf-8'), path)
    
    if not token_data:
        return jsonify({'error', 'Could not decode token'}), 406

    user_id: str
    iss: str
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
        blacklist.expire(token, 60*60*24)
    print(blacklist.ttl(token))
    response: Response = make_response(redirect(FRONTEND))
    response.set_cookie(COOKIE_AUTH, max_age=0)
    
    return response


# TODO: Delete user
