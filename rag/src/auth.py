from fastapi import Request, HTTPException, status, Depends
from sqlalchemy.orm import Session
from authlib.jose import jwt
from authlib.jose.errors import ExpiredTokenError, InvalidTokenError
import os

from .database import SessionLocal
from .models import User

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
    Dekoduje token JWT (RSA) z cookie `TorchED_AUTH`.
    Jeśli token nieprawidłowy, rzuca 401.
    """
    token = request.cookies.get("TorchED_AUTH")
    print(token)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No auth cookie provided.",
        )

    # Ścieżka do klucza
    path = os.getenv("PUP_PATH", "")
    if not path:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server misconfigured: missing public key path."
        )

    try:
        with open(path, "r") as f:
            public_key = f.read()
        if not public_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Public key file is empty or not found."
            )

        decoded = jwt.decode(token.encode("utf-8"), public_key)
        decoded.validate()  # weryfikacja exp, iat, itp.

        user_id = decoded.get("aud")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalid: 'aud' (user_id) missing.",
            )

    except ExpiredTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired."
        )
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate token (invalid)."
        )
    except OSError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not read public key file: {e}"
        )

    # Sprawdzamy w bazie, czy user istnieje
    user = db.query(User).filter(User.id_ == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found."
        )

    return user
