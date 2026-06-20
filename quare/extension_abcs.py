"""
Abstract base classes that define the public contract for Quare extensions.

Every profiler extension must expose a class that implements
:class:`ExtensionDataLoader` so that :func:`~quare.create_db.create_db` can
invoke it without knowing the extension's internals.
"""

from abc import ABC, abstractmethod
from pathlib import Path


class ExtensionDataLoader(ABC):
    """
    Abstract contract for loading preprocessed profiler data into the database.

    Each extension's ``loader.py`` must expose a concrete subclass named
    ``ExtensionDataLoaderImpl`` that implements :meth:`load`.

    Example skeleton::

        class ExtensionDataLoaderImpl(ExtensionDataLoader):
            @staticmethod
            def load(data_dir_path: Path) -> None:
                # walk data_dir_path, insert rows via DataLoader helpers …
    """

    @staticmethod
    @abstractmethod
    def load(data_dir_path: Path) -> None:
        """
        Load all preprocessed profiler data found under *data_dir_path* into
        the active database session.

        Implementations should use :class:`~quare.data_loader.DataLoader`
        helpers and commit via the shared session obtained from
        :func:`~quare.utils.get_db_session`.

        :param data_dir_path: Root directory that contains preprocessed CSV
            files organised in the canonical
            ``<session>/<machine>/<use_case>/<task_size>/<date>/`` hierarchy.
        :type data_dir_path: pathlib.Path
        """
