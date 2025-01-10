
from flask import Blueprint, request, jsonify
from ..jwt import generate_token
from ..utils import signature_check
from ..config import Config
api_auth = Blueprint(
    name='api_auth',
    import_name=__name__,
)

@signature_check
@api_auth.route('/token', methods=['POST'])
def get_token() -> dict | tuple:
    data = request.get_json()
    if data and (user_id := data.get('user_id')) and (role := data.get('role')):
        iss = data.get('iss', 'Anonymous')
        try:
            # Użyj Config.PRP_PATH do wskazania ścieżki klucza prywatnego
            token_bytes = generate_token(user_id=user_id, role=role, iss=iss, path=Config.PRP_PATH)
            token = token_bytes.decode('utf-8')
        except Exception as e:
            return jsonify({'error': "Token generation failed", 'details': str(e)}), 500
    else:
        return jsonify({'Error': 'Invalid data'}), 400        
    return jsonify({'Token': token}), 200
