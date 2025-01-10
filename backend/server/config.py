import os
# from dotenv import load_dotenv
#
# load_dotenv()


class Config:
    DATABASE_URL: str = os.getenv("DATABASE_URL", 'postgresql://postgres:njLFJCMxXaxbWXHsCLgUvfFnsishdbvW@postgres.railway.internal:5432/railway')
    SQLALCHEMY_TRACK_MODYFICATIONS: bool = False
    SECRET_KEY: str | None = os.getenv('SECRET_KEY')


class TestConfig:
    DATABASE_URL: str = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODYFICATIONS: bool = False
    SECRET_KEY: str | None = os.getenv('SECRET_KEY')