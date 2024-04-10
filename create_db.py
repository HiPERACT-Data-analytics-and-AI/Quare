from collections.abc import Callable
from pathlib import Path

import pandas as pd
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from db_models import DBBase, Machine, ProfilingSession, amduprofpcm_models

path_struct: dict[str, tuple[int, ...]] = {
    "use_case": (2,),
    "machine": (3,),
    "task_size": (5,),
    "session": (3, 4, 5, 6, 7),
}


def _extract_from_path(key: str, path: Path) -> str:
    return ".".join(path.parts[i] for i in path_struct[key])


def _load_machine_info(path: Path, session: ProfilingSession) -> object:
    machine_csv = pd.read_csv(path, header=None).T
    # for i, row in machine_csv.iterrows():
    #     print("\n\n\n", row, "\n\n\n")
    print("\n\n\n", machine_csv.iloc[1].to_dict(), "\n\n\n")
    converted = machine_csv.iloc[1].to_dict()
    machine_uprof = amduprofpcm_models.AMDuProfPcm_machine_info(
        profiling_session=session.name,
        system=converted[0],
        num_of_sockets=converted[1],
        num_of_ccds=converted[2],
        num_of_cores=converted[3],
        num_of_threads=converted[4],
        smt_enabled_in_hw=converted[5],
        smt_enabled_in_os=converted[6],
        num_of_threads_sharing_l3=converted[7],
    )
    return machine_uprof


def _load_further_machine_info(path: Path, session: ProfilingSession) -> object: ...


def _load_machine_cpu_topology(path: Path, session: ProfilingSession) -> object: ...


def _load_core_metrics(path: Path, session: ProfilingSession) -> object: ...


def _load_l3_metrics(path: Path, session: ProfilingSession) -> object: ...


def load_uprof_pcm(db_session: Session) -> None:
    FILE_SUFFIXES: list[tuple[str, Callable[[Path, ProfilingSession], object]]] = [
        ("machine_info.csv", _load_machine_info),
        ("further_machine_info.csv", _load_further_machine_info),
        ("machine_cpu_topology.csv", _load_machine_cpu_topology),
        ("core_metrics.csv", _load_core_metrics),
        ("l3_metrics.csv", _load_l3_metrics),
    ]

    for input_path in Path("csvized_data").glob(f"**/*.{FILE_SUFFIXES[0][0]}"):
        general_path: Path = input_path.parent
        name_base: str = input_path.name[: -len(FILE_SUFFIXES[0][0])]

        machine = Machine(name=_extract_from_path("machine", input_path))
        db_session.add(machine)
        db_session.commit()

        session = ProfilingSession(
            name=_extract_from_path("session", input_path),
            use_case=_extract_from_path("use_case", input_path),
            task_size=_extract_from_path("task_size", input_path),
            machine=machine.id,
        )

        db_session.add(session)

        for suffix, function in FILE_SUFFIXES:
            path: Path = general_path / (name_base + suffix)
            # db_session.add(function(path, session))

        db_session.commit()


def main():
    db_engine: Engine = create_engine("sqlite:///quare.sqlite3", echo=False)
    DBBase.metadata.create_all(db_engine)

    with Session(db_engine) as db_session:
        # for data_path in Path("csvized_data").glob("[0-9]*"):
        #     print(data_path)
        load_uprof_pcm(db_session)
        db_session.commit()


if __name__ == "__main__":
    main()
