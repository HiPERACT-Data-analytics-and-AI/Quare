from collections.abc import Callable
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from db_models.amduprofmpi_models import (
    AMDuProfMPI_environment,
    AMDuProfMPI_metrics,
    AMDuProfMPI_metrics_dict,
)

from .amduprof_loaders_utils import (
    InMemoryTables,
    MetricContext,
    create_metric_instance,
    load_generic_metrics,
    walk_through_data,
)


def _load_environment(context: MetricContext) -> list[AMDuProfMPI_environment]:
    """
    _summary_

    :param context: _description_
    :return: _description_
    """
    try:
        environment_csv = pd.read_csv(context.path, header=None, index_col=0).T
    except FileNotFoundError:
        return []

    row = environment_csv.iloc[0]
    environment_uprof = AMDuProfMPI_environment(
        repetition=context.repetition_id,
        total_ranks=row.get("TOTAL RANKS ", default=None),
        lib_version=row.get("LIB VERSION ", default=None),
        std_version=row.get("STD VERSION ", default=None),
    )
    return [environment_uprof]


def _load_functions_summary(
    context: MetricContext,
) -> list[AMDuProfMPI_metrics]:
    """
    _summary_

    :param context: _description_
    :return: _description_
    """
    try:
        metrics_csv = pd.read_csv(context.path, header=0, index_col=0)
    except FileNotFoundError:
        return []

    InMemoryTables.update_metrics_dict(context.db_session, AMDuProfMPI_metrics_dict)
    instances_to_add: list[AMDuProfMPI_metrics] = list()
    for _, row in metrics_csv.iterrows():
        for name, value in row.items():
            instance = create_metric_instance(
                context,
                str(f"{row.name} | {name}"),
                value,
                None,
                "function",
                AMDuProfMPI_metrics,
                AMDuProfMPI_metrics_dict,
            )
            instances_to_add.append(instance)
    return instances_to_add


def _load_rank_summary(context: MetricContext) -> list[AMDuProfMPI_metrics]:
    """
    _summary_

    :param context: _description_
    :return: _description_
    """
    try:
        metrics_csv = pd.read_csv(context.path, header=0, index_col=0)
    except FileNotFoundError:
        return []

    return load_generic_metrics(
        context, metrics_csv, 0, "rank", AMDuProfMPI_metrics, AMDuProfMPI_metrics_dict
    )


def load_mpiuprof(db_session: Session, data_dir_path: Path) -> None:
    """
    _summary_

    :param db_session: _description_
    :param data_dir_path: _description_
    """
    FILE_SUFFIXES: list[tuple[str, Callable[[MetricContext], list]]] = [
        ("environment.csv", _load_environment),
        ("functions_summary.csv", _load_functions_summary),
        ("rank_summary.csv", _load_rank_summary),
    ]

    walk_through_data(data_dir_path, db_session, "AMDuProfMPI", FILE_SUFFIXES)
