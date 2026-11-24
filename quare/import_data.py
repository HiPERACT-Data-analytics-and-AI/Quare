"""
``import-data`` subcommand: convert a measurement tree with a foreign layout
into the raw data layout used by ``preprocess-data``.

Usage::

    quare import-data --layout motorbike-2024|motorbike-2026|uap --source DIR --map FILE
"""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from pathlib import Path

from .importers import motorbike2024, motorbike2026, uap
from .utils import load_settings

IMPORTERS = {
    "motorbike-2024": motorbike2024,
    "motorbike-2026": motorbike2026,
    "uap": uap,
}
"""Available importers, by the name given to ``--layout``."""


def add_arguments(parser: ArgumentParser) -> None:
    """
    Register ``--layout`` and the arguments shared by all importers.

    :param parser: Parser of the ``import-data`` command.
    :type parser: argparse.ArgumentParser
    """
    parser.add_argument("--layout", choices=sorted(IMPORTERS), required=True)
    parser.add_argument(
        "--source", type=Path, required=True, help="root of the measurement tree"
    )
    parser.add_argument(
        "--map", type=Path, required=True, help="JSON mapping file (see examples/)"
    )
    parser.add_argument(
        "--machine",
        action="append",
        help="machine name to import (repeatable; default: all in the mapping)",
    )


def import_data(args: Namespace) -> None:
    """
    Run the importer selected with ``--layout``.

    The target is ``raw_data_directory_path`` from the settings.

    :param args: Parsed command-line arguments.
    :type args: argparse.Namespace
    """
    raw_data_path = Path(load_settings()["raw_data_directory_path"])
    IMPORTERS[args.layout].run(args, raw_data_path)
