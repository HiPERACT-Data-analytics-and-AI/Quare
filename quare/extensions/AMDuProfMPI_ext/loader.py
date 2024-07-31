from collections.abc import Callable
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from ...data_loader import DataLoader, MetricContext
from ...models import MetricsBase
from .models import (
    AMDuProfMPI_environment,
    AMDuProfMPI_metrics,
    AMDuProfMPI_metrics_dict,
)


def _load_environment(
    data_loader: DataLoader, context: MetricContext
) -> list[AMDuProfMPI_environment]:
    """
    _summary_

    :param context: _description_
    :return: _description_
    """
    try:
        environment_csv = pd.read_csv(context.file_path, header=None, index_col=0).T
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
    data_loader: DataLoader,
    context: MetricContext,
) -> list[MetricsBase]:
    """
    _summary_

    :param context: _description_
    :return: _description_
    """
    try:
        metrics_csv = pd.read_csv(context.file_path, header=0, index_col=0)
    except FileNotFoundError:
        return []

    instances_to_add: list[MetricsBase] = list()
    for _, row in metrics_csv.iterrows():
        for name, value in row.items():
            instance = data_loader.create_metric_instance(
                context,
                str(row.name),
                value,
                str(name),
                None,
                "function",
            )
            instances_to_add.append(instance)
    return instances_to_add


def _load_rank_summary(
    data_loader: DataLoader, context: MetricContext
) -> list[MetricsBase]:
    """
    _summary_

    :param context: _description_
    :return: _description_
    """
    try:
        metrics_csv = pd.read_csv(context.file_path, header=0, index_col=0)
    except FileNotFoundError:
        return []

    return data_loader.load_generic_metrics(context, metrics_csv, 0, "rank")


def load(db_session: Session, data_dir_path: Path) -> None:
    """
    _summary_

    :param db_session: _description_
    :param data_dir_path: _description_
    """
    FILE_SUFFIXES: list[tuple[str, Callable[[DataLoader, MetricContext], list]]] = [
        ("environment.csv", _load_environment),
        ("functions_summary.csv", _load_functions_summary),
        ("rank_summary.csv", _load_rank_summary),
    ]

    data_loader = DataLoader(
        db_session, data_dir_path, AMDuProfMPI_metrics, AMDuProfMPI_metrics_dict
    )
    data_loader.walk_through_data("AMDuProfMPI", FILE_SUFFIXES)
