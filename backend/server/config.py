import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    DATABASE_URL: str = f'postgresql+psycopg://{os.getenv('USER_DB')}:{os.getenv('PASSWORD_DB')}@{os.getenv('SERVER')}/{os.getenv('POSTGRES_DB')}'
    SQLALCHEMY_TRACK_MODYFICATIONS: bool = False
    SECRET_KEY: str | None = os.getenv('SECRET_KEY')


class TestConfig:
    DATABASE_URL: str = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODYFICATIONS: bool = False
    SECRET_KEY: str | None = os.getenv('SECRET_KEY')