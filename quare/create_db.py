"""
``create-db`` subcommand: initialise the SQLite database and load all
preprocessed profiler data.

The workflow is:

1. Dynamically import every extension's ``models.py`` so that the extension's
   ORM classes are registered with :class:`~quare.models.DBBase`.
2. Call ``DBBase.metadata.create_all(engine)`` to create any missing tables.
3. For each extension that has a ``loader.py``, instantiate its
   ``ExtensionDataLoaderImpl`` and call
   :meth:`~quare.extension_abcs.ExtensionDataLoader.load`.

Extensions without a ``models.py`` or ``loader.py`` are silently skipped.

This module can also be executed directly::

    python -m quare.create_db
"""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from .models import DBBase
from .utils import (
    close_db_session,
    create_db_engine,
    discover_extensions,
    get_db_session,
    import_extension_module,
    load_settings,
)


def create_db(_: Namespace) -> None:
    """
    Create the database schema and load all preprocessed profiler data.

    Iterates over all installed extensions twice:

    * **First pass** — imports each extension's ``models.py`` to register its
      ORM table definitions with :class:`~quare.models.DBBase`, then calls
      ``DBBase.metadata.create_all`` to create any tables that do not yet
      exist.
    * **Second pass** — imports each extension's ``loader.py`` and calls its
      ``ExtensionDataLoaderImpl().load(data_dir_path)``, committing after each
      extension completes.

    The database session is closed in a ``finally`` block regardless of
    whether loading succeeds or raises.

    .. note::
        There is currently no option to run only specific extensions.  As a
        workaround, temporarily rename the extension directory to remove the
        ``_ext`` suffix to hide it from discovery.

    :param _: Parsed CLI namespace (unused; reserved for future per-extension
        flags).
    :type _: argparse.Namespace
    """
    settings = load_settings()
    data_dir_path = Path(settings["preprocessed_data_directory_path"])

    for extension_path in discover_extensions():
        import_extension_module(extension_path, "models")

    DBBase.metadata.create_all(create_db_engine())

    try:
        for extension_path in discover_extensions():
            module = import_extension_module(extension_path, "loader")
            if module is None:
                continue
            module.ExtensionDataLoaderImpl().load(data_dir_path)
            get_db_session().commit()
    finally:
        close_db_session()


if __name__ == "__main__":
    create_db(Namespace())
