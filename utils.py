from sqlalchemy import Engine
from sqlalchemy import create_engine as _create_engine


def create_db_engine() -> Engine:
    db_engine: Engine = _create_engine("sqlite:///quare.sqlite3", echo=False)
    return db_engine
