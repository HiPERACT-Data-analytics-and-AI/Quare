from collections.abc import Callable
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from ...data_loader import DataLoader, MetricContext
from ...extensions_abcs import ExtensionDataLoader
from ...models import MetricsBase
from .models import (
    AMDuProfPCM_further_machine_info,
    AMDuProfPCM_machine_cpu_topology,
    AMDuProfPCM_machine_info,
    AMDuProfPCM_metrics,
    AMDuProfPCM_metrics_dict,
)


class Loaders:
    @staticmethod
    def load_machine_info(
        data_loader: DataLoader, context: MetricContext
    ) -> list[AMDuProfPCM_machine_info]:
        """
        _summary_

        :param context: _description_
        :return: _description_
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
        _summary_

        :param context: _description_
        :return: _description_
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
        _summary_

        :param context: _description_
        :return: _description_
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
        _summary_

        :param context: _description_
        :return: _description_
        """
        try:
            metrics_csv = pd.read_csv(context.file_path, header=0, index_col=0).T
        except FileNotFoundError:
            return []

        name: str = "core"
        return data_loader.load_generic_metrics(context, metrics_csv, 5, name)

    @staticmethod
    def load_l3_metrics(
        data_loader: DataLoader, context: MetricContext
    ) -> list[MetricsBase]:
        """
        _summary_

        :param context: _description_
        :return: _description_
        """
        try:
            metrics_csv = pd.read_csv(context.file_path, header=0, index_col=0).T
        except FileNotFoundError:
            return []

        name: str = "ccx"
        return data_loader.load_generic_metrics(context, metrics_csv, 4, name)


class ExtensionDataLoaderImpl(ExtensionDataLoader):
    @staticmethod
    def load(db_session: Session, data_dir_path: Path) -> None:
        """
        _summary_

        :param db_session: _description_
        :param data_dir_path: _description_
        """

        FILE_SUFFIXES: list[tuple[str, Callable[[DataLoader, MetricContext], list]]] = [
            ("machine_info.csv", Loaders.load_machine_info),
            ("machine_cpu_topology.csv", Loaders.load_machine_cpu_topology),
            ("further_machine_info.csv", Loaders.load_further_machine_info),
            ("core_metrics.csv", Loaders.load_core_metrics),
            ("l3_metrics.csv", Loaders.load_l3_metrics),
        ]

        data_loader = DataLoader(
            db_session, data_dir_path, AMDuProfPCM_metrics, AMDuProfPCM_metrics_dict
        )
        data_loader.walk_through_data("AMDuProfPCM", FILE_SUFFIXES)
