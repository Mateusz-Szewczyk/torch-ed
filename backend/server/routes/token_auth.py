import os
from flask import Blueprint, request, jsonify
from ..jwt import generate_token
from ..utils import signature_check


auth: Blueprint = Blueprint(
    name='api_auth',
    import_name=__name__,
)


@signature_check
@auth.route('/token', methods=['POST'])
def get_token() -> dict | tuple:
    data: dict | None = request.get_json()
    token: str
    
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
