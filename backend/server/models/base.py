from sqlalchemy.orm import (
    DeclarativeBase,
)


class Base(DeclarativeBase):
    pass


metadata = Base.metadata
