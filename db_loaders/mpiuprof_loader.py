from collections.abc import Callable
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from db_models.mpiuprof_models import (
    MPIuProf_environment,
    MPIuProf_functions_dict,
    MPIuProf_functions_summary,
    MPIuProf_rank_summary,
)

from .uprof_utils import MetricContext, walk_through_sessions


class InMemoryTables:
    functions_dict: dict[str, int] = {}

    @classmethod
    def update_functions_dict(cls, db_session: Session) -> None:
        functions_dict_list = db_session.execute(
            select(MPIuProf_functions_dict.id, MPIuProf_functions_dict.name)
        ).all()
        cls.functions_dict = {row[1]: row[0] for row in functions_dict_list}


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

    walk_through_sessions(data_dir_path, db_session, FILE_SUFFIXES)
