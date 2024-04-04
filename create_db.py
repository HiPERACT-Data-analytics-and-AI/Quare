from collections.abc import Callable
from pathlib import Path

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import Session

from db_models import DBBase, ProfilingSession


def _load_machine_info(path: Path) -> None: ...


def _load_further_machine_info(path: Path) -> None: ...


def _load_machine_cpu_topology(path: Path) -> None: ...


def _load_core_metrics(path: Path) -> None: ...


def _load_l3_metrics(path: Path) -> None: ...


def load_uprof_pcm(db_session: Session) -> None:
    FILE_SUFFIXES: list[tuple[str, Callable[[Path], None]]] = [
        ("machine_info.csv", _load_machine_info),
        ("further_machine_info.csv", _load_further_machine_info),
        ("machine_cpu_topology.csv", _load_machine_cpu_topology),
        ("core_metrics.csv", _load_core_metrics),
        ("l3_metrics.csv", _load_l3_metrics),
    ]

    for input_path in Path("csvized_data").glob(f"**/*.{FILE_SUFFIXES[0][0]}"):
        general_path: Path = input_path.parent
        name_base: str = input_path.name[: -len(FILE_SUFFIXES[0][0])]

        for suffix, function in FILE_SUFFIXES:
            path: Path = general_path / (name_base + suffix)
            function(path)


def main():
    db_engine: Engine = create_engine("sqlite:///quare.sqlite3", echo=False)
    # DBBase.metadata.create_all(db_engine)

    session: ProfilingSession = ProfilingSession()

    path_structure_parts: dict = {
        0: session.name,
        2: session.use_case,
        3: session.machine,
        5: session.task_size,
    }

    with Session(db_engine) as db_session:
        for data_path in Path("csvized_data").glob("[0-9]*"):
            print(data_path.name)
            load_uprof_pcm(db_session)


if __name__ == "__main__":
    main()
