"""
Database loader for the AMD uProf MPI profiler extension.

Reads the preprocessed CSV files produced by
:class:`~quare.extensions.AMDuProfMPI_ext.preprocessor.AMDuProfMPIPreprocessor`
and inserts them into the ORM models defined in
:mod:`quare.extensions.AMDuProfMPI_ext.models`.

The :class:`Loaders` helper class contains one static method per CSV file
type.  :class:`ExtensionDataLoaderImpl` wires them together and is the entry
point called by :func:`~quare.create_db.create_db`.
"""

from __future__ import annotations

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
    """
    Collection of static loader functions, one per preprocessed CSV file type.

    Each method accepts a :class:`~quare.data_loader.DataLoader` instance and
    a :class:`~quare.data_loader.MetricContext`, reads the CSV at
    ``context.file_path``, and returns a list of ORM instances to be added to
    the session.  Missing files are handled gracefully by returning an empty list.
    """

    @staticmethod
    def load_environment(
        data_loader: DataLoader, context: MetricContext
    ) -> list[AMDuProfMPI_environment]:
        """
        Parse the ``environment`` CSV and return an
        :class:`AMDuProfMPI_environment` row.

        The file is expected to have no header row (``header=None``) and uses
        the first column as the row index; the data is transposed so that
        field names become column names in the resulting single-row DataFrame.

        :param data_loader: The managing :class:`~quare.data_loader.DataLoader`
            (not used directly but required by the callback protocol).
        :type data_loader: quare.data_loader.DataLoader
        :param context: Bundle containing the path to the ``environment.csv``
            file and the owning repetition ID.
        :type context: quare.data_loader.MetricContext
        :returns: A list containing a single :class:`AMDuProfMPI_environment`
            ORM instance, or an empty list if the file does not exist.
        :rtype: list[AMDuProfMPI_environment]
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
        Parse the ``functions_summary`` CSV and return per-function metric rows.

        The CSV is expected to have MPI function names as the row index and
        metric names (e.g. time, call count, volume) as column headers.  Each
        (function, metric) cell produces one
        :class:`~quare.models.MetricsBase` instance with
        ``processing_unit="function"`` and ``processing_unit_idx=None``.

        :param data_loader: The :class:`~quare.data_loader.DataLoader` used to
            create metric instances via
            :meth:`~quare.data_loader.DataLoader.create_metric_instance`.
        :type data_loader: quare.data_loader.DataLoader
        :param context: Bundle containing the path to the
            ``functions_summary.csv`` file and the owning repetition ID.
        :type context: quare.data_loader.MetricContext
        :returns: A list of :class:`~quare.models.MetricsBase` ORM instances
            (one per function-metric cell), or an empty list if the file is
            absent.
        :rtype: list[quare.models.MetricsBase]
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
        Parse the ``rank_summary`` CSV and return per-rank metric rows.

        The CSV row index is a plain integer rank number (no prefix characters
        to strip), so *index_trimmer* is ``0``.

        :param data_loader: The :class:`~quare.data_loader.DataLoader` used to
            create metric instances via
            :meth:`~quare.data_loader.DataLoader.load_generic_metrics`.
        :type data_loader: quare.data_loader.DataLoader
        :param context: Bundle containing the path to the ``rank_summary.csv``
            file and the owning repetition ID.
        :type context: quare.data_loader.MetricContext
        :returns: A list of :class:`~quare.models.MetricsBase` ORM instances
            (one per rank-metric cell), or an empty list if the file is absent.
        :rtype: list[quare.models.MetricsBase]
        """
        try:
            metrics_csv = pd.read_csv(context.file_path, header=0, index_col=0)
        except FileNotFoundError:
            return []

        return data_loader.load_generic_metrics(context, metrics_csv, 0, "rank")


class ExtensionDataLoaderImpl(ExtensionDataLoader):
    """
    Concrete :class:`~quare.extension_abcs.ExtensionDataLoader` for AMD uProf MPI.

    Wires together the three CSV file types and their corresponding loader
    functions, then delegates the directory walk to
    :meth:`~quare.data_loader.DataLoader.walk_through_data`.
    """

    @staticmethod
    def load(data_dir_path: Path) -> None:
        """
        Load all AMD uProf MPI data found under *data_dir_path* into the database.

        Discovers repetitions by globbing for ``*.environment.csv`` files
        inside ``AMDuProfMPI`` subdirectories.  For each new repetition, all
        three file types are processed in order via the :class:`Loaders`
        callbacks.

        :param data_dir_path: Root of the preprocessed-data directory tree
            (value of ``preprocessed_data_directory_path`` from settings).
        :type data_dir_path: pathlib.Path
        """
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
