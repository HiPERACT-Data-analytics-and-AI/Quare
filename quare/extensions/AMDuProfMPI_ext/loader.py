from collections.abc import Callable
from pathlib import Path

import pandas as pd

from ...data_loader import DataLoader, MetricContext
from ...extension_abcs import ExtensionDataLoader
from ...models import MetricsBase
from ...utils import get_db_session
from .models import (
    AMDuProfMPI_environment,
    AMDuProfMPI_metrics,
    AMDuProfMPI_metrics_dict,
)


class Loaders:
    @staticmethod
    def load_environment(
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

    @staticmethod
    def load_functions_summary(
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

    @staticmethod
    def load_rank_summary(
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


class ExtensionDataLoaderImpl(ExtensionDataLoader):
    @staticmethod
    def load(data_dir_path: Path) -> None:
        FILE_SUFFIXES: list[tuple[str, Callable[[DataLoader, MetricContext], list]]] = [
            ("environment.csv", Loaders.load_environment),
            ("functions_summary.csv", Loaders.load_functions_summary),
            ("rank_summary.csv", Loaders.load_rank_summary),
        ]

        data_loader = DataLoader(
            get_db_session(),
            data_dir_path,
            AMDuProfMPI_metrics,
            AMDuProfMPI_metrics_dict,
        )
        data_loader.walk_through_data("AMDuProfMPI", FILE_SUFFIXES)
