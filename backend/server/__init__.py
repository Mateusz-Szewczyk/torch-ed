from flask import Flask
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from .config import Config, TestConfig
from .models import Base


session: scoped_session


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
        

    from .api.api_auth import auth as api_auth
    app.register_blueprint(api_auth, url_prefix='/api/auth')
    
    @app.teardown_appcontext
    def remove_session(exception=None) -> None:
        session.remove()
        
    return app
    
    