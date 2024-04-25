from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session
from .utils import create_if_not_exists, extract_from_path

from db_models import Machine, ProfilingSession, UseCase
from db_models.mpiuprof_models import (
    MPIuProf_environment,
    MPIuProf_functions_dict,
    MPIuProf_functions_summary,
    MPIuProf_rank_summary,
)


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
    ...


def _load_functions_summary(context: MetricContext) -> list[MPIuProf_functions_summary]:
    ...


def _load_rank_summary(context: MetricContext) -> list[MPIuProf_rank_summary]:
    ...


def load_mpiuprof(db_session: Session, data_dir_path: Path) -> None:
    InMemoryTables.update_functions_dict

    FILE_SUFFIXES: list[tuple[str, Callable[[MetricContext], list]]] = [
        ("environment.csv", _load_environment),
        ("functions_summary.csv", _load_functions_summary),
        ("rank_summary.csv", _load_rank_summary),
    ]
