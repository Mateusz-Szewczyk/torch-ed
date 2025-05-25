from fastapi import Request, HTTPException, status, Depends
from sqlalchemy.orm import Session
from authlib.jose import jwt
from authlib.jose.errors import ExpiredTokenError, InvalidTokenError
import os
import logging

from .database import SessionLocal
from .models import User
from .config import Config

# Konfiguracja loggingu
logger = logging.getLogger(__name__)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
        request: Request,
        db: Session = Depends(get_db)
) -> User:
    """
    Dekoduje token JWT (RSA) z cookie `TorchED_auth` (POPRAWKA: mała litera 'a').
    Jeśli token nieprawidłowy, rzuca 401.
    Pełna kompatybilność z systemem auth z Flask.
    """
    # POPRAWKA: Użyj tej samej nazwy cookie co w Flask
    token = request.cookies.get("TorchED_auth")  # była "TorchED_AUTH"
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No auth cookie provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Ścieżka do klucza publicznego
    path = Config.PUP_PATH
    if not path:
        logger.error("PUP_PATH not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server misconfigured: missing public key path."
        )

    try:
        # Odczytaj klucz publiczny
        with open(path, "r") as f:
            public_key = f.read()
        if not public_key:
            logger.error(f"Public key file is empty: {path}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Public key file is empty or not found."
            )

        # Dekoduj i waliduj token
        decoded = jwt.decode(token.encode("utf-8"), public_key)
        decoded.validate()  # weryfikacja exp, iat, itp.

        # POPRAWKA: Dodaj walidację issuer (zgodność z Flask)
        issuer = decoded.get("iss")
        if issuer != "TorchED_BACKEND_AUTH":
            logger.warning(f"Invalid token issuer: {issuer}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalid: incorrect issuer.",
            )

        # Pobierz user_id z pola 'aud'
        user_id = decoded.get("aud")
        if not user_id:
            logger.warning("Token missing 'aud' field")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalid: 'aud' (user_id) missing.",
            )

        # POPRAWKA: Dodaj walidację roli (opcjonalne, ale przydatne)
        user_role = decoded.get("pre")
        if not user_role:
            logger.warning("Token missing 'pre' (role) field")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalid: role information missing.",
            )

    except ExpiredTokenError:
        logger.info(f"Expired token for request to {request.url}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidTokenError as e:
        logger.warning(f"Invalid token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate token (invalid).",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except OSError as e:
        logger.error(f"Could not read public key file {path}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not read public key file: {e}"
        )
    except Exception as e:
        logger.error(f"Unexpected error during token validation: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token validation failed.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # POPRAWKA: Sprawdzamy w bazie czy user istnieje (użyj id_ zamiast id)
    user = db.query(User).filter(User.id_ == user_id).first()
    if user is None:
        logger.warning(f"User {user_id} not found in database")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
        )

    # POPRAWKA: Sprawdź czy konto jest potwierdzone
    if not user.confirmed:
        logger.info(f"Unconfirmed account access attempt: {user.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account not confirmed. Please check your email.",
        )

    # POPRAWKA: Sprawdź zgodność roli (opcjonalne, ale zwiększa bezpieczeństwo)
    if user.role != user_role:
        logger.warning(f"Role mismatch for user {user_id}: token={user_role}, db={user.role}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token role mismatch.",
        )

    logger.debug(f"Successfully authenticated user: {user.email}")
    return user


def get_current_user_optional(
        request: Request,
        db: Session = Depends(get_db)
) -> User | None:
    """
    Opcjonalna autentykacja - zwraca użytkownika jeśli jest zalogowany, None w przeciwnym razie.
    Nie rzuca wyjątku jeśli brak tokenu.
    """
    try:
        return get_current_user(request, db)
    except HTTPException:
        return None


def require_role(required_role: str):
    """
    Dependency do sprawdzania roli użytkownika.

    Usage:
    @app.get("/admin")
    def admin_only(user: User = Depends(require_role("admin"))):
        return {"message": "Admin only"}
    """

    def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role != required_role:
            logger.warning(f"Role access denied: {user.email} ({user.role}) tried to access {required_role}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {required_role}",
            )
        return user

    return role_checker


def require_any_role(allowed_roles: list[str]):
    """
    Dependency do sprawdzania czy użytkownik ma jedną z dozwolonych ról.

    Usage:
    @app.get("/moderator")
    def mod_or_admin(user: User = Depends(require_any_role(["admin", "moderator"]))):
        return {"message": "Moderator or admin"}
    """

    def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            logger.warning(f"Role access denied: {user.email} ({user.role}) tried to access {allowed_roles}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(allowed_roles)}",
            )
        return user

    return role_checker


# Pomocnicze funkcje dla testowania
def verify_token_structure(token: str) -> dict:
    """
    Funkcja pomocnicza do debugowania - dekoduje token bez walidacji.
    TYLKO DO TESTOWANIA!
    """
    try:
        import base64
        import json

        # Pobierz payload (środkowa część tokenu)
        parts = token.split('.')
        if len(parts) != 3:
            return {"error": "Invalid token format"}

        # Dekoduj payload
        payload = parts[1]
        # Dodaj padding jeśli potrzeba
        payload += '=' * (-len(payload) % 4)
        decoded_payload = base64.urlsafe_b64decode(payload)
        return json.loads(decoded_payload)

    except Exception as e:
        return {"error": f"Failed to decode: {e}"}


# Testowa funkcja do weryfikacji kompatybilności
async def test_auth_compatibility():
    """
    Funkcja testowa do sprawdzenia kompatybilności z Flask auth.
    Wywołaj ją podczas startup aplikacji.
    """
    try:
        # Sprawdź czy Config jest dostępny
        if not hasattr(Config, 'PUP_PATH'):
            logger.error("Config.PUP_PATH not found")
            return False

        # Sprawdź czy klucz publiczny istnieje
        if not os.path.exists(Config.PUP_PATH):
            logger.error(f"Public key file not found: {Config.PUP_PATH}")
            return False

        logger.info("Auth compatibility check passed")
        return True

    except Exception as e:
        logger.error(f"Auth compatibility check failed: {e}")
        return False
