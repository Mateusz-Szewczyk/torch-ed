import datetime
import hashlib
import json
import os
from typing import Dict, Any, Tuple, Union

from dotenv import load_dotenv
from flask import request, Blueprint, jsonify, send_file, Response
from sqlalchemy import text
from werkzeug.security import generate_password_hash, check_password_hash
from ..jwt import decode_token
from ..models import User
from .. import session
from ..config import Config
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
load_dotenv()

user_info: Blueprint = Blueprint('user_info', __name__)

# Konfiguracja z Config class
COOKIE_AUTH = 'TorchED_auth'


def get_user_from_token() -> Tuple[Union[User, None], Dict[str, Union[str, int]]]:
    """
    Helper function to get user from JWT token.
    Returns tuple (User | None, error_response)
    Accepts token from Cookie or Authorization header (Bearer token)
    """
    try:
        # Get token from cookie first, then fall back to Authorization header
        token = request.cookies.get(COOKIE_AUTH, None)

        if not token:
            # Try Authorization header (Bearer token) for web clients
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]  # Remove 'Bearer ' prefix

        if not token:
            return None, {'error': 'Not authenticated', 'code': 401}

        # Decode token using public key
        try:
            decoded_data = decode_token(token.encode('utf-8'), Config.PUP_PATH)
        except Exception as e:
            logger.error(f"Token decode error: {e}")
            return None, {'error': 'Invalid token', 'code': 401}

        if not decoded_data:
            return None, {'error': 'Token verification failed', 'code': 401}

        # Get user_id from token (stored in 'aud' field)
        user_id = decoded_data.get('aud')
        if not user_id:
            return None, {'error': 'Invalid token payload', 'code': 401}

        # Check if user exists in database
        user = session.query(User).filter_by(id_=user_id).first()
        if not user:
            return None, {'error': 'User not found', 'code': 404}

        if not user.confirmed:
            return None, {'error': 'Account not confirmed', 'code': 403}

        # Verify token issuer
        iss = decoded_data.get('iss')
        if iss != 'TorchED_BACKEND_AUTH':
            return None, {'error': 'Invalid token issuer', 'code': 401}

        return user, {}

    except Exception as e:
        logger.error(f"Error in get_user_from_token: {e}")
        return None, {'error': 'Authentication failed', 'code': 500}


@user_info.route('/profile', methods=['GET', 'PUT'])
def user_profile() -> Union[Response, Tuple[Response, int]]:
    """
    GET: Gets user profile information
    PUT: Updates user profile (username)
    """
    try:
        user, error = get_user_from_token()
        if error:
            return jsonify({'error': error['error']}), error['code']

        if request.method == 'GET':
            # Return profile information
            join_date = None
            if hasattr(user, 'created_at') and user.created_at:
                join_date = user.created_at.strftime('%Y-%m-%d')

            return jsonify({
                'success': True,
                'user': {
                    'id': user.id_,
                    'email': user.email,
                    'username': user.user_name,
                    'role': user.role,
                    'confirmed': user.confirmed,
                    'joinDate': join_date
                }
            }), 200

        elif request.method == 'PUT':
            # Update profile
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400

            username = data.get('username', '').strip()
            if not username:
                return jsonify({'error': 'Username cannot be empty'}), 400

            if len(username) < 3:
                return jsonify({'error': 'Username must be at least 3 characters long'}), 400

            if len(username) > 50:
                return jsonify({'error': 'Username must be less than 50 characters'}), 400

            # Check if username is already taken
            existing_user = session.query(User).filter(
                User.user_name == username,
                User.id_ != user.id_
            ).first()

            if existing_user:
                return jsonify({'error': 'Username already taken'}), 400

            # Update username
            session.execute(
                text("UPDATE users SET user_name = :username WHERE id_ = :user_id"),
                {"username": username, "user_id": user.id_}
            )
            session.commit()

            logger.info(f"Username updated for user {user.id_}: {username}")

            return jsonify({
                'success': True,
                'message': 'Username updated successfully',
                'username': username
            }), 200

    except Exception as e:
        session.rollback()
        logger.error(f"Error in user_profile: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@user_info.route('/change-password', methods=['POST'])
def change_password() -> Union[Response, Tuple[Response, int]]:
    """
    Changes user password after verifying current password.
    """
    try:
        user, error = get_user_from_token()
        if error:
            return jsonify({'error': error['error']}), error['code']

        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        current_password = data.get('currentPassword')
        new_password = data.get('newPassword')

        if not all([current_password, new_password]):
            return jsonify({'error': 'Current password and new password are required'}), 400

        # Verify current password
        if not check_password_hash(user.password, current_password):
            return jsonify({'error': 'Current password is incorrect'}), 400

        # Validate new password
        if len(new_password) < 8:
            return jsonify({'error': 'New password must be at least 8 characters long'}), 400

        # Check password requirements
        if not any(c.islower() for c in new_password):
            return jsonify({'error': 'Password must contain at least one lowercase letter'}), 400

        if not any(c.isupper() for c in new_password):
            return jsonify({'error': 'Password must contain at least one uppercase letter'}), 400

        if not any(c.isdigit() for c in new_password):
            return jsonify({'error': 'Password must contain at least one digit'}), 400

        if not any(c in '!@#$%^&*(),.?":{}|<>' for c in new_password):
            return jsonify({'error': 'Password must contain at least one special character'}), 400

        # Check if new password is different from current
        if check_password_hash(user.password, new_password):
            return jsonify({'error': 'New password cannot be the same as current password'}), 400

        # Hash new password with same salt_length as in registration
        hashed_password = generate_password_hash(new_password, salt_length=24)

        # Update password in database
        session.execute(
            text("UPDATE users SET password = :password WHERE id_ = :user_id"),
            {"password": hashed_password, "user_id": user.id_}
        )
        session.commit()

        logger.info(f"Password changed for user {user.id_}")

        return jsonify({
            'success': True,
            'message': 'Password changed successfully'
        }), 200

    except Exception as e:
        session.rollback()
        logger.error(f"Error in change_password: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@user_info.route('/export-data', methods=['GET'])
def export_user_data() -> Union[Response, Tuple[Response, int]]:
    """
    Exports user data in JSON format.
    """
    try:
        user, error = get_user_from_token()
        if error:
            return jsonify({'error': error['error']}), error['code']

        # Collect all user data
        user_data = {
            'profile': {
                'id': user.id_,
                'username': user.user_name,
                'email': user.email,
                'role': user.role,
                'confirmed': user.confirmed,
                'age': user.age,
                'created_at': user.created_at.isoformat() if hasattr(user, 'created_at') and user.created_at else None,
                'export_date': datetime.datetime.utcnow().isoformat()
            },
            'metadata': {
                'export_version': '1.0',
                'export_timestamp': datetime.datetime.utcnow().isoformat(),
                'data_format': 'JSON'
            }
        }

        # Create temporary file
        export_filename = f"user_data_export_{user.id_}_{int(datetime.datetime.utcnow().timestamp())}.json"
        temp_dir = '/tmp' if os.name != 'nt' else os.environ.get('TEMP', '.')
        file_path = os.path.join(temp_dir, export_filename)

        # Save data to file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Data export created for user {user.id_}")

        # Return file as download
        return send_file(
            file_path,
            as_attachment=True,
            download_name=export_filename,
            mimetype='application/json'
        )

    except Exception as e:
        logger.error(f"Error in export_user_data: {e}")
        return jsonify({'error': 'Failed to export data'}), 500


@user_info.route('/delete-account', methods=['DELETE'])
def delete_account() -> Union[Response, Tuple[Response, int]]:
    """
    Deletes user account and all associated data.
    """
    try:
        user, error = get_user_from_token()
        if error:
            return jsonify({'error': error['error']}), error['code']

        data = request.get_json()
        confirmation = data.get('confirmation') if data else None

        # Require deletion confirmation
        if confirmation not in ['USUŃ KONTO', 'DELETE ACCOUNT']:
            return jsonify({'error': 'Account deletion not confirmed properly'}), 400

        user_id = user.id_
        user_email = user.email

        try:
            session.execute(
                text("DELETE FROM password_reset_tokens WHERE user_id = :user_id"),
                {"user_id": user_id}
            )
            user_to_delete = session.query(User).filter_by(id_=user_id).first()
            if user_to_delete:
                session.delete(user_to_delete)

            session.commit()

            logger.info(f"Account deleted for user {user_id} (email: {user_email})")

            # Create response with cleared cookie
            resp = jsonify({
                'success': True,
                'message': 'Account deleted successfully'
            })

            # Clear authentication cookie
            resp.set_cookie(
                COOKIE_AUTH,
                '',
                expires=0,
                httponly=True,
                secure=Config.IS_SECURE,
                path='/',
                domain=Config.DOMAIN,
                samesite='None' if Config.IS_SECURE else 'Lax'
            )

            return resp, 200

        except Exception as db_error:
            session.rollback()
            logger.error(f"Database error during account deletion: {db_error}")
            return jsonify({'error': 'Failed to delete account from database'}), 500

    except Exception as e:
        session.rollback()
        logger.error(f"Error in delete_account: {e}")
        return jsonify({'error': 'Internal server error'}), 500
