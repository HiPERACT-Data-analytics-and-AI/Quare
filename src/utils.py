from sqlalchemy import Engine
from sqlalchemy import create_engine as _create_engine


def create_db_engine() -> Engine:
    """
    Creates DB engine from SQLAlchemy, to have a consistent engine generation
    throughout the whole projects, for all modules


    :return: _description_
    """
    db_engine: Engine = _create_engine("sqlite:///src/quare.sqlite3", echo=False)
    return db_engine
