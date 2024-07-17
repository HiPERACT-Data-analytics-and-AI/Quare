from json import load
from pathlib import Path

from sqlalchemy import Engine
from sqlalchemy import create_engine as _create_engine


def load_settings() -> dict:
    """
    _summary_

    :return: _description_
    """

    KEYS_WITH_PATHS: tuple[str, ...] = (
        "raw_data_directory_path",
        "csvized_data_directory_path",
        "db_path",
        "output_directory_path",
    )

    # TODO Load settings once from provided path or from here if the path is None.
    # Make it singleton-like pattern
    settings_path: Path = Path(__file__).parent / "settings.json"
    with open(settings_path) as settings_file:
        settings = load(settings_file)
        for path in KEYS_WITH_PATHS:
            settings[path] = settings_path.parent / settings[path]
        return settings


# TODO Make it as a singleton (or use as is?). Therefore, there will be no need
# for passing a Session instance to all the functions. Another approach is to create
# multiple engine instances - each module will have its own and independent Session.
# Maybe some of these classes - Engine, Session - is a singleton already?
def create_db_engine() -> Engine:
    """
    Creates DB engine from SQLAlchemy, to have a consistent engine generation
    throughout the whole projects, for all modules

    :return: _description_
    """

    settings = load_settings()
    db_engine: Engine = _create_engine(f"sqlite:///{settings['db_path']}", echo=False)
    return db_engine
