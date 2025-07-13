import datetime
import hashlib
import re
import secrets
import os
import hmac
import time

from dotenv import load_dotenv
from flask import request, redirect, Blueprint, jsonify, url_for
from sqlalchemy import text
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug import Response
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import redis

from ..jwt import generate_token, decode_token, generate_confirmation_token, confirm_token
from ..models import User
from .. import session
from ..config import Config
from ..utils import send_email, FRONTEND
import logging

# Enhanced logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
load_dotenv()

# Redis setup for rate limiting and token blacklisting
redis_client = redis.from_url(
    os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    decode_responses=True,
    socket_connect_timeout=5,
    socket_timeout=5
)

# Rate limiter setup
limiter = Limiter(
    get_remote_address,
    storage_uri=f"{os.getenv('REDIS_URL', 'redis://localhost:6379/0')}",
    default_limits=["1000 per day", "100 per hour"]
)

user_auth: Blueprint = Blueprint('auth', __name__)

# Configuration
COOKIE_AUTH = 'TorchED_auth'
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = 300  # 5 minutes


def add_security_headers(response):
    """Add security headers to response"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response


def secure_compare(a, b):
    """Timing-safe string comparison"""
    return hmac.compare_digest(str(a), str(b))


def add_response_delay():
    """Add small delay to normalize response times"""
    time.sleep(0.1)


def validate_email(email):
    """Enhanced email validation"""
    if not email or len(email) > 254:
        return False
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_pattern, email) is not None


def sanitize_input(data):
    """Sanitize input data"""
    if isinstance(data, str):
        return data.strip()[:255]  # Limit length and remove whitespace
    return data


def log_auth_attempt(action, email, ip, success, reason=None):
    """Log authentication attempt for audit purposes"""
    log_data = {
        'action': action,
        'email': email,
        'ip': ip,
        'success': success,
        'reason': reason,
        'timestamp': datetime.datetime.utcnow().isoformat()
    }
    logger.info(f"AUTH_AUDIT: {log_data}")


def blacklist_token(token, exp_time):
    """Add token to Redis blacklist"""
    try:
        redis_client.setex(f"blacklist:{token}", exp_time, "1")
        logger.info(f"Token blacklisted successfully")
    except Exception as e:
        logger.error(f"Failed to blacklist token: {e}")


def is_token_blacklisted(token):
    """Check if token is in Redis blacklist"""
    try:
        return redis_client.exists(f"blacklist:{token}")
    except Exception as e:
        logger.error(f"Failed to check token blacklist: {e}")
        return False


def check_account_lockout(email):
    """Check if account is locked due to too many failed attempts"""
    try:
        lockout_key = f"lockout:{email}"
        attempts = redis_client.get(lockout_key)
        return int(attempts or 0) >= MAX_LOGIN_ATTEMPTS
    except Exception as e:
        logger.error(f"Failed to check account lockout: {e}")
        return False


def increment_failed_attempts(email):
    """Increment failed login attempts counter"""
    try:
        lockout_key = f"lockout:{email}"
        current_attempts = redis_client.incr(lockout_key)
        redis_client.expire(lockout_key, LOCKOUT_DURATION)
        logger.warning(f"Failed login attempt {current_attempts}/{MAX_LOGIN_ATTEMPTS} for {email}")
        return current_attempts
    except Exception as e:
        logger.error(f"Failed to increment failed attempts: {e}")
        return 0


def reset_failed_attempts(email):
    """Reset failed login attempts counter"""
    try:
        lockout_key = f"lockout:{email}"
        redis_client.delete(lockout_key)
        logger.info(f"Reset failed attempts for {email}")
    except Exception as e:
        logger.error(f"Failed to reset failed attempts: {e}")


def normalize_datetime(dt):
    """Convert datetime to naive UTC datetime for consistent comparisons"""
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


@user_auth.after_request
def after_request(response):
    """Add security headers to all responses"""
    return add_security_headers(response)


@user_auth.route('/login', methods=['POST', 'GET'])
@limiter.limit("5 per 5 minutes")  # Rate limiting: 5 attempts per 5 minutes per IP
def login() -> Response | tuple:
    """Creates token and puts it in cookie with enhanced security"""
    client_ip = get_remote_address()

    # Check if already logged in
    is_logged = request.cookies.get(COOKIE_AUTH, None)
    if is_logged:
        try:
            # Check if token is blacklisted
            if not is_token_blacklisted(is_logged):
                decoded_data = decode_token(is_logged.encode('utf-8'), Config.PUP_PATH)
                if decoded_data:
                    return add_security_headers(jsonify({'success': True, 'message': 'Already logged in'}))
        except:
            pass  # Token invalid, continue with login

    if request.method == 'GET':
        add_response_delay()
        return add_security_headers(jsonify({'authenticated': False, 'message': 'Not logged in'})), 401

    # POST request - handle login
    try:
        data = request.get_json()
        if not data:
            add_response_delay()
            log_auth_attempt('login', 'unknown', client_ip, False, 'No data provided')
            return add_security_headers(jsonify({'error': 'No data provided'})), 400

        # Sanitize inputs
        email = sanitize_input(data.get('user_name') or data.get('email'))
        password = sanitize_input(data.get('password'))

        if not email or not password:
            add_response_delay()
            log_auth_attempt('login', email or 'unknown', client_ip, False, 'Missing credentials')
            return add_security_headers(jsonify({'error': 'Email and password are required'})), 400

        # Normalize email
        email = email.lower().strip()

        # Enhanced email validation
        if not validate_email(email):
            add_response_delay()
            log_auth_attempt('login', email, client_ip, False, 'Invalid email format')
            return add_security_headers(jsonify({'error': 'Invalid email format'})), 400

        # Check account lockout
        if check_account_lockout(email):
            add_response_delay()
            log_auth_attempt('login', email, client_ip, False, 'Account locked')
            return add_security_headers(jsonify({
                'error': 'Account temporarily locked due to too many failed attempts. Try again later.',
                'locked': True
            })), 423

        # Find user by email
        user = session.query(User).filter_by(email=email).first()

        # Use timing-safe comparison for user existence check
        user_exists = user is not None

        # Always check password to prevent timing attacks
        if user_exists:
            password_valid = check_password_hash(user.password, password)
        else:
            # Dummy password check to maintain constant time
            check_password_hash(generate_password_hash('dummy_password'), password)
            password_valid = False

        if not user_exists or not password_valid:
            add_response_delay()
            if user_exists:
                increment_failed_attempts(email)
            log_auth_attempt('login', email, client_ip, False, 'Invalid credentials')
            return add_security_headers(jsonify({'error': 'Invalid credentials'})), 400

        # Check if account is confirmed
        if not user.confirmed:
            add_response_delay()
            log_auth_attempt('login', email, client_ip, False, 'Account not confirmed')
            return add_security_headers(jsonify({
                'error': 'Account not confirmed. Please check your email.',
                'is_confirmed': False
            })), 423

        # Successful login - reset failed attempts
        reset_failed_attempts(email)

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
            log_auth_attempt('login', email, client_ip, False, 'Token generation failed')
            return add_security_headers(jsonify({'error': 'Authentication failed'})), 500

        # Log successful login
        log_auth_attempt('login', email, client_ip, True, 'Success')

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
        return add_security_headers(resp)

    except Exception as e:
        logger.error(f"Login error: {e}")
        add_response_delay()
        log_auth_attempt('login', 'unknown', client_ip, False, f'Server error: {str(e)}')
        return add_security_headers(jsonify({'error': 'Server error occurred'})), 500


@user_auth.route('/register', methods=['POST'])
@limiter.limit("3 per 10 minutes")  # Rate limiting for registration
def register() -> Response | tuple:
    """Add new user to database with email confirmation and enhanced security"""
    client_ip = get_remote_address()

    try:
        data = request.get_json()
        if not data:
            add_response_delay()
            log_auth_attempt('register', 'unknown', client_ip, False, 'No data provided')
            return add_security_headers(jsonify({'error': 'No data provided'})), 400

        required_fields = ['user_name', 'password', 'password2', 'email']
        for field in required_fields:
            if field not in data or not data[field]:
                add_response_delay()
                log_auth_attempt('register', data.get('email', 'unknown'), client_ip, False, f'Missing field: {field}')
                return add_security_headers(jsonify({'error': f'{field} is required'})), 400

        # Sanitize inputs
        email = sanitize_input(data['email']).lower().strip()
        password = sanitize_input(data['password'])
        password2 = sanitize_input(data['password2'])
        user_name = sanitize_input(data['user_name'])

        # Enhanced email validation
        if not validate_email(email):
            add_response_delay()
            log_auth_attempt('register', email, client_ip, False, 'Invalid email format')
            return add_security_headers(jsonify({'error': 'Invalid email format'})), 400

        # Validate username length and content
        if len(user_name) < 3 or len(user_name) > 50:
            add_response_delay()
            log_auth_attempt('register', email, client_ip, False, 'Invalid username length')
            return add_security_headers(jsonify({'error': 'Username must be between 3 and 50 characters'})), 400

        # Validate password match using secure comparison
        if not secure_compare(password, password2):
            add_response_delay()
            log_auth_attempt('register', email, client_ip, False, 'Passwords do not match')
            return add_security_headers(jsonify({'error': 'Passwords do not match'})), 400

        # Enhanced password validation
        if len(password) < 8:
            add_response_delay()
            return add_security_headers(jsonify({'error': 'Hasło musi mieć co najmniej 8 znaków.'})), 400
        if not re.search(r'[a-z]', password):
            add_response_delay()
            return add_security_headers(
                jsonify({'error': 'Hasło musi zawierać co najmniej jedną małą literę (a-z).'})), 400
        if not re.search(r'[A-Z]', password):
            add_response_delay()
            return add_security_headers(
                jsonify({'error': 'Hasło musi zawierać co najmniej jedną dużą literę (A-Z).'})), 400
        if not re.search(r'[0-9]', password):
            add_response_delay()
            return add_security_headers(jsonify({'error': 'Hasło musi zawierać co najmniej jedną cyfrę (0-9).'})), 400
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            add_response_delay()
            return add_security_headers(
                jsonify({'error': 'Hasło musi zawierać co najmniej jeden znak specjalny (!@#$%^&*(),.?":{}|<>).'})), 400

        # Check if user already exists
        existing_user = session.query(User).filter_by(email=email).first()
        if existing_user:
            add_response_delay()
            log_auth_attempt('register', email, client_ip, False, 'Email already exists')
            return add_security_headers(jsonify({'error': 'User with this email already exists'})), 400

        # Create new user
        user = User(
            user_name=user_name,
            password=generate_password_hash(password, salt_length=24),
            email=email,
            role=data.get('role', 'user'),
            age=int(data.get('age', 0)) if data.get('age') else 0,
            confirmed=False
        )

        # Generate confirmation token
        token = generate_confirmation_token(email)
        if not token:
            logger.error("Failed to generate confirmation token")
            return add_security_headers(jsonify({'error': 'Failed to generate confirmation token'})), 500

        session.add(user)
        session.commit()

        confirmation_link = f"{FRONTEND}/confirm-email?token={token}"

        # Enhanced email template
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

        send_email(email, "Potwierdź rejestrację w TorchED", message, html=True)

        log_auth_attempt('register', email, client_ip, True, 'Registration successful')

        return add_security_headers(jsonify({
            'success': True,
            'message': 'User registered successfully. Please check your email for confirmation.'
        })), 201

    except Exception as e:
        session.rollback()
        logger.error(f"Error in register: {e}")
        add_response_delay()
        log_auth_attempt('register', 'unknown', client_ip, False, f'Server error: {str(e)}')
        return add_security_headers(jsonify({'error': 'Registration failed. Please try again.'})), 500


@user_auth.route('/logout', methods=['GET'])
def logout() -> Response | tuple:
    """Logs out user by clearing cookie and blacklisting token"""
    client_ip = get_remote_address()
    token = request.cookies.get(COOKIE_AUTH, None)

    if not token:
        add_response_delay()
        return add_security_headers(jsonify({'error': 'User not logged in'})), 400

    # Verify token before logout
    try:
        decoded_data = decode_token(token.encode('utf-8'), Config.PUP_PATH)
        if decoded_data:
            user_id = decoded_data.get('aud')
            exp_time = decoded_data.get('exp', 0)
            current_time = int(datetime.datetime.utcnow().timestamp())

            # Calculate remaining time for blacklist
            remaining_time = max(0, exp_time - current_time)

            # Blacklist the token
            blacklist_token(token, remaining_time)

            logger.info(f"User {user_id} logged out successfully from IP {client_ip}")
            log_auth_attempt('logout', f'user_id:{user_id}', client_ip, True, 'Success')
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
    return add_security_headers(resp)


@user_auth.route('/confirm_email/<token>', methods=['GET'])
def confirm_email(token: str) -> tuple[Response, int] | Response:
    """Confirms user email using token with enhanced security"""
    client_ip = get_remote_address()

    try:
        is_valid, email = confirm_token(token)

        if not is_valid or not email:
            add_response_delay()
            log_auth_attempt('email_confirm', email or 'unknown', client_ip, False, 'Invalid token')
            return add_security_headers(jsonify({'error': 'Invalid or expired confirmation token'})), 400

        user = session.query(User).filter_by(email=email).first()
        if not user:
            add_response_delay()
            log_auth_attempt('email_confirm', email, client_ip, False, 'User not found')
            return add_security_headers(jsonify({'error': 'User not found'})), 404

        if user.confirmed:
            log_auth_attempt('email_confirm', email, client_ip, True, 'Already confirmed')
            return redirect(f"{FRONTEND}?confirmed=already")

        user.confirmed = True
        session.commit()

        logger.info(f"Email confirmed for user: {email}")
        log_auth_attempt('email_confirm', email, client_ip, True, 'Success')
        return redirect(f"{FRONTEND}?confirmed=success")

    except Exception as e:
        session.rollback()
        logger.error(f"Error in confirm_email: {e}")
        add_response_delay()
        log_auth_attempt('email_confirm', 'unknown', client_ip, False, f'Server error: {str(e)}')
        return add_security_headers(jsonify({'error': 'Email confirmation failed'})), 500


@user_auth.route('/forgot-password', methods=['POST'])
@limiter.limit("3 per 15 minutes")  # Rate limiting for password reset
def forgot_password() -> Response | tuple:
    """Sends password reset email with enhanced security"""
    client_ip = get_remote_address()

    try:
        data = request.get_json()
        if not data or not data.get('email'):
            add_response_delay()
            log_auth_attempt('password_reset_request', 'unknown', client_ip, False, 'No email provided')
            return add_security_headers(jsonify({'error': 'Email is required'})), 400

        email = sanitize_input(data.get('email')).strip().lower()

        # Enhanced email validation
        if not validate_email(email):
            add_response_delay()
            log_auth_attempt('password_reset_request', email, client_ip, False, 'Invalid email format')
            return add_security_headers(jsonify({'error': 'Invalid email format'})), 400

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

            # NAPRAWIONY LINK - używa FRONTEND (już było prawidłowe)
            reset_link = f"{FRONTEND}/reset-password?reset_token={reset_token}"

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

            # Send email
            send_email(email, "🔒 Resetowanie hasła - TorchED", message, html=True)
            logger.info(f"Password reset email sent to: {email}")
            log_auth_attempt('password_reset_request', email, client_ip, True, 'Reset email sent')

        # Always return success to prevent email enumeration
        # This protects against attacks that try to discover valid email addresses
        add_response_delay()
        return add_security_headers(jsonify({
            'success': True,
            'message': 'Jeśli podany email istnieje w naszej bazie, wysłaliśmy link do resetowania hasła.'
        })), 200

    except Exception as e:
        session.rollback()
        logger.error(f"Error in forgot_password: {e}")
        add_response_delay()
        log_auth_attempt('password_reset_request', 'unknown', client_ip, False, f'Server error: {str(e)}')
        return add_security_headers(jsonify({'error': 'Wystąpił błąd. Spróbuj ponownie później.'})), 500


@user_auth.route('/reset-password', methods=['POST'])
@limiter.limit("5 per 15 minutes")  # Rate limiting for password reset
def reset_password() -> Response | tuple:
    """Resets password using token with enhanced security"""
    client_ip = get_remote_address()

    try:
        data = request.get_json()
        if not data:
            add_response_delay()
            log_auth_attempt('password_reset', 'unknown', client_ip, False, 'No data provided')
            return add_security_headers(jsonify({'error': 'Brak danych'})), 400

        token = sanitize_input(data.get('reset_token'))
        new_password = sanitize_input(data.get('new_password'))
        confirm_password = sanitize_input(data.get('confirm_password'))

        if not all([token, new_password, confirm_password]):
            add_response_delay()
            log_auth_attempt('password_reset', 'unknown', client_ip, False, 'Missing fields')
            return add_security_headers(jsonify({'error': 'Wszystkie pola są wymagane'})), 400

        # Use secure comparison for password matching
        if not secure_compare(new_password, confirm_password):
            add_response_delay()
            log_auth_attempt('password_reset', 'unknown', client_ip, False, 'Passwords do not match')
            return add_security_headers(jsonify({'error': 'Hasła nie są identyczne'})), 400

        # Enhanced password validation
        if len(new_password) < 8:
            add_response_delay()
            return add_security_headers(jsonify({'error': 'Hasło musi mieć co najmniej 8 znaków'})), 400

        if not re.search(r'[a-z]', new_password):
            add_response_delay()
            return add_security_headers(jsonify({'error': 'Hasło musi zawierać małą literę'})), 400

        if not re.search(r'[A-Z]', new_password):
            add_response_delay()
            return add_security_headers(jsonify({'error': 'Hasło musi zawierać dużą literę'})), 400

        if not re.search(r'[0-9]', new_password):
            add_response_delay()
            return add_security_headers(jsonify({'error': 'Hasło musi zawierać cyfrę'})), 400

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', new_password):
            add_response_delay()
            return add_security_headers(jsonify({'error': 'Hasło musi zawierać znak specjalny'})), 400

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
            add_response_delay()
            log_auth_attempt('password_reset', 'unknown', client_ip, False, 'Invalid token')
            return add_security_headers(jsonify({'error': 'Token nieprawidłowy lub wygasł'})), 400

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
            add_response_delay()
            log_auth_attempt('password_reset', email, client_ip, False, 'Token expired')
            return add_security_headers(jsonify({'error': 'Token wygasł. Poproś o nowy link.'})), 400

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
        log_auth_attempt('password_reset', email, client_ip, True, 'Success')

        return add_security_headers(jsonify({
            'success': True,
            'message': 'Hasło zostało pomyślnie zmienione. Możesz się teraz zalogować.'
        })), 200

    except Exception as e:
        session.rollback()
        logger.error(f"Error in reset_password: {e}")
        add_response_delay()
        log_auth_attempt('password_reset', 'unknown', client_ip, False, f'Server error: {str(e)}')
        return add_security_headers(jsonify({'error': 'Wystąpił błąd. Spróbuj ponownie później.'})), 500


@user_auth.route('/session-check', methods=['GET'])
def session_check() -> Response | tuple:
    """Checks if user is logged in by verifying JWT token with enhanced security"""
    try:
        # Get token from cookie
        token = request.cookies.get(COOKIE_AUTH, None)
        if not token:
            return add_security_headers(jsonify({'authenticated': False})), 401

        # Check if token is blacklisted
        if is_token_blacklisted(token):
            return add_security_headers(jsonify({'authenticated': False, 'error': 'Token revoked'})), 401

        # Decode and verify token using public key
        try:
            decoded_data = decode_token(token.encode('utf-8'), Config.PUP_PATH)
        except Exception as e:
            logger.error(f"Token decode error: {e}")
            return add_security_headers(jsonify({'authenticated': False, 'error': 'Invalid token'})), 401

        if not decoded_data:
            return add_security_headers(jsonify({'authenticated': False, 'error': 'Token verification failed'})), 401

        # Get user_id from decoded token (stored in 'aud' field)
        user_id = decoded_data.get('aud')
        if not user_id:
            return add_security_headers(jsonify({'authenticated': False, 'error': 'Invalid token payload'})), 401

        # Check if user still exists in database
        user = session.query(User).filter_by(id_=user_id).first()
        if not user:
            return add_security_headers(jsonify({'authenticated': False, 'error': 'User not found'})), 401

        # Check account confirmation status
        if not user.confirmed:
            return add_security_headers(jsonify({
                'authenticated': True,
                'user_id': user.id_,
                'email': user.email,
                'confirmed': False,
                'message': 'Account not confirmed'
            })), 200

        # Verify token issuer
        iss = decoded_data.get('iss')
        if iss != 'TorchED_BACKEND_AUTH':
            return add_security_headers(jsonify({'authenticated': False, 'error': 'Invalid token issuer'})), 401

        # Return success with user information
        return add_security_headers(jsonify({
            'authenticated': True,
            'user_id': user.id_,
            'email': user.email,
            'confirmed': user.confirmed,
            'role': user.role,
            'username': user.user_name
        })), 200

    except Exception as e:
        logger.error(f"Error in session_check: {e}")
        return add_security_headers(jsonify({'authenticated': False})), 401
