# init_db.py

from database import engine, Base
from models import Deck, Flashcard

def init_db():
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")

if __name__ == "__main__":
    init_db()