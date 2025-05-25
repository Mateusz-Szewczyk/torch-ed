import datetime
import hashlib
import secrets

from dotenv import load_dotenv
from flask import request, redirect, Blueprint, jsonify, url_for
from sqlalchemy import text
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
    data: dict
    user: User
    key_words: list[str]
    password: str
    email: str
    token: str
    link: str
    message: str

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

    # HTML email content - ulepszony szablon
    message = f"""
        <html>
          <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
              * {{ box-sizing: border-box; margin: 0; padding: 0; }}
              body {{ 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; 
                color: #1a1a1a; 
                line-height: 1.6; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 20px; 
                min-height: 100vh;
              }}
              .email-wrapper {{ 
                max-width: 600px; 
                margin: 0 auto; 
                background: #ffffff; 
                border-radius: 16px; 
                overflow: hidden;
                box-shadow: 0 20px 40px rgba(0,0,0,0.15);
              }}
              .header {{ 
                background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
                color: white; 
                text-align: center; 
                padding: 40px 20px;
                position: relative;
              }}
              .header::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><pattern id="grain" width="100" height="100" patternUnits="userSpaceOnUse"><circle cx="25" cy="25" r="1" fill="white" opacity="0.1"/><circle cx="75" cy="75" r="1" fill="white" opacity="0.1"/><circle cx="50" cy="10" r="0.5" fill="white" opacity="0.1"/><circle cx="20" cy="80" r="0.5" fill="white" opacity="0.1"/></pattern></defs><rect width="100" height="100" fill="url(%23grain)"/></svg>');
              }}
              .header h1 {{ 
                font-size: 2.5rem; 
                font-weight: 800; 
                margin-bottom: 8px;
                position: relative;
                z-index: 1;
              }}
              .header .subtitle {{ 
                font-size: 1.1rem; 
                opacity: 0.9;
                font-weight: 400;
                position: relative;
                z-index: 1;
              }}
              .content {{ 
                padding: 40px 30px;
                background: #ffffff;
              }}
              .welcome-text {{ 
                font-size: 1.1rem; 
                color: #374151; 
                margin-bottom: 24px;
                text-align: center;
              }}
              .highlight {{ 
                background: linear-gradient(120deg, #a78bfa 0%, #ec4899 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                font-weight: 600;
              }}
              .button-container {{ 
                text-align: center; 
                margin: 32px 0;
              }}
              .button {{ 
                display: inline-block; 
                padding: 16px 32px; 
                background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
                color: #ffffff !important; 
                text-decoration: none; 
                border-radius: 50px; 
                font-weight: 600;
                font-size: 1.1rem;
                transition: all 0.3s ease;
                box-shadow: 0 4px 15px rgba(79, 70, 229, 0.4);
                text-transform: uppercase;
                letter-spacing: 0.5px;
              }}
              .button:hover {{ 
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(79, 70, 229, 0.6);
              }}
              .link-fallback {{ 
                background: #f8fafc; 
                border: 2px dashed #cbd5e1; 
                border-radius: 8px; 
                padding: 16px; 
                margin: 24px 0;
                text-align: center;
              }}
              .link-fallback p {{ 
                font-size: 0.9rem; 
                color: #64748b; 
                margin-bottom: 8px;
              }}
              .link-fallback a {{ 
                color: #4f46e5; 
                word-break: break-all; 
                font-family: 'Courier New', monospace;
                font-size: 0.85rem;
              }}
              .info-box {{ 
                background: linear-gradient(135deg, #fef3c7 0%, #fbbf24 100%);
                border-left: 4px solid #f59e0b;
                padding: 16px;
                border-radius: 8px;
                margin: 24px 0;
              }}
              .info-box p {{ 
                color: #92400e; 
                font-size: 0.95rem;
                margin: 0;
              }}
              .footer {{ 
                background: #f8fafc; 
                text-align: center; 
                padding: 30px 20px;
                border-top: 1px solid #e2e8f0;
              }}
              .footer-content {{ 
                max-width: 400px; 
                margin: 0 auto;
              }}
              .contact-info {{ 
                font-size: 0.9rem; 
                color: #64748b; 
                margin-bottom: 12px;
              }}
              .contact-info a {{ 
                color: #4f46e5; 
                text-decoration: none;
                font-weight: 500;
              }}
              .copyright {{ 
                font-size: 0.8rem; 
                color: #9ca3af; 
                font-weight: 400;
              }}
              .logo {{ 
                display: none;
              }}
              @media (max-width: 600px) {{
                .email-wrapper {{ margin: 10px; border-radius: 12px; }}
                .header {{ padding: 30px 15px; }}
                .header h1 {{ font-size: 2rem; }}
                .content {{ padding: 30px 20px; }}
                .button {{ padding: 14px 28px; font-size: 1rem; }}
              }}
            </style>
          </head>
          <body>
            <div class="email-wrapper">
              <div class="header">
                <h1>TorchED</h1>
                <div class="subtitle">Twoja podróż z nauką właśnie się zaczyna</div>
              </div>

              <div class="content">
                <p class="welcome-text">
                  Witaj w <span class="highlight">TorchED</span>! 🎉<br>
                  Cieszymy się, że dołączasz do naszej społeczności pasjonatów nauki.
                </p>

                <p style="color: #374151; margin-bottom: 24px;">
                  Aby w pełni cieszyć się wszystkimi funkcjami naszej platformy, musisz potwierdzić swój adres email. To zajmie tylko chwilę!
                </p>

                <div class="button-container">
                  <a href="{link}" class="button">
                    ✨ Potwierdź moje konto
                  </a>
                </div>

                <div class="link-fallback">
                  <p>Problemy z przyciskiem? Skopiuj i wklej ten link:</p>
                  <a href="{link}">{link}</a>
                </div>

                <div class="info-box">
                  <p>
                    <strong>💡 Wskazówka:</strong> Jeśli nie rejestrowałeś się w TorchED, możesz spokojnie zignorować tę wiadomość.
                  </p>
                </div>

                <p style="color: #374151; text-align: center; margin-top: 32px; font-style: italic;">
                  Nie możemy się doczekać, aby zobaczyć, jak rozwijasz swoje umiejętności z nami! 🚀
                </p>

                <p style="color: #6b7280; text-align: center; margin-top: 16px;">
                  Z pozdrowieniami,<br>
                  <strong style="color: #4f46e5;">Zespół TorchED</strong>
                </p>
              </div>

              <div class="footer">
                <div class="footer-content">
                  <div class="contact-info">
                    Masz pytania? Napisz do nas: 
                    <a href="mailto:mateusz.szewczyk000@gmail.com">mateusz.szewczyk000@gmail.com</a>
                  </div>
                  <div class="copyright">
                    © 2025 TorchED. Wszystkie prawa zastrzeżone.
                  </div>
                </div>
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


@user_auth.route('/confirm_email/<token>', methods=['GET'])
def confirm_email(token: str) -> tuple[Response, int] | Response:
    try:
        is_valid, email = confirm_token(token)

        if not is_valid or not email:
            return jsonify({'error': 'Invalid or expired token'}), 400

        user: User | None = session.query(User).filter_by(email=email).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        if user.confirmed:
            return jsonify({'message': 'Email already confirmed.'}), 200

        user.confirmed = True
        session.add(user)
        session.commit()

        return redirect(FRONTEND)

    except Exception as e:
        # Rollback w przypadku błędu
        session.rollback()
        return jsonify({'error': 'An error occurred during email confirmation'}), 500
    finally:
        # Zamknij sesję
        session.close()


@signature_check
@user_auth.route('/unregister/<int:iden>')
def delete_user(iden: int) -> Response:
    # Implementacja usuwania użytkownika
    ...
    return redirect(FRONTEND)


@user_auth.route('/forgot-password', methods=['POST'])
def forgot_password() -> Response | tuple:
    """
    Wysyła email z linkiem do resetowania hasła.
    Zawsze zwraca sukces dla bezpieczeństwa.
    """
    try:
        data = request.get_json()
        if not data or not data.get('email'):
            return jsonify({'error': 'Email is required'}), 400

        email = data.get('email').strip().lower()

        # Znajdź użytkownika
        user: User | None = session.query(User).filter_by(email=email).first()

        if user and user.confirmed:
            # Generuj bezpieczny token
            reset_token = secrets.token_urlsafe(48)
            token_hash = hashlib.sha256(reset_token.encode()).hexdigest()

            # POPRAWKA: Użyj utcnow() zamiast now(UTC) dla consistency
            expires_at = datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=30)

            # Usuń stare tokeny
            session.execute(
                text("DELETE FROM password_reset_tokens WHERE user_id = :user_id"),
                {"user_id": user.id_}
            )

            # Zapisz nowy token
            session.execute(
                text(
                    "INSERT INTO password_reset_tokens (user_id, token_hash, expires_at) VALUES (:user_id, :token_hash, :expires_at)"),
                {
                    "user_id": user.id_,
                    "token_hash": token_hash,
                    "expires_at": expires_at
                }
            )
            session.commit()

            # Stwórz link resetowania
            reset_link = f"{FRONTEND}/reset-password?token={reset_token}"

            # Email template (bez zmian)
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

            # Wyślij email
            send_email(email, "🔒 Resetowanie hasła - TorchED", message, html=True)

        return jsonify({
            'success': True,
            'message': 'Jeśli podany email istnieje w naszej bazie, wysłaliśmy link do resetowania hasła.'
        }), 200

    except Exception as e:
        logger.error(f"Error in forgot_password: {e}")
        return jsonify({'error': 'Wystąpił błąd. Spróbuj ponownie później.'}), 500


@user_auth.route('/reset-password', methods=['POST'])
def reset_password() -> Response | tuple:
    """
    Resetuje hasło na podstawie tokenu.
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

        # Zahashuj token do sprawdzenia w bazie
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        # Znajdź token w bazie
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

        # POPRAWKA: Zapewnij że oba datetime są "naive" (bez timezone)
        current_time = datetime.datetime.utcnow()  # naive datetime

        # Konwertuj expires_at do naive datetime
        if expires_at:
            # Jeśli expires_at jest string
            if isinstance(expires_at, str):
                try:
                    # Spróbuj parsować z timezone
                    if 'T' in expires_at and ('+' in expires_at or 'Z' in expires_at):
                        expires_at = datetime.datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                        expires_at = expires_at.replace(tzinfo=None)  # Make naive
                    else:
                        # Parse jako naive datetime
                        expires_at = datetime.datetime.fromisoformat(expires_at)
                except ValueError:
                    # Fallback parsing
                    expires_at = datetime.datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S')

            # Jeśli expires_at jest aware datetime object
            elif hasattr(expires_at, 'tzinfo') and expires_at.tzinfo is not None:
                expires_at = expires_at.replace(tzinfo=None)  # Make naive

        # Teraz oba są naive - można porównać
        if current_time > expires_at:
            session.execute(
                text("DELETE FROM password_reset_tokens WHERE token_hash = :token_hash"),
                {"token_hash": token_hash}
            )
            session.commit()
            return jsonify({'error': 'Token wygasł. Poproś o nowy link.'}), 400

        # Aktualizuj hasło użytkownika
        hashed_password = generate_password_hash(new_password, salt_length=24)
        session.execute(
            text("UPDATE users SET password = :password WHERE id_ = :user_id"),
            {"password": hashed_password, "user_id": user_id}
        )

        # Usuń użyty token
        session.execute(
            text("DELETE FROM password_reset_tokens WHERE user_id = :user_id"),
            {"user_id": user_id}
        )

        session.commit()

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
    Sprawdza czy użytkownik jest zalogowany poprzez weryfikację JWT token z cookie.
    Endpoint odpowiednik login() ale dla sprawdzania sesji.
    """
    try:
        # Pobierz token z cookie (używa tego samego COOKIE_AUTH co login)
        token = request.cookies.get(COOKIE_AUTH, None)
        if not token:
            return jsonify({'authenticated': False}), 401

        # Dekoduj i weryfikuj token (odwrotność generate_token)
        try:
            decoded_data = decode_token(token.encode('utf-8'))
        except Exception as e:
            logger.error(f"Token decode error: {e}")
            return jsonify({'authenticated': False, 'error': 'Invalid token'}), 401

        # Sprawdź czy token nie wygasł i ma prawidłową strukturę
        if not decoded_data:
            return jsonify({'authenticated': False, 'error': 'Token verification failed'}), 401

        # Pobierz user_id z zdekodowanego tokenu
        user_id = decoded_data.get('user_id')
        if not user_id:
            return jsonify({'authenticated': False, 'error': 'Invalid token payload'}), 401

        # Sprawdź czy użytkownik nadal istnieje w bazie (podobnie jak w login)
        user = session.query(User).filter_by(id_=user_id).first()
        if not user:
            return jsonify({'authenticated': False, 'error': 'User not found'}), 401

        # Sprawdź dodatkowe warunki (jak w login przy data_check)
        if not user.confirmed:
            return jsonify({
                'authenticated': True,  # Token jest ważny
                'user_id': user.id_,
                'email': user.email,
                'confirmed': False,
                'message': 'Account not confirmed'
            }), 200

        # Sprawdź czy token ma prawidłowy issuer (jak w generate_token)
        iss = decoded_data.get('iss')
        if iss != 'TorchED_BACKEND_AUTH':
            return jsonify({'authenticated': False, 'error': 'Invalid token issuer'}), 401

        # Zwróć sukces z informacjami o użytkowniku
        return jsonify({
            'authenticated': True,
            'user_id': user.id_,
            'email': user.email,
            'confirmed': user.confirmed,
            'role': user.role
        }), 200

    except Exception as e:
        logger.error(f"Error in session_check: {e}")
        return jsonify({'authenticated': False}), 401
