"""
Entry point module for the Quare command-line interface.

Running ``python -m quare <command>`` (or the installed ``quare`` script) lands
here.  Each subcommand maps to a single workflow function:

* ``preprocess-data`` — split / copy raw profiler files into a normalised layout.
* ``create-db``       — load preprocessed files into the SQLite database.
* ``plot``            — query the database and generate plots / CSV exports.
"""

from argparse import ArgumentParser, Namespace
from collections.abc import Callable
from pathlib import Path

from .create_db import create_db
from .plot import plot
from .preprocess import preprocess
from .utils import close_db_session, set_settings_path


def _add_common_args(subparser: ArgumentParser) -> None:
    """
    Attach arguments that are shared by every subcommand to *subparser*.

    Currently registers ``--config`` so users can point to a custom
    ``settings.json`` without modifying the one bundled with the package.

    :param subparser: The :class:`~argparse.ArgumentParser` instance for a
        specific subcommand, as returned by
        :meth:`~argparse.ArgumentParser.add_parser`.
    :type subparser: argparse.ArgumentParser
    """
    subparser.add_argument(
        "--config",
        metavar="PATH",
        type=Path,
        default=None,
        help=(
            "Path to a settings.json file.  Overrides the QUARE_SETTINGS "
            "environment variable and the settings.json bundled with the package."
        ),
    )


def main() -> None:
    """
    Entry point for the Quare toolkit.

    Parses command-line arguments, optionally overrides the settings path,
    dispatches to the requested subcommand function, and guarantees that the
    database session is closed on exit (even when the subcommand raises).

    Subcommands
    -----------
    preprocess-data
        Call :func:`~quare.preprocess.preprocess`.
    create-db
        Call :func:`~quare.create_db.create_db`.
    plot
        Call :func:`~quare.plot.plot`.

    :raises SystemExit: When ``--help`` is passed or required arguments are
        missing (standard :mod:`argparse` behaviour).
    """
    commands: dict[str, Callable[[Namespace], None]] = {
        "preprocess-data": preprocess,
        "create-db": create_db,
        "plot": plot,
    }
    parser = ArgumentParser(prog="quare")
    subparsers = parser.add_subparsers(title="Tools", required=True, dest="command")

    for name in commands:
        _add_common_args(subparsers.add_parser(name))

    args = parser.parse_args()

    if args.config is not None:
        set_settings_path(args.config)

    try:
        commands[args.command](args)
    finally:
        close_db_session()


if __name__ == "__main__":
    main()
