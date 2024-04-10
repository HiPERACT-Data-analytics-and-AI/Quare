from collections.abc import Callable
from pathlib import Path

import pandas as pd
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from db_models import DBBase, Machine, UseCase, ProfilingSession, amduprofpcm_models

path_struct: dict[str, tuple[int, ...]] = {
    "use_case": (2,),
    "machine": (3,),
    "task_size": (5,),
    "session": (3, 4, 5, 6, 7),
}


def _extract_from_path(key: str, path: Path) -> str:
    return ".".join(path.parts[i] for i in path_struct[key])


def _load_machine_info(path: Path, session: ProfilingSession) -> amduprofpcm_models.AMDuProfPcm_machine_info:
    machine_csv = pd.read_csv(path, header=None, index_col=0).T
    # for i, row in machine_csv.iterrows():
    #     print("\n\n\n", row, "\n\n\n")
    # print("\n\n\n", type(machine_csv.iloc[0].get("SMT Enabled in HW:")), "\n\n\n")
    row = machine_csv.iloc[0]

    machine_uprof = amduprofpcm_models.AMDuProfPcm_machine_info(
        profiling_session=session.name,
        system=row.get("System:", default=None),
        num_of_sockets=row.get("Number of Sockets :", default=None),
        num_of_ccds=row.get("Number of CCDs :", default=None),
        num_of_ccxs=row.get("Number of Core Complexes(CCX) :", default=None),
        num_of_cores=row.get("Number of Cores :", default=None),
        num_of_threads=row.get("Number of Threads :", default=None),
        smt_enabled_in_hw=bool(row.get("SMT Enabled in HW:")),
        smt_enabled_in_os=bool(row.get("SMT Enabled by OS :")),
        num_of_threads_sharing_l3=row.get("Number of Threads sharing L3:", default=None),
    )
    return machine_uprof


def _load_further_machine_info(path: Path, session: ProfilingSession) -> DBBase: ...


def _load_machine_cpu_topology(path: Path, session: ProfilingSession) -> DBBase: ...


def _load_core_metrics(path: Path, session: ProfilingSession) -> DBBase: ...


def _load_l3_metrics(path: Path, session: ProfilingSession) -> DBBase: ...


def load_uprof_pcm(db_session: Session) -> None:
    FILE_SUFFIXES: list[tuple[str, Callable[[Path, ProfilingSession], DBBase]]] = [
        ("machine_info.csv", _load_machine_info),
        # ("further_machine_info.csv", _load_further_machine_info),
        # ("machine_cpu_topology.csv", _load_machine_cpu_topology),
        # ("core_metrics.csv", _load_core_metrics),
        # ("l3_metrics.csv", _load_l3_metrics),
    ]

    for input_path in Path("csvized_data").glob(f"**/*.{FILE_SUFFIXES[0][0]}"):
        general_path: Path = input_path.parent
        name_base: str = input_path.name[: -len(FILE_SUFFIXES[0][0])]

        machine = Machine(name=_extract_from_path("machine", input_path))
        db_session.add(machine)

        use_case = UseCase(name=_extract_from_path("use_case", input_path))
        db_session.add(use_case)

        session = ProfilingSession(
            name=_extract_from_path("session", input_path),
            use_case=_extract_from_path("use_case", input_path),
            task_size=_extract_from_path("task_size", input_path),
            machine=machine.name,
        )
        db_session.add(session)

        for suffix, function in FILE_SUFFIXES:
            path: Path = general_path / (name_base + suffix)
            db_session.add(function(path, session))


def main():
    db_engine: Engine = create_engine("sqlite:///quare.sqlite3", echo=False)
    DBBase.metadata.create_all(db_engine)

    with Session(db_engine) as db_session:
        load_uprof_pcm(db_session)
        db_session.commit()


if __name__ == "__main__":
    main()
