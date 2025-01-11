# src/database.py

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv

# Załaduj zmienne środowiskowe z pliku .env
load_dotenv()

POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
POSTGRES_DB = os.getenv('POSTGRES_DB')
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5432')

DATABASE_URL = os.getenv('DATABASE_URL',f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")

# Utwórz silnik SQLAlchemy
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

# Utwórz sesję
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Utwórz bazę deklaratywną
Base = declarative_base()
