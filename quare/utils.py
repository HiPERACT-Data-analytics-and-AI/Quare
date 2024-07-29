from itertools import islice
from json import load
from pathlib import Path
from typing import TypeVar

from sqlalchemy import Engine
from sqlalchemy import create_engine as _create_engine
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import MetricsDictBase, TaskSizesDict


class InMemoryTaskSizesDict:
    """_summary_"""

    _db_session: Session | None = None
    """member description"""
    rows: dict[str, tuple[int, int]] = {}
    """member description"""

    @classmethod
    def initialize(cls, db_session: Session) -> None:
        """_summary_

        :param db_session: _description_
        """
        cls._db_session = db_session
        cls.update()

    @classmethod
    def update(cls) -> None:
        """_summary_

        :raises Exception: _description_
        """
        if not cls._db_session:
            raise Exception("Class not initialized")
        results_list = cls._db_session.execute(
            select(
                TaskSizesDict.id,
                TaskSizesDict.name,
                TaskSizesDict.size,
            )
        ).all()
        cls.rows = {row[1]: (row[0], row[2]) for row in results_list}


class InMemoryMetricsDict:
    """_summary_"""

    # A little wet code in this class but not overly complicated
    _table: type[MetricsDictBase]
    """member description"""
    _db_session: Session | None = None
    """member description"""
    rows: dict[str, int] = {}
    """member description"""

    @classmethod
    def initialize(cls, db_session: Session, table: type[MetricsDictBase]) -> None:
        """_summary_

        :param db_session: _description_
        :param table: _description_
        """
        cls._db_session = db_session
        cls._table = table
        cls.update()

    @classmethod
    def update(cls) -> None:
        """_summary_

        :raises Exception: _description_
        """
        if not cls._db_session:
            raise Exception("Class not initialized")
        results_list = cls._db_session.execute(
            select(
                cls._table.id,
                cls._table.name,
                cls._table.unit,
                cls._table.processing_unit,
            )
        ).all()
        cls.rows = {str(row[1]) + str(row[2]) + row[3]: row[0] for row in results_list}


T = TypeVar("T")
U = TypeVar("U")


def divide_dict_into_chunks(
    dict_to_splice: dict[T, U], max_size: int
) -> list[dict[T, U]]:
    """
    _summary_

    :param dict_to_splice: _description_
    :param max_size: _description_
    :return: _description_
    """
    dict_items_iterator = iter(dict_to_splice.items())
    return [
        dict(islice(dict_items_iterator, max_size))
        for _ in range(0, len(dict_to_splice), max_size)
    ]


def discover_extensions() -> list[Path]:
    extensions_path: Path = Path(__file__).parent / "extensions"
    return [path for path in extensions_path.glob("*_ext")]


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

    # TODO Check for inconsistent repetitions and warn the user if exist

    return db_engine
