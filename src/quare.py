from argparse import ArgumentParser, Namespace
from collections.abc import Callable

from create_db import create_db
from csvize import csvize
from plot import plot


def main() -> None:
    commands: dict[str, Callable[[Namespace], None]] = {
        "csvize": csvize,
        "create-db": create_db,
        "plot": plot,
    }
    parser = ArgumentParser()
    subparsers = parser.add_subparsers(title="Tools", required=True, dest="command")

    subparsers.add_parser("csvize")
    # csvize_parser = subparsers.add_parser("csvize")
    # csvize_parser.add_argument(
    #     "-s",
    #     "--source",
    #     action="extend",
    #     nargs="+",
    #     type=str,
    #     dest="source",
    # )
    # csvize_parser.add_argument(
    #     "-d",
    #     "--destination",
    #     action="extend",
    #     nargs="+",
    #     type=str,
    #     dest="destination",
    # )
    subparsers.add_parser("create-db")
    subparsers.add_parser("plot")

    args = parser.parse_args()
    commands[args.command](args)


if __name__ == "__main__":
    main()
