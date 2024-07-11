from json import load
from pathlib import Path

from sqlalchemy import Engine
from sqlalchemy import create_engine as _create_engine


def load_settings() -> dict:
    """
    _summary_

    :return: _description_
    """

    settings_path: Path = Path("settings.json")
    with open(settings_path) as settings_file:
        return load(settings_file)


def create_db_engine() -> Engine:
    """
    Creates DB engine from SQLAlchemy, to have a consistent engine generation
    throughout the whole projects, for all modules


    :return: _description_
    """
    settings = load_settings()
    db_engine: Engine = _create_engine(f"sqlite:///{settings['db_path']}", echo=False)
    return db_engine
