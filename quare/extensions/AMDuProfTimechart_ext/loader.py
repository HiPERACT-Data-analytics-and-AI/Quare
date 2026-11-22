"""
Loader for the AMD uProf Timechart (power) extension.

Reads ``run.power.csv`` (see :mod:`.preprocessor`) and stores every sample as a
metric ``Node <n> power`` (unit ``W``, processing unit ``sample``, index =
sample number).  Empty cells (a node trace shorter than the longest one) are
skipped.

Authors: Marcin Lawenda, Łukasz Szustak
"""

from __future__ import annotations

import math
from collections.abc import Callable
from pathlib import Path

import pandas as pd

from ...data_loader import DataLoader, MetricContext
from ...extension_abcs import ExtensionDataLoader
from ...models import MetricsBase
from ...utils import get_db_session
from .models import AMDuProfTimechart_metrics, AMDuProfTimechart_metrics_dict


class Loaders:
    """Loader functions for the files of this extension."""

    @staticmethod
    def load_power(data_loader: DataLoader, context: MetricContext) -> list[MetricsBase]:
        """Return one metric row per power sample of ``power.csv``."""
        try:
            table = pd.read_csv(context.file_path, index_col=0)
        except FileNotFoundError:
            return []
        instances: list[MetricsBase] = []
        for sample, row in table.iterrows():
            for name, value in row.items():
                if value is None or (isinstance(value, float) and math.isnan(value)):
                    continue
                instances.append(
                    data_loader.create_metric_instance(
                        context, str(name), float(value), "W", int(str(sample)), "sample"
                    )
                )
        return instances


class ExtensionDataLoaderImpl(ExtensionDataLoader):
    """Loads the power traces of all preprocessed repetitions."""

    @staticmethod
    def load(data_dir_path: Path) -> None:
        """Load all ``AMDuProfTimechart`` directories below *data_dir_path*."""
        file_suffixes: list[tuple[str, Callable[[DataLoader, MetricContext], list]]] = [
            ("power.csv", Loaders.load_power)
        ]
        data_loader = DataLoader(
            get_db_session(),
            data_dir_path,
            AMDuProfTimechart_metrics,
            AMDuProfTimechart_metrics_dict,
        )
        data_loader.walk_through_data("AMDuProfTimechart", file_suffixes)
