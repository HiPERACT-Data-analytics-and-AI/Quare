"""
Database loader for the AMD uProf Performance Counter Monitor (PCM) extension.

Reads the preprocessed CSV files produced by
:class:`~quare.extensions.AMDuProfPCM_ext.preprocessor.AMDuProfPCMPreprocessor`
and inserts the data into the ORM models defined in
:mod:`quare.extensions.AMDuProfPCM_ext.models`.

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
    AMDuProfPCM_further_machine_info,
    AMDuProfPCM_machine_cpu_topology,
    AMDuProfPCM_machine_info,
    AMDuProfPCM_metrics,
    AMDuProfPCM_metrics_dict,
)


class Loaders:
    """
    Collection of static loader functions, one per preprocessed CSV file type.

    Each method accepts a :class:`~quare.data_loader.DataLoader` instance and
    a :class:`~quare.data_loader.MetricContext`, reads the CSV at
    ``context.file_path``, and returns a list of ORM instances to be added to
    the session.  Missing files are handled gracefully by returning an empty
    list.
    """

    @staticmethod
    def load_machine_info(
        data_loader: DataLoader, context: MetricContext
    ) -> list[AMDuProfPCM_machine_info]:
        """
        Parse the ``machine_info`` CSV and return an :class:`AMDuProfPCM_machine_info` row.

        The file is expected to have no header row (``header=None``) and the
        first column acts as the row index; the data is transposed so that
        column names become the index of the resulting single-row DataFrame.

        :param data_loader: The :class:`~quare.data_loader.DataLoader` managing
            the current import session (not used directly here but required by
            the loader callback protocol).
        :type data_loader: quare.data_loader.DataLoader
        :param context: Bundle containing the path to the ``machine_info.csv``
            file and the owning repetition ID.
        :type context: quare.data_loader.MetricContext
        :returns: A list containing a single :class:`AMDuProfPCM_machine_info`
            ORM instance, or an empty list if the file does not exist.
        :rtype: list[AMDuProfPCM_machine_info]
        """
        try:
            machine_csv = pd.read_csv(context.file_path, header=None, index_col=0).T
        except FileNotFoundError:
            return []

        row = machine_csv.iloc[0]
        machine_uprof = AMDuProfPCM_machine_info(
            repetition=context.repetition_id,
            system=row.get("System:", default=None),
            num_of_sockets=row.get("Number of Sockets :", default=None),
            num_of_ccds=row.get("Number of CCDs :", default=None),
            num_of_ccxs=row.get("Number of Core Complexes(CCX) :", default=None),
            num_of_cores=row.get("Number of Cores :", default=None),
            num_of_threads=row.get("Number of Threads :", default=None),
            smt_enabled_in_hw=bool(row.get("SMT Enabled in HW:")),
            smt_enabled_in_os=bool(row.get("SMT Enabled by OS :")),
            num_of_threads_sharing_l3=row.get(
                "Number of Threads sharing L3:", default=None
            ),
        )
        return [machine_uprof]

    @staticmethod
    def load_machine_cpu_topology(
        data_loader: DataLoader,
        context: MetricContext,
    ) -> list[AMDuProfPCM_machine_cpu_topology]:
        """
        Parse the ``machine_cpu_topology`` CSV and return topology rows.

        One :class:`AMDuProfPCM_machine_cpu_topology` instance is created per
        line (socket/CCD/CCX entry) in the CSV.

        :param data_loader: The managing :class:`~quare.data_loader.DataLoader`
            (not used directly but required by the callback protocol).
        :type data_loader: quare.data_loader.DataLoader
        :param context: Bundle containing the path to the
            ``machine_cpu_topology.csv`` file and the owning repetition ID.
        :type context: quare.data_loader.MetricContext
        :returns: A list of :class:`AMDuProfPCM_machine_cpu_topology` ORM
            instances, or an empty list if the file does not exist.
        :rtype: list[AMDuProfPCM_machine_cpu_topology]
        """
        try:
            cpu_csv = pd.read_csv(context.file_path)
        except FileNotFoundError:
            return []

        instances_to_add: list[AMDuProfPCM_machine_cpu_topology] = list()
        for _, row in cpu_csv.iterrows():
            instance = AMDuProfPCM_machine_cpu_topology(
                repetition=context.repetition_id,
                socket=row.get("Socket", default=None),
                ccd=row.get(" CCD", default=None),
                ccx=row.get(" CCX", default=None),
                cores=row.get(" Core(s)", default=None),
            )
            instances_to_add.append(instance)
        return instances_to_add

    @staticmethod
    def load_further_machine_info(
        data_loader: DataLoader,
        context: MetricContext,
    ) -> list[AMDuProfPCM_further_machine_info]:
        """
        Parse the ``further_machine_info`` CSV and return a configuration row.

        The file layout is identical to ``machine_info.csv`` (transposed
        key-value format).

        :param data_loader: The managing :class:`~quare.data_loader.DataLoader`
            (not used directly but required by the callback protocol).
        :type data_loader: quare.data_loader.DataLoader
        :param context: Bundle containing the path to the
            ``further_machine_info.csv`` file and the owning repetition ID.
        :type context: quare.data_loader.MetricContext
        :returns: A list containing a single
            :class:`AMDuProfPCM_further_machine_info` ORM instance, or an
            empty list if the file does not exist.
        :rtype: list[AMDuProfPCM_further_machine_info]
        """
        try:
            further_machine_csv = pd.read_csv(
                context.file_path, header=None, index_col=0
            ).T
        except FileNotFoundError:
            return []

        row = further_machine_csv.iloc[0]
        further_machine_uprof = AMDuProfPCM_further_machine_info(
            repetition=context.repetition_id,
            core_p0_state_freq=row.get("Core P0 state frequency (MHz):", default=None),
            multiplex_interval_for_core=row.get(
                "Multiplex interval for core (ms):", default=None
            ),
            multiplex_interval_for_l3=row.get(
                "Multiplex interval for l3 (ms):", default=None
            ),
            multiplex_interval_for_df=row.get(
                "Multiplex interval for df (ms):", default=None
            ),
            measured_df_frequency=row.get("Measured DF Frequency (MHz):", default=None),
            multiplex_interval=row.get("Multiplex interval (ms):", default=None),
            version=row.get("Version:", default=None),
        )
        return [further_machine_uprof]

    @staticmethod
    def load_core_metrics(
        data_loader: DataLoader, context: MetricContext
    ) -> list[MetricsBase]:
        """
        Parse the ``core_metrics`` CSV and return per-core metric rows.

        The CSV is expected to have performance-counter values organised with
        one row per core (row index ``"Core <N>"``) and one column per metric.
        The row index is trimmed by 5 characters (``len("Core ")``)) to extract
        the integer core index.

        :param data_loader: The :class:`~quare.data_loader.DataLoader` used to
            create metric instances via
            :meth:`~quare.data_loader.DataLoader.load_generic_metrics`.
        :type data_loader: quare.data_loader.DataLoader
        :param context: Bundle containing the path to the ``core_metrics.csv``
            file and the owning repetition ID.
        :type context: quare.data_loader.MetricContext
        :returns: A list of :class:`~quare.models.MetricsBase` ORM instances
            (one per core-metric cell), or an empty list if the file is absent.
        :rtype: list[quare.models.MetricsBase]
        """
        try:
            metrics_csv = pd.read_csv(context.file_path, header=0, index_col=0).T
        except FileNotFoundError:
            return []

        return data_loader.load_generic_metrics(context, metrics_csv, 5, "core")

    @staticmethod
    def load_l3_metrics(
        data_loader: DataLoader, context: MetricContext
    ) -> list[MetricsBase]:
        """
        Parse the ``l3_metrics`` CSV and return per-CCX L3 metric rows.

        The CSV row index is of the form ``"CCX<N>"``; the first 3 characters
        (``len("CCX")``) are trimmed to extract the integer CCX index.

        :param data_loader: The :class:`~quare.data_loader.DataLoader` used to
            create metric instances.
        :type data_loader: quare.data_loader.DataLoader
        :param context: Bundle containing the path to the ``l3_metrics.csv``
            file and the owning repetition ID.
        :type context: quare.data_loader.MetricContext
        :returns: A list of :class:`~quare.models.MetricsBase` ORM instances
            (one per CCX-metric cell), or an empty list if the file is absent.
        :rtype: list[quare.models.MetricsBase]
        """
        try:
            metrics_csv = pd.read_csv(context.file_path, header=0, index_col=0).T
        except FileNotFoundError:
            return []

        return data_loader.load_generic_metrics(context, metrics_csv, 4, "ccx")


class ExtensionDataLoaderImpl(ExtensionDataLoader):
    """
    Concrete :class:`~quare.extension_abcs.ExtensionDataLoader` for AMD uProf PCM.

    Wires together the five CSV file types and their corresponding loader
    functions, then delegates the directory walk to
    :meth:`~quare.data_loader.DataLoader.walk_through_data`.
    """

    @staticmethod
    def load(data_dir_path: Path) -> None:
        """
        Load all AMD uProf PCM data found under *data_dir_path* into the database.

        Discovers repetitions by globbing for ``*.machine_info.csv`` files
        inside ``AMDuProfPCM`` subdirectories.  For each new repetition, all
        five file types are processed in order via the :class:`Loaders`
        callbacks.

        :param data_dir_path: Root of the preprocessed-data directory tree
            (value of ``preprocessed_data_directory_path`` from settings).
        :type data_dir_path: pathlib.Path
        """
        FILE_SUFFIXES: list[tuple[str, Callable[[DataLoader, MetricContext], list]]] = [
            ("machine_info.csv", Loaders.load_machine_info),
            ("machine_cpu_topology.csv", Loaders.load_machine_cpu_topology),
            ("further_machine_info.csv", Loaders.load_further_machine_info),
            ("core_metrics.csv", Loaders.load_core_metrics),
            ("l3_metrics.csv", Loaders.load_l3_metrics),
        ]

        data_loader = DataLoader(
            get_db_session(),
            data_dir_path,
            AMDuProfPCM_metrics,
            AMDuProfPCM_metrics_dict,
        )
        data_loader.walk_through_data("AMDuProfPCM", FILE_SUFFIXES)
