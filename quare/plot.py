"""
``plot`` subcommand: generate plots, CSV exports, and INFO tables from the
database.

For each extension that has a ``plotter.py``, the module is imported
dynamically.  The module must expose:

* ``__extension_data_plotter__`` — a :class:`~quare.plotter.Plotter` subclass
  (or :class:`~quare.plotter.Plotter` itself) to instantiate.

The plotter's :meth:`~quare.plotter.Plotter.make_all` is then called to
produce all configured outputs.

This module can also be executed directly::

    python -m quare.plot
"""

from argparse import Namespace
from importlib import util

from .utils import close_db_session, discover_extensions


def plot(_: Namespace) -> None:
    """
    Discover all extensions and run their plotting pipelines.

    For each installed extension that contains a ``plotter.py``, the module is
    imported and its ``__extension_data_plotter__`` class is instantiated with
    the extension's bare name (without the ``_ext`` suffix).  The instance's
    :meth:`~quare.plotter.Plotter.make_all` method is called to generate plots,
    CSV files, and INFO tables.

    The database session is closed in a ``finally`` block regardless of
    whether plotting succeeds or raises.

    Extensions without a ``plotter.py`` are silently skipped.

    :param _: Parsed CLI namespace (unused; reserved for future per-extension
        flags).
    :type _: argparse.Namespace
    """
    try:
        for extension_path in discover_extensions():
            path = extension_path / "plotter.py"
            if not path.exists():
                continue
            spec = util.spec_from_file_location(path.stem, path)
            if spec is not None:
                module = util.module_from_spec(spec)
                if spec.loader is not None:
                    module.__package__ = "quare.extensions." + extension_path.stem
                    spec.loader.exec_module(module)
                    module.__extension_data_plotter__(
                        extension_path.stem[: -len("_ext")]
                    ).make_all()
    finally:
        close_db_session()


if __name__ == "__main__":
    plot(Namespace())
