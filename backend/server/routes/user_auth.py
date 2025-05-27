import datetime
import hashlib
import re
import secrets
import os

from dotenv import load_dotenv
from flask import request, redirect, Blueprint, jsonify, url_for
from sqlalchemy import text
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug import Response
from ..jwt import generate_token, decode_token, generate_confirmation_token, confirm_token
from ..models import User
from .. import session
from ..config import Config
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
load_dotenv()

user_auth: Blueprint = Blueprint('auth', __name__)

# Konfiguracja z Config class
FRONTEND = os.getenv('FRONTEND_URL', 'http://localhost:3000')
COOKIE_AUTH = 'TorchED_auth'


def normalize_datetime(dt):
    """
    Konwertuje datetime do naive UTC datetime dla consistent porównań.
    """
    if dt is None:
        return None

    if isinstance(dt, str):
        try:
            if 'T' in dt and ('+' in dt or 'Z' in dt):
                dt = datetime.datetime.fromisoformat(dt.replace('Z', '+00:00'))
            else:
                dt = datetime.datetime.fromisoformat(dt)
        except ValueError:
            dt = datetime.datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')

    if hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
        dt = dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)

    return dt


@user_auth.route('/login', methods=['POST', 'GET'])
def login() -> Response | tuple:
    """
    Creates token and puts it in cookie.
    """
    # Check if already logged in
    is_logged = request.cookies.get(COOKIE_AUTH, None)
    if is_logged:
        try:
            decoded_data = decode_token(is_logged.encode('utf-8'), Config.PUP_PATH)
            if decoded_data:
                return jsonify({'success': True, 'message': 'Already logged in'})
        except:
            pass  # Token invalid, continue with login

    if request.method == 'GET':
        return jsonify({'authenticated': False, 'message': 'Not logged in'}), 401

    # POST request - handle login
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    email = data.get('user_name') or data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    # Find user by email
    user = session.query(User).filter_by(email=email.lower().strip()).first()
    if not user:
        return jsonify({'error': 'Invalid credentials'}), 400

    # Verify password
    if not check_password_hash(user.password, password):
        return jsonify({'error': 'Invalid credentials'}), 400

    # Check if account is confirmed
    if not user.confirmed:
        return jsonify({
            'error': 'Account not confirmed. Please check your email.',
            'is_confirmed': False
        }), 423

    # Generate JWT token using private key
    try:
        token_bytes = generate_token(
            user_id=user.id_,
            role=user.role,
            iss='TorchED_BACKEND_AUTH',
            path=Config.PRP_PATH
        )
        token = token_bytes.decode('utf-8')
    except Exception as e:
        logger.error(f"Token generation failed: {e}")
        return jsonify({'error': 'Authentication failed'}), 500

    resp = jsonify({
        'success': True,
        'message': 'Logged in successfully',
        'is_confirmed': user.confirmed
    })

    resp.set_cookie(
        COOKIE_AUTH,
        token,
        samesite='None',
        max_age=60 * 60 * 24 * 5,  # 5 days
        httponly=True,
        secure=Config.IS_SECURE,
        path='/',
        domain=Config.DOMAIN
    )
    return resp


@user_auth.route('/register', methods=['POST'])
def register() -> Response | tuple:
    """
    Add new user to database with email confirmation.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        required_fields = ['user_name', 'password', 'password2', 'email']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'{field} is required'}), 400

        email = data['email'].lower().strip()
        password = data['password']
        password2 = data['password2']
        user_name = data['user_name'].strip()

        # Validate password match
        if password != password2:
            return jsonify({'error': 'Passwords do not match'}), 400

        # Password validation regexes (zgodne z frontendem)
        if len(password) < 8:
            return jsonify({'error': 'Hasło musi mieć co najmniej 8 znaków.'}), 400
        if not re.search(r'[a-z]', password):
            return jsonify({'error': 'Hasło musi zawierać co najmniej jedną małą literę (a-z).'}), 400
        if not re.search(r'[A-Z]', password):
            return jsonify({'error': 'Hasło musi zawierać co najmniej jedną dużą literę (A-Z).'}), 400
        if not re.search(r'[0-9]', password):
            return jsonify({'error': 'Hasło musi zawierać co najmniej jedną cyfrę (0-9).'}), 400
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return jsonify({'error': 'Hasło musi zawierać co najmniej jeden znak specjalny (!@#$%^&*(),.?":{}|<>).'}), 400

        # Check if user already exists
        existing_user = session.query(User).filter_by(email=email).first()
        if existing_user:
            return jsonify({'error': 'User with this email already exists'}), 400

        # Create new user
        user = User(
            user_name=user_name,
            password=generate_password_hash(password, salt_length=24),
            email=email,
            role=data.get('role', 'user'),
            age=data.get('age', 0),
            confirmed=False
        )

        # Generate confirmation token
        token = generate_confirmation_token(email)
        if not token:
            return jsonify({'error': 'Failed to generate confirmation token'}), 500

        session.add(user)
        session.commit()

        # Create confirmation link
        confirmation_link = url_for('auth.confirm_email', token=token, _external=True)

        # Enhanced email template (jak poprzednio)
        message = f"""
        <html>
          <head>
            <style>
              body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; color: #1a1a1a; background: #f8fafc; padding: 20px; }}
              .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
              .header {{ background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); color: white; padding: 30px 20px; text-align: center; }}
              .content {{ padding: 30px 20px; }}
              .button {{ display: inline-block; padding: 14px 28px; background: #4f46e5; color: white !important; text-decoration: none; border-radius: 8px; font-weight: 600; }}
              .footer {{ background: #f8fafc; padding: 20px; text-align: center; color: #64748b; font-size: 14px; }}
            </style>
          </head>
          <body>
            <div class="container">
              <div class="header">
                <h1>🎉 Witaj w TorchED!</h1>
                <p>Potwierdź swoje konto</p>
              </div>
              <div class="content">
                <p>Cześć {user_name}!</p>
                <p>Dziękujemy za rejestrację w TorchED. Aby aktywować swoje konto, kliknij przycisk poniżej:</p>
                <div style="text-align: center; margin: 30px 0;">
                  <a href="{confirmation_link}" class="button">✨ Potwierdź konto</a>
                </div>
                <p style="font-size: 14px; color: #64748b;">
                  Jeśli przycisk nie działa, skopiuj ten link:<br>
                  <a href="{confirmation_link}">{confirmation_link}</a>
                </p>
              </div>
              <div class="footer">
                <p>© 2025 TorchED. Wiadomość wysłana automatycznie.</p>
              </div>
            </div>
          </body>
        </html>
        """

        # Send confirmation email (assuming send_email function exists)
        # send_email(email, "Potwierdź rejestrację w TorchED", message, html=True)

        return jsonify({
            'success': True,
            'message': 'User registered successfully. Please check your email for confirmation.'
        }), 201

    except Exception as e:
        session.rollback()
        logger.error(f"Error in register: {e}")
        return jsonify({'error': 'Registration failed. Please try again.'}), 500


@user_auth.route('/logout', methods=['GET'])
def logout() -> Response | tuple:
    """
    Logs out user by clearing cookie and optionally blacklisting token.
    """
    token = request.cookies.get(COOKIE_AUTH, None)
    if not token:
        return jsonify({'error': 'User not logged in'}), 400

    # Verify token before logout
    try:
        decoded_data = decode_token(token.encode('utf-8'), Config.PUP_PATH)
        if decoded_data:
            user_id = decoded_data.get('aud')
            logger.info(f"User {user_id} logged out successfully")
    except Exception as e:
        logger.warning(f"Token verification during logout failed: {e}")

    # Clear cookie
    resp = jsonify({'success': True, 'message': 'Successfully logged out'})
    resp.set_cookie(
        COOKIE_AUTH,
        '',
        expires=0,
        httponly=True,
        secure=Config.IS_SECURE,
        path='/',
        domain=Config.DOMAIN,
        samesite='None'
    )
    return resp


@user_auth.route('/confirm_email/<token>', methods=['GET'])
def confirm_email(token: str) -> tuple[Response, int] | Response:
    """
    Confirms user email using token.
    """
    try:
        is_valid, email = confirm_token(token)

        if not is_valid or not email:
            return jsonify({'error': 'Invalid or expired confirmation token'}), 400

        user = session.query(User).filter_by(email=email).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        if user.confirmed:
            return jsonify({'message': 'Email already confirmed'}), 200

        user.confirmed = True
        session.commit()

        logger.info(f"Email confirmed for user: {email}")
        return redirect(FRONTEND)

    except Exception as e:
        session.rollback()
        logger.error(f"Error in confirm_email: {e}")
        return jsonify({'error': 'Email confirmation failed'}), 500


@user_auth.route('/forgot-password', methods=['POST'])
def forgot_password() -> Response | tuple:
    """
    Sends password reset email.
    """
    try:
        data = request.get_json()
        if not data or not data.get('email'):
            return jsonify({'error': 'Email is required'}), 400

        email = data.get('email').strip().lower()

        # Find user
        user = session.query(User).filter_by(email=email).first()

        if user and user.confirmed:
            # Generate secure reset token
            reset_token = secrets.token_urlsafe(48)
            token_hash = hashlib.sha256(reset_token.encode()).hexdigest()

            # Use naive datetime for consistency
            expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=30)

            # Remove old tokens
            session.execute(
                text("DELETE FROM password_reset_tokens WHERE user_id = :user_id"),
                {"user_id": user.id_}
            )

            # Save new token
            session.execute(
                text(
                    "INSERT INTO password_reset_tokens (user_id, token_hash, expires_at) VALUES (:user_id, :token_hash, :expires_at)"
                ),
                {
                    "user_id": user.id_,
                    "token_hash": token_hash,
                    "expires_at": expires_at
                }
            )
            session.commit()

            # Create reset link
            reset_link = f"{FRONTEND}/reset-password?token={reset_token}"

            # Email template
            message = f"""
            <html>
              <head>
                <style>
                  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; color: #1a1a1a; background: #f8fafc; padding: 20px; }}
                  .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
                  .header {{ background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); color: white; padding: 30px 20px; text-align: center; }}
                  .content {{ padding: 30px 20px; }}
                  .button {{ display: inline-block; padding: 14px 28px; background: #4f46e5; color: white !important; text-decoration: none; border-radius: 8px; font-weight: 600; }}
                  .warning {{ background: #fef3c7; border: 1px solid #f59e0b; padding: 12px; border-radius: 6px; margin: 20px 0; color: #92400e; }}
                  .footer {{ background: #f8fafc; padding: 20px; text-align: center; color: #64748b; font-size: 14px; }}
                </style>
              </head>
              <body>
                <div class="container">
                  <div class="header">
                    <h1>🔒 Resetowanie hasła</h1>
                    <p>TorchED - Bezpieczne resetowanie</p>
                  </div>
                  <div class="content">
                    <p>Cześć!</p>
                    <p>Otrzymaliśmy prośbę o zresetowanie hasła do Twojego konta w TorchED.</p>
                    <div style="text-align: center; margin: 30px 0;">
                      <a href="{reset_link}" class="button">🔑 Zresetuj hasło</a>
                    </div>
                    <div class="warning">
                      <strong>⚠️ Ważne:</strong>
                      <ul style="margin: 8px 0 0 20px;">
                        <li>Link jest ważny przez <strong>30 minut</strong></li>
                        <li>Jeśli nie prosiłeś o reset, zignoruj tę wiadomość</li>
                        <li>Nie udostępniaj tego linku nikomu</li>
                      </ul>
                    </div>
                    <p style="font-size: 14px; color: #64748b; margin-top: 20px;">
                      Jeśli przycisk nie działa, skopiuj ten link:<br>
                      <a href="{reset_link}" style="color: #4f46e5; word-break: break-all;">{reset_link}</a>
                    </p>
                  </div>
                  <div class="footer">
                    <p>© 2025 TorchED. Wiadomość wysłana automatycznie.</p>
                  </div>
                </div>
              </body>
            </html>
            """

            # Send email (uncomment when send_email is available)
            # send_email(email, "🔒 Resetowanie hasła - TorchED", message, html=True)
            logger.info(f"Password reset email would be sent to: {email}")

        return jsonify({
            'success': True,
            'message': 'Jeśli podany email istnieje w naszej bazie, wysłaliśmy link do resetowania hasła.'
        }), 200

    except Exception as e:
        session.rollback()
        logger.error(f"Error in forgot_password: {e}")
        return jsonify({'error': 'Wystąpił błąd. Spróbuj ponownie później.'}), 500


@user_auth.route('/reset-password', methods=['POST'])
def reset_password() -> Response | tuple:
    """
    Resets password using token.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Brak danych'}), 400

        token = data.get('token')
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')

        if not all([token, new_password, confirm_password]):
            return jsonify({'error': 'Wszystkie pola są wymagane'}), 400

        if new_password != confirm_password:
            return jsonify({'error': 'Hasła nie są identyczne'}), 400

        if len(new_password) < 8:
            return jsonify({'error': 'Hasło musi mieć co najmniej 8 znaków'}), 400

        # Hash token for database lookup
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        # Find token in database
        result = session.execute(
            text("""
            SELECT prt.user_id, prt.expires_at, u.email 
            FROM password_reset_tokens prt 
            JOIN users u ON prt.user_id = u.id_ 
            WHERE prt.token_hash = :token_hash
            """),
            {"token_hash": token_hash}
        ).fetchone()

        if not result:
            return jsonify({'error': 'Token nieprawidłowy lub wygasł'}), 400

        user_id, expires_at, email = result

        # Normalize datetime for comparison
        current_time = datetime.datetime.utcnow()
        expires_at = normalize_datetime(expires_at)

        if current_time > expires_at:
            session.execute(
                text("DELETE FROM password_reset_tokens WHERE token_hash = :token_hash"),
                {"token_hash": token_hash}
            )
            session.commit()
            return jsonify({'error': 'Token wygasł. Poproś o nowy link.'}), 400

        # Update user password
        hashed_password = generate_password_hash(new_password, salt_length=24)
        session.execute(
            text("UPDATE users SET password = :password WHERE id_ = :user_id"),
            {"password": hashed_password, "user_id": user_id}
        )

        # Remove used token
        session.execute(
            text("DELETE FROM password_reset_tokens WHERE user_id = :user_id"),
            {"user_id": user_id}
        )

        session.commit()
        logger.info(f"Password reset successful for user {user_id}")

        return jsonify({
            'success': True,
            'message': 'Hasło zostało pomyślnie zmienione. Możesz się teraz zalogować.'
        }), 200

    except Exception as e:
        session.rollback()
        logger.error(f"Error in reset_password: {e}")
        return jsonify({'error': 'Wystąpił błąd. Spróbuj ponownie później.'}), 500


@user_auth.route('/session-check', methods=['GET'])
def session_check() -> Response | tuple:
    """
    Checks if user is logged in by verifying JWT token.
    """
    try:
        # Get token from cookie
        token = request.cookies.get(COOKIE_AUTH, None)
        if not token:
            return jsonify({'authenticated': False}), 401

        # Decode and verify token using public key
        try:
            decoded_data = decode_token(token.encode('utf-8'), Config.PUP_PATH)
        except Exception as e:
            logger.error(f"Token decode error: {e}")
            return jsonify({'authenticated': False, 'error': 'Invalid token'}), 401

        if not decoded_data:
            return jsonify({'authenticated': False, 'error': 'Token verification failed'}), 401

        # Get user_id from decoded token (stored in 'aud' field)
        user_id = decoded_data.get('aud')
        if not user_id:
            return jsonify({'authenticated': False, 'error': 'Invalid token payload'}), 401

        # Check if user still exists in database
        user = session.query(User).filter_by(id_=user_id).first()
        if not user:
            return jsonify({'authenticated': False, 'error': 'User not found'}), 401

        # Check account confirmation status
        if not user.confirmed:
            return jsonify({
                'authenticated': True,
                'user_id': user.id_,
                'email': user.email,
                'confirmed': False,
                'message': 'Account not confirmed'
            }), 200

        # Verify token issuer
        iss = decoded_data.get('iss')
        if iss != 'TorchED_BACKEND_AUTH':
            return jsonify({'authenticated': False, 'error': 'Invalid token issuer'}), 401

        # Return success with user information
        return jsonify({
            'authenticated': True,
            'user_id': user.id_,
            'email': user.email,
            'confirmed': user.confirmed,
            'role': user.role,
            'username': user.user_name
        }), 200

    except Exception as e:
        logger.error(f"Error in session_check: {e}")
        return jsonify({'authenticated': False}), 401
