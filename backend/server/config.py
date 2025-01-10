import base64
import os
# from dotenv import load_dotenv
#
# load_dotenv()


class Config:
    DATABASE_URL: str = os.getenv("DATABASE_URL", 'postgresql://postgres:njLFJCMxXaxbWXHsCLgUvfFnsishdbvW@postgres.railway.internal:5432/railway')
    SQLALCHEMY_TRACK_MODYFICATIONS: bool = False
    SECRET_KEY: str | None = os.getenv('SECRET_KEY')
    PRP_PATH: str = "prp_key.pem"
    PUP_PATH: str = "pup_key.pem"
    SALT = os.getenv('SALT')



class TestConfig:
    DATABASE_URL: str = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODYFICATIONS: bool = False
    SECRET_KEY: str | None = os.getenv('SECRET_KEY')


def load_private_keys():
    prp_key_base64 = os.getenv("PRP_KEY")
    pup_key_base64 = os.getenv("PUP_KEY")

    if prp_key_base64:
        prp_key = base64.b64decode(prp_key_base64).decode('utf-8')
        with open(Config.PRP_PATH, "w") as f:
            f.write(prp_key)
    else:
        raise ValueError("PRP_KEY environment variable is missing!")

    if pup_key_base64:
        pup_key = base64.b64decode(pup_key_base64).decode('utf-8')
        with open(Config.PUP_PATH, "w") as f:
            f.write(pup_key)
    else:
        raise ValueError("PUP_KEY environment variable is missing!")


def get_engine(testing=False):
    from sqlalchemy import create_engine, Engine
    if testing:
        return create_engine(TestConfig.DATABASE_URL, echo=True)
    else:
        return create_engine(Config.DATABASE_URL, echo=True)