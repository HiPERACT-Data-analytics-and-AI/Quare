"""
``preprocess-data`` subcommand: transform raw profiler output into a
normalised directory layout ready for database loading.

Each discovered extension's ``preprocessor.py`` module exposes a class
assigned to ``__extension_data_preprocessor__``.  :func:`preprocess`
instantiates that class (which must be a subclass of
:class:`~quare.preprocessor.Preprocessor`) and calls its
:meth:`~quare.preprocessor.Preprocessor.preprocess` method.

This module can also be executed directly::

    python -m quare.preprocess
"""

from argparse import Namespace
from importlib import util
from pathlib import Path

from .utils import discover_extensions, load_settings


def preprocess(_: Namespace) -> None:
    """
    Discover all extensions and run their preprocessors.

    Reads the ``raw_data_directory_path`` and
    ``preprocessed_data_directory_path`` entries from the active settings,
    creates the preprocessed-data directory if it does not exist, then
    iterates over every installed extension.  For each extension that contains
    a ``preprocessor.py``, the module is imported dynamically and its
    ``__extension_data_preprocessor__`` class is instantiated and executed.

    Extensions that lack a ``preprocessor.py`` are silently skipped.

    :param _: Parsed CLI namespace (unused; reserved for future per-extension
        flags).
    :type _: argparse.Namespace
    :raises FileNotFoundError: If ``raw_data_directory_path`` does not exist.
    """
    settings = load_settings()
    raw_data_path: Path = Path(settings["raw_data_directory_path"])
    preprocessed_data_path: Path = Path(settings["preprocessed_data_directory_path"])

    if not raw_data_path.exists():
        raise FileNotFoundError(raw_data_path.resolve().as_posix())

    preprocessed_data_path.mkdir(parents=True, exist_ok=True)

    for extension_path in discover_extensions():
        path = extension_path / "preprocessor.py"
        spec = util.spec_from_file_location(path.stem, path)
        if spec is not None:
            module = util.module_from_spec(spec)
            if spec.loader is not None:
                module.__package__ = "quare.extensions." + extension_path.stem
                spec.loader.exec_module(module)
                module.__extension_data_preprocessor__(
                    extension_path.stem[: -len("_ext")],
                    raw_data_path,
                    preprocessed_data_path,
                ).preprocess()


if __name__ == "__main__":
    preprocess(Namespace())
