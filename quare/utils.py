"""
Shared utilities for the Quare toolkit.

Provides:

* In-memory caches for frequently-queried DB tables
  (:class:`InMemoryTaskSizesDict`, :class:`InMemoryMetricsDict`).
* Generic helper functions (:func:`divide_dict_into_chunks`).
* Extension discovery (:func:`discover_extensions`, :func:`get_extension_path`).
* Settings loading with path-override support (:func:`load_settings`,
  :func:`set_settings_path`).
* Database engine and session management (:func:`create_db_engine`,
  :func:`get_db_session`, :func:`close_db_session`).
"""

from __future__ import annotations

from itertools import islice
from json import load
from os import environ
from pathlib import Path
from typing import TypeVar

from sqlalchemy import Engine
from sqlalchemy import create_engine as _create_engine
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import MetricsDictBase, TaskSizesDict


class InMemoryTaskSizesDict:
    """
    In-memory mirror of the ``Task_sizes_dict`` database table.

    Keeps a local copy of all task-size records so loaders can look up IDs
    without issuing a query per row.  Call :meth:`update` to refresh after
    new rows are committed.

    :ivar rows: Mapping from task-size name to ``(id, numeric_size)`` pairs.
    :vartype rows: dict[str, tuple[int, int]]
    """

    def __init__(self, db_session: Session) -> None:
        """
        Initialise the cache and populate it immediately from the database.

        :param db_session: Active SQLAlchemy session used for all queries.
        :type db_session: sqlalchemy.orm.Session
        """
        self._db_session = db_session
        self.rows: dict[str, tuple[int, int]] = {}
        self.update()

    def update(self) -> None:
        """
        Reload :attr:`rows` from the ``Task_sizes_dict`` table.

        Should be called after new :class:`~quare.models.TaskSizesDict` rows
        have been committed so that subsequent look-ups reflect the latest
        database state.
        """
        results_list = self._db_session.execute(
            select(
                TaskSizesDict.id,
                TaskSizesDict.name,
                TaskSizesDict.size,
            )
        ).all()
        self.rows = {row.name: (row.id, row.size) for row in results_list}


class InMemoryMetricsDict:
    """
    In-memory mirror of a profiler-specific ``*_metrics_dict`` database table.

    Keeps a local copy of metric-dictionary records so that
    :class:`~quare.data_loader.DataLoader` can resolve metric IDs without
    a round-trip per value.  Call :meth:`update` to refresh after new rows
    are committed.

    :ivar rows: Mapping from a ``\\x00``-separated composite key
        ``"name\\x00unit\\x00processing_unit"`` to the metric-dictionary row ID.
    :vartype rows: dict[str, int]
    """

    def __init__(self, db_session: Session, table: type[MetricsDictBase]) -> None:
        """
        Initialise the cache for *table* and populate it immediately.

        :param db_session: Active SQLAlchemy session used for all queries.
        :type db_session: sqlalchemy.orm.Session
        :param table: The concrete :class:`~quare.models.MetricsDictBase`
            subclass whose rows should be cached (e.g.
            ``AMDuProfPCM_metrics_dict``).
        :type table: type[quare.models.MetricsDictBase]
        """
        self._db_session = db_session
        self._table = table
        self.rows: dict[str, int] = {}
        self.update()

    def update(self) -> None:
        """
        Reload :attr:`rows` from the backing metrics-dictionary table.

        Should be called after new metric-dictionary rows have been committed
        so that subsequent :meth:`~quare.data_loader.DataLoader.create_metric_instance`
        calls reflect the latest database state.
        """
        results_list = self._db_session.execute(
            select(
                self._table.id,
                self._table.name,
                self._table.unit,
                self._table.processing_unit,
            )
        ).all()
        self.rows = {
            f"{row.name}\x00{row.unit}\x00{row.processing_unit}": row.id
            for row in results_list
        }


T = TypeVar("T")
U = TypeVar("U")


def divide_dict_into_chunks(
    dict_to_splice: dict[T, U], max_size: int
) -> list[dict[T, U]]:
    """
    Split a dictionary into a list of smaller dictionaries.

    Insertion order is preserved.  The last chunk may be smaller than
    *max_size* if the total number of items is not a multiple of *max_size*.

    Example::

        divide_dict_into_chunks({"a": 1, "b": 2, "c": 3}, 2)
        # → [{"a": 1, "b": 2}, {"c": 3}]

    :param dict_to_splice: The source dictionary to partition.
    :type dict_to_splice: dict[T, U]
    :param max_size: Maximum number of key-value pairs per chunk.  Must be
        greater than zero.
    :type max_size: int
    :returns: A list of dictionaries, each containing at most *max_size* items.
    :rtype: list[dict[T, U]]
    """
    dict_items_iterator = iter(dict_to_splice.items())
    return [
        dict(islice(dict_items_iterator, max_size))
        for _ in range(0, len(dict_to_splice), max_size)
    ]


def discover_extensions() -> list[Path]:
    """
    Return absolute paths to all installed Quare extension directories.

    An extension is any sub-directory of ``quare/extensions/`` whose name
    ends with the ``_ext`` suffix (e.g. ``AMDuProfPCM_ext``).

    :returns: List of resolved :class:`~pathlib.Path` objects, one per
        discovered extension directory.  The list may be empty if no
        extensions are installed.
    :rtype: list[pathlib.Path]
    """
    extensions_path: Path = Path(__file__).parent / "extensions"
    return [path.resolve() for path in extensions_path.glob("*_ext")]


def get_extension_path(name: str) -> Path:
    """
    Return the absolute path to a named extension directory.

    The extension directory is expected at
    ``quare/extensions/<name>_ext``.

    :param name: Bare extension name without the ``_ext`` suffix
        (e.g. ``"AMDuProfPCM"``).
    :type name: str
    :returns: Resolved :class:`~pathlib.Path` to the extension directory.
    :rtype: pathlib.Path
    :raises ValueError: If no directory named ``<name>_ext`` exists under
        ``quare/extensions/``.
    """
    extension_path: Path = Path(__file__).parent / "extensions" / f"{name}_ext"
    if not extension_path.exists():
        raise ValueError(f'Extension "{name}" does not exist')
    return extension_path.resolve()


# ---------------------------------------------------------------------------
# Settings management
# ---------------------------------------------------------------------------

_settings_cache: dict | None = None
_settings_path_override: Path | None = None

FALLBACK_SETTINGS_PATH: Path = Path(__file__).parent / "settings.json"
"""
Absolute path to the ``settings.json`` shipped with the package.

Used as a last-resort default when neither :func:`set_settings_path` nor the
``QUARE_SETTINGS`` environment variable have been set.
"""

SETTINGS_PATH_ENV_VAR = "QUARE_SETTINGS"
"""
Name of the environment variable that can point to a custom settings file.

Set this variable to an absolute path before running Quare to avoid editing
the bundled ``settings.json``.  Example::

    export QUARE_SETTINGS=/home/user/my_project/settings.json
"""


def set_settings_path(path: Path) -> None:
    """
    Override the settings file path used by :func:`load_settings`.

    Clears the settings cache so the next call to :func:`load_settings` reads
    from *path*.  Intended to be called once at startup — typically from
    :func:`~quare.__main__.main` when the user passes ``--config``.

    :param path: Absolute or relative path to a ``settings.json`` file.
    :type path: pathlib.Path
    """
    global _settings_path_override, _settings_cache
    _settings_path_override = path
    _settings_cache = None


def load_settings() -> dict:
    """
    Load and cache the Quare settings file.

    The settings file is located by consulting three sources in order of
    decreasing precedence:

    1. A path set explicitly via :func:`set_settings_path` (or ``--config``).
    2. The ``QUARE_SETTINGS`` environment variable.
    3. The ``settings.json`` bundled with the package (:data:`FALLBACK_SETTINGS_PATH`).

    Path-valued keys (``raw_data_directory_path``,
    ``preprocessed_data_directory_path``, ``db_path``,
    ``output_directory_path``) are converted from relative strings — relative
    to the settings file's own directory — into resolved :class:`~pathlib.Path`
    objects before being returned.

    Results are cached in ``_settings_cache`` after the first successful load;
    subsequent calls return the cached copy.  The cache is invalidated by
    :func:`set_settings_path`.

    :returns: Dictionary of all settings keys and their (converted) values.
    :rtype: dict
    :raises FileNotFoundError: If the resolved settings file does not exist.
    :raises json.JSONDecodeError: If the settings file contains invalid JSON.
    """
    global _settings_cache
    if _settings_cache is not None:
        return _settings_cache

    KEYS_WITH_PATHS: tuple[str, ...] = (
        "raw_data_directory_path",
        "preprocessed_data_directory_path",
        "db_path",
        "output_directory_path",
    )

    if _settings_path_override is not None:
        settings_path = _settings_path_override
    elif SETTINGS_PATH_ENV_VAR in environ:
        settings_path = Path(environ[SETTINGS_PATH_ENV_VAR])
    else:
        settings_path = FALLBACK_SETTINGS_PATH

    with open(settings_path) as settings_file:
        settings = load(settings_file)
        for key in KEYS_WITH_PATHS:
            settings[key] = (settings_path.parent / settings[key]).resolve()
        _settings_cache = settings
        return settings


# ---------------------------------------------------------------------------
# Database engine / session
# ---------------------------------------------------------------------------

def create_db_engine() -> Engine:
    """
    Create an SQLAlchemy engine connected to the configured SQLite database.

    The database file path is read from :func:`load_settings` (key
    ``"db_path"``).  Each call constructs a new engine; callers that need a
    shared engine should cache the result themselves or use
    :func:`get_db_session`.

    :returns: A configured :class:`sqlalchemy.engine.Engine` instance.
    :rtype: sqlalchemy.engine.Engine
    """
    settings = load_settings()
    return _create_engine(f"sqlite:///{settings['db_path']}", echo=False)


session: Session | None = None
"""
Module-level singleton database session.

Managed exclusively through :func:`get_db_session` and
:func:`close_db_session`.  Direct access is discouraged.
"""


def get_db_session() -> Session:
    """
    Return the module-level singleton :class:`~sqlalchemy.orm.Session`.

    Creates a new session (and underlying engine) on the first call; returns
    the cached session on subsequent calls.

    :returns: The active database session.
    :rtype: sqlalchemy.orm.Session
    """
    global session
    if not session:
        session = Session(create_db_engine())
    return session


def close_db_session() -> None:
    """
    Close the module-level singleton session and release its resources.

    Safe to call even if the session has not been opened.  After this call,
    the next :func:`get_db_session` invocation will open a fresh session.
    """
    global session
    if session:
        session.close()
        session = None
