from argparse import Namespace
from importlib import util

from .utils import close_db_session, discover_extensions


def plot(_: Namespace) -> None:
    """
    Plots chosen or all the metrics (depends on settings), creates INFO plot and CSV
    file with data that has been used to make plots.

    The data is plotted by profiler-specific extensions. A specific extension can be
    temporarily hidden in a way described in :py:func:`.create_db.create_db`.
    """
    for extension_path in discover_extensions():
        path = extension_path / "plotter.py"
        spec = util.spec_from_file_location(path.stem, path)
        if spec is not None:
            module = util.module_from_spec(spec)
            if spec.loader is not None:
                module.__package__ = "quare.extensions." + extension_path.stem
                spec.loader.exec_module(module)
                module.__extension_data_plotter__(
                    extension_path.stem[: -len("_ext")]
                ).make_all()
    close_db_session()


if __name__ == "__main__":
    plot(Namespace())
