import os
import logging
from flask import Blueprint, redirect, url_for
from authlib.integrations.flask_client import OAuth
from werkzeug.security import generate_password_hash
from sqlalchemy.exc import IntegrityError
import secrets

from ..models import User
from ..config import Config
from ..jwt import generate_token
from ..utils import FRONTEND, add_security_headers

logger = logging.getLogger(__name__)

oauth_blueprint = Blueprint('oauth', __name__)

# Initialize OAuth
oauth = OAuth()


def init_oauth(app):
    """Initialize OAuth with app"""
    oauth.init_app(app)

    # Register Google
    oauth.register(
        name='google',
        client_id=os.getenv('GOOGLE_CLIENT_ID'),
        client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )

    # Register GitHub
    oauth.register(
        name='github',
        client_id=os.getenv('GITHUB_CLIENT_ID'),
        client_secret=os.getenv('GITHUB_CLIENT_SECRET'),
        access_token_url='https://github.com/login/oauth/access_token',
        authorize_url='https://github.com/login/oauth/authorize',
        api_base_url='https://api.github.com/',
        client_kwargs={'scope': 'user:email'},
    )


def handle_oauth_user(provider, user_info):
    """
    Create or get OAuth user and return JWT token.
    This keeps your existing JWT session system.
    """
    # Import session here to avoid circular import
    from .. import session

    try:
        email = user_info.get('email')

        if not email:
            logger.error(f"No email from {provider} OAuth")
            return None, "Email not provided by OAuth provider"

        email = email.lower().strip()

        # Check if user exists
        user = session.query(User).filter_by(email=email).first()

        if user:
            # User exists - check if they're using a different login method
            if user.password and len(user.password) > 10:  # Has email/password login
                # You can either:
                # A) Allow linking (update to add OAuth)
                # B) Block and ask them to use password login
                # For security, let's allow linking:
                logger.info(f"Existing user {email} logged in via {provider}")
            else:
                logger.info(f"OAuth user {email} logged in via {provider}")
        else:
            # Create new OAuth user (no password stored)
            username = user_info.get('name') or user_info.get('login') or email.split('@')[0]

            # Generate a random password (never shown to user, just for DB constraint)
            random_password = secrets.token_urlsafe(32)

            user = User(
                user_name=username[:50],  # Truncate if needed
                password=generate_password_hash(random_password, salt_length=24),
                email=email,
                role='user',
                age=0,
                confirmed=True  # OAuth emails are pre-verified
            )

            session.add(user)
            session.commit()
            logger.info(f"New OAuth user created: {email} via {provider}")

        # Generate YOUR existing JWT token (same as email/password login)
        token_bytes = generate_token(
            user_id=user.id_,
            role=user.role,
            iss='TorchED_BACKEND_AUTH',
            path=Config.PRP_PATH
        )

        return token_bytes.decode('utf-8'), None

    except IntegrityError as e:
        session.rollback()
        logger.error(f"Database error in OAuth: {e}")
        return None, "User creation failed"
    except Exception as e:
        session.rollback()
        logger.error(f"Error in handle_oauth_user: {e}")
        return None, str(e)


# Google OAuth routes
@oauth_blueprint.route('/auth/google')
def google_login():
    """Redirect to Google OAuth"""
    redirect_uri = url_for('oauth.google_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@oauth_blueprint.route('/auth/google/callback')
def google_callback():
    """Handle Google OAuth callback"""
    try:
        # Exchange code for token and get user info
        token = oauth.google.authorize_access_token()
        user_info = token.get('userinfo')

        if not user_info:
            resp = oauth.google.get('https://www.googleapis.com/oauth2/v3/userinfo')
            user_info = resp.json()

        logger.info(f"Google OAuth callback for: {user_info.get('email')}")

        # Create/get user and issue JWT
        jwt_token, error = handle_oauth_user('google', user_info)

        if error:
            return redirect(f"{FRONTEND}?error=oauth_failed")

        # Create response with JWT cookie (same as your /login endpoint)
        response = redirect(f"{FRONTEND}?login=success")
        response.set_cookie(
            'TorchED_auth',
            jwt_token,
            samesite='None',
            max_age=60 * 60 * 24 * 5,  # 5 days
            httponly=True,
            secure=Config.IS_SECURE,
            path='/',
            domain=Config.DOMAIN
        )

        return add_security_headers(response)

    except Exception as e:
        logger.error(f"Google OAuth error: {e}")
        return redirect(f"{FRONTEND}?error=oauth_failed")


# GitHub OAuth routes
@oauth_blueprint.route('/auth/github')
def github_login():
    """Redirect to GitHub OAuth"""
    redirect_uri = url_for('oauth.github_callback', _external=True)
    return oauth.github.authorize_redirect(redirect_uri)


@oauth_blueprint.route('/auth/github/callback')
def github_callback():
    """Handle GitHub OAuth callback"""
    try:
        # Exchange code for token
        token = oauth.github.authorize_access_token()

        # Get user info
        resp = oauth.github.get('user', token=token)
        user_info = resp.json()

        # GitHub might not return email in profile, fetch separately
        if not user_info.get('email'):
            email_resp = oauth.github.get('user/emails', token=token)
            emails = email_resp.json()
            # Get primary verified email
            for email_obj in emails:
                if email_obj.get('primary') and email_obj.get('verified'):
                    user_info['email'] = email_obj['email']
                    break

        logger.info(f"GitHub OAuth callback for: {user_info.get('email')}")

        # Create/get user and issue JWT
        jwt_token, error = handle_oauth_user('github', user_info)

        if error:
            return redirect(f"{FRONTEND}?error=oauth_failed")

        # Create response with JWT cookie (same as your /login endpoint)
        response = redirect(f"{FRONTEND}?login=success")
        response.set_cookie(
            'TorchED_auth',
            jwt_token,
            samesite='None',
            max_age=60 * 60 * 24 * 5,  # 5 days
            httponly=True,
            secure=Config.IS_SECURE,
            path='/',
            domain=Config.DOMAIN
        )

        return add_security_headers(response)

    except Exception as e:
        logger.error(f"GitHub OAuth error: {e}")
        return redirect(f"{FRONTEND}?error=oauth_failed")
