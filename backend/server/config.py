import base64
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    DATABASE_URL: str = os.getenv("DATABASE_URL", 'postgresql://admin:admin1234@localhost:5432/torched_db')
    SQLALCHEMY_TRACK_MODYFICATIONS: bool = False
    SECRET_KEY: str | None = os.getenv('SECRET_KEY')
    PRP_PATH: str = "prp_key.pem"
    PUP_PATH: str = "pup_key.pem"
    SALT: str = os.getenv('SALT', '')
    _domain_env = os.getenv('DOMAIN')
    DOMAIN: str | None = None if _domain_env == 'localhost' else _domain_env
    IS_SECURE: bool = os.getenv('IS_SECURE', 'true').lower() == 'true'
    RESEND_API_KEY: str | None = os.getenv('RESEND_API_KEY')

    @classmethod
    def validate(cls) -> None:
        """Validate critical environment variables are set."""
        if not cls.RESEND_API_KEY:
            raise ValueError(
                "RESEND_API_KEY is required but not set. "
                "Please add it to your .env or Railway environment variables."
            )



class TestConfig:
    DATABASE_URL: str = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODYFICATIONS: bool = False
    SECRET_KEY: str | None = os.getenv('SECRET_KEY')


def load_private_keys():
    prp_key_base64 = os.getenv("PRP_KEY")
    pup_key_base64 = os.getenv("PUP_KEY")

    if prp_key_base64:
        # Decode to BYTES, write bytes directly
        prp_key_bytes = base64.b64decode(prp_key_base64)
        with open(Config.PRP_PATH, "wb") as f:
            f.write(prp_key_bytes)
    else:
        raise ValueError("PRP_KEY environment variable is missing!")

    if pup_key_base64:
        pup_key_bytes = base64.b64decode(pup_key_base64)
        with open(Config.PUP_PATH, "wb") as f:
            f.write(pup_key_bytes)
    else:
        raise ValueError("PUP_KEY environment variable is missing!")


def get_engine(testing=False):
    from sqlalchemy import create_engine, Engine
    if testing:
        return create_engine(TestConfig.DATABASE_URL, echo=True)
    else:
        return create_engine(Config.DATABASE_URL, echo=True)
