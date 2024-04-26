from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from db_models import Machine, ProfilingSession, UseCase
from db_models.mpiuprof_models import (
    MPIuProf_environment,
    MPIuProf_functions_dict,
    MPIuProf_functions_summary,
    MPIuProf_rank_summary,
)

from .utils import create_if_not_exists, extract_from_path


class InMemoryTables:
    functions_dict: dict[str, int] = {}

    @classmethod
    def update_functions_dict(cls, db_session: Session) -> None:
        functions_dict_list = db_session.execute(
            select(MPIuProf_functions_dict.id, MPIuProf_functions_dict.name)
        ).all()
        cls.functions_dict = {row[1]: row[0] for row in functions_dict_list}


@dataclass
class MetricContext:
    path: Path
    session_id: int
    db_session: Session


def _load_environment(context: MetricContext) -> list[MPIuProf_environment]:
    try:
        environment_csv = pd.read_csv(context.path, header=None, index_col=0).T
    except FileNotFoundError:
        return []
    row = environment_csv.iloc[0]

    environment_uprof = MPIuProf_environment(
        profiling_session=context.session_id,
        total_ranks=row.get("TOTAL RANKS ", default=None),
        lib_version=row.get("LIB VERSION ", default=None),
        std_version=row.get("STD VERSION ", default=None),
    )
    return [environment_uprof]


def _load_functions_summary(context: MetricContext) -> list[MPIuProf_functions_summary]:
    try:
        summary_csv = pd.read_csv(context.path)
    except FileNotFoundError:
        return []

    instances_to_add: list[MPIuProf_functions_summary] = list()
    for _, row in summary_csv.iterrows():
        if row.get("Function") not in InMemoryTables.functions_dict.keys():
            function = MPIuProf_functions_dict(name=row.get("Function"))
            context.db_session.add(function)
            context.db_session.commit()
            InMemoryTables.update_functions_dict(context.db_session)

        instance = MPIuProf_functions_summary(
            profiling_session=context.session_id,
            function=InMemoryTables.functions_dict[str(row.get("Function"))],
            min_time=row.get("Min Time(seconds)", default=None),
            max_time=row.get("Max Time(seconds)", default=None),
            average_time=row.get("Average Time(seconds)", default=None),
            mpi_time_percent=row.get("MPI Time(%)", default=None),
            volume=row.get("Volume(Bytes)", default=None),
            calls=row.get("Calls", default=None),
            total_time=row.get("Total Time(seconds)", default=None),
        )
        instances_to_add.append(instance)
    return instances_to_add


def _load_rank_summary(context: MetricContext) -> list[MPIuProf_rank_summary]:
    try:
        summary_csv = pd.read_csv(context.path)
    except FileNotFoundError:
        return []

    instances_to_add: list[MPIuProf_rank_summary] = list()
    for _, row in summary_csv.iterrows():
        instance = MPIuProf_rank_summary(
            profiling_session=context.session_id,
            rank=row.get("Rank", default=None),
            pid=row.get("PID", default=None),
            mpi_time=row.get("MPI Time(seconds)", default=None),
            mpi_time_percent=row.get("MPI Time(%)", default=None),
            wait_time=row.get("Wait Time(seconds)", default=None),
            call_count=row.get("Call Count", default=None),
            volume=row.get("Volume(Bytes)", default=None),
        )
        instances_to_add.append(instance)
    return instances_to_add


def load_mpiuprof(db_session: Session, data_dir_path: Path) -> None:
    InMemoryTables.update_functions_dict(db_session)

    FILE_SUFFIXES: list[tuple[str, Callable[[MetricContext], list]]] = [
        ("environment.csv", _load_environment),
        ("functions_summary.csv", _load_functions_summary),
        ("rank_summary.csv", _load_rank_summary),
    ]

    for input_path in Path(data_dir_path).glob(f"**/*.{FILE_SUFFIXES[0][0]}"):
        general_path: Path = input_path.parent
        name_base: str = input_path.name[: -len(FILE_SUFFIXES[0][0])]

        machine_name = extract_from_path("machine", input_path)
        machine = Machine(name=machine_name)
        machine = create_if_not_exists(
            db_session=db_session,
            to_create=machine,
            where_column=Machine.name,
            equal_to=machine_name,
        )

        use_case_name = extract_from_path("use_case", input_path)
        use_case = UseCase(name=use_case_name)
        use_case = create_if_not_exists(
            db_session=db_session,
            to_create=use_case,
            where_column=UseCase.name,
            equal_to=use_case_name,
        )

        db_session.commit()  # the commit needed to obtain the ids of the added objects

        session_name = extract_from_path("session", input_path)
        session = ProfilingSession(
            name=session_name,
            use_case=use_case.id,
            task_size=extract_from_path("task_size", input_path),
            machine=machine.id,
        )
        session = create_if_not_exists(
            db_session=db_session,
            to_create=session,
            where_column=ProfilingSession.name,
            equal_to=session_name,
        )

        db_session.commit()

        for suffix, function in FILE_SUFFIXES:
            path: Path = general_path / (name_base + suffix)
            db_session.add_all(
                function(
                    MetricContext(
                        path=path, session_id=session.id, db_session=db_session
                    )
                )
            )
