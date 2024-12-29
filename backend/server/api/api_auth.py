import os
import hmac
import hashlib
from flask import Blueprint, request, jsonify
from ..jwt import generate_token


auth: Blueprint = Blueprint(
    name='api_auth',
    import_name=__name__,
)

@auth.route('/token', methods=['POST'])
def get_token() -> dict | tuple:
    data: dict | None = request.get_json()
    token: str
    key: str | None = os.getenv('SIGNATURE')
    messege: str | None = os.getenv('MESSAGE')
    
    if not key or not messege:
        return jsonify({ 'error': 'Server misconfiguration' }), 500
    
    key_bytes: bytes = key.encode('utf-8')
    messege_bytes: bytes = messege.encode('utf-8')
    signature: str = request.headers.get('TorchED-S', '')
    expected_signature: str = hmac.new(key_bytes, messege_bytes, hashlib.sha256).hexdigest()
    print(expected_signature)
    if not hmac.compare_digest(signature, expected_signature):
        return jsonify({ 'error': 'Unauthorized'}), 401
    
    if data and (user_id := data.get('user_id')) and (role := data.get('role')):
        iss: str = data.get('iss', 'Anonymus')
        try:
            token_bytes: bytes = generate_token(user_id, role, iss=iss, path=os.getenv('PRP_PATH', ''))            
            token = token_bytes.decode('utf-8')
        except Exception as e:
            return jsonify({'error': "Token generation failed: ", 'details': str(e)}), 500
    else:
        return jsonify({'Error': 'Invalid data'}), 400        
    return jsonify({'Token': token}), 200
