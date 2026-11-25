"""
Loader for the LIKWID extension.

Reads ``run.stat.csv`` (see :mod:`.preprocessor`) and stores, for every row,
four metrics named ``<group> <metric>`` with the processing unit ``sum``,
``min``, ``max`` and ``avg`` (the statistic over the hardware threads).  The
unit is the bracketed text of the metric name (``MHz``, ``GBytes``, ...).

Authors: Marcin Lawenda, Łukasz Szustak
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

import pandas as pd

from ...data_loader import DataLoader, MetricContext
from ...extension_abcs import ExtensionDataLoader
from ...models import MetricsBase
from ...utils import get_db_session
from .models import LIKWID_metrics, LIKWID_metrics_dict

STATISTICS = ("sum", "min", "max", "avg")
_UNIT = re.compile(r"\[([^\]]*)\]")


class Loaders:
    """Loader functions for the files of this extension."""

    @staticmethod
    def load_stat(data_loader: DataLoader, context: MetricContext) -> list[MetricsBase]:
        """Return the statistics of every metric row of ``stat.csv``."""
        try:
            table = pd.read_csv(context.file_path)
        except FileNotFoundError:
            return []
        instances: list[MetricsBase] = []
        for row in table.itertuples(index=False):
            unit = _UNIT.search(str(row.metric))
            for statistic in STATISTICS:
                instances.append(
                    data_loader.create_metric_instance(
                        context,
                        f"{row.group} {row.metric}",
                        float(getattr(row, statistic)),
                        unit.group(1) if unit else "",
                        None,
                        statistic,
                    )
                )
        return instances


class ExtensionDataLoaderImpl(ExtensionDataLoader):
    """Loads the LIKWID statistics of all preprocessed repetitions."""

    @staticmethod
    def load(data_dir_path: Path) -> None:
        """Load all ``LIKWID`` directories below *data_dir_path*."""
        file_suffixes: list[tuple[str, Callable[[DataLoader, MetricContext], list]]] = [
            ("stat.csv", Loaders.load_stat)
        ]
        data_loader = DataLoader(
            get_db_session(), data_dir_path, LIKWID_metrics, LIKWID_metrics_dict
        )
        data_loader.walk_through_data("LIKWID", file_suffixes)
