import os
import redis
from flask import Flask
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from dotenv import load_dotenv
from flask_cors import CORS

from .config import Config, TestConfig
from .models.base import Base


load_dotenv()

session: scoped_session
blacklist: redis.Redis = redis.Redis(
    host=os.getenv('REDIS_URL', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    db=0, decode_responses=True)


def get_engine(testing: bool = False) -> Engine:
    engine: Engine = create_engine(Config.DATABASE_URL)\
        if not testing else \
            create_engine(TestConfig.DATABASE_URL)
    return engine


def create_app(testing: bool = False) -> Flask:
    global session

    app: Flask = Flask(__name__)

    if testing:
        app.config.from_object(TestConfig)
    else:
        app.config.from_object(Config)



    engine: Engine = get_engine(testing=testing)
    session_local: sessionmaker = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = scoped_session(session_local)

    with engine.begin() as conn:
        Base.metadata.create_all(bind=conn)


    from .routes.token_auth import api_auth as api_auth
    from .routes.user_auth import user_auth
    app.register_blueprint(api_auth, url_prefix='/api/v1/auth')
    app.register_blueprint(user_auth, url_prefix='/api/v1/auth')
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'None'

    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": ["http://localhost:3000",
                            "http://127.0.0.1:3000",
                            "https://torch-9vlkoolu7-mateusz-szewczyks-projects.vercel.app",
                            "https://torch-ed.vercel.app"
                            ],

                "supports_credentials": True,
                "allow_headers": ["Content-Type", "Authorization"],
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
            }
        }
    )

    @app.teardown_appcontext
    def remove_session(exception=None) -> None:
        session.remove()

    return app
