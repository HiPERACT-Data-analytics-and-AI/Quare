from collections.abc import Callable
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from db_models.amduprofpcm_models import (
    AMDuProfPcm_core_metrics,
    AMDuProfPcm_further_machine_info,
    AMDuProfPcm_l3_metrics,
    AMDuProfPcm_machine_cpu_topology,
    AMDuProfPcm_machine_info,
    AMDuProfPcm_metrics_dict,
)

from .uprof_utils import MetricContext, walk_through_sessions


class InMemoryTables:
    metrics_dict: dict[str, int] = {}

    @classmethod
    def update_metrics_dict(cls, db_session: Session) -> None:
        metrics_dict_list = db_session.execute(
            select(AMDuProfPcm_metrics_dict.id, AMDuProfPcm_metrics_dict.name)
        ).all()
        cls.metrics_dict = {row[1]: row[0] for row in metrics_dict_list}


def _load_machine_info(context: MetricContext) -> list[AMDuProfPcm_machine_info]:
    try:
        machine_csv = pd.read_csv(context.path, header=None, index_col=0).T
    except FileNotFoundError:
        return []

    row = machine_csv.iloc[0]
    machine_uprof = AMDuProfPcm_machine_info(
        profiling_session=context.session_id,
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


def _load_machine_cpu_topology(
    context: MetricContext,
) -> list[AMDuProfPcm_machine_cpu_topology]:
    try:
        cpu_csv = pd.read_csv(context.path)
    except FileNotFoundError:
        return []

    instances_to_add: list[AMDuProfPcm_machine_cpu_topology] = list()
    for _, row in cpu_csv.iterrows():
        instance = AMDuProfPcm_machine_cpu_topology(
            profiling_session=context.session_id,
            socket=row.get("Socket", default=None),
            ccd=row.get(" CCD", default=None),
            ccx=row.get(" CCX", default=None),
            cores=row.get(" Core(s)", default=None),
        )
        instances_to_add.append(instance)
    return instances_to_add


def _load_further_machine_info(
    context: MetricContext,
) -> list[AMDuProfPcm_further_machine_info]:
    try:
        further_machine_csv = pd.read_csv(context.path, header=None, index_col=0).T
    except FileNotFoundError:
        return []

    row = further_machine_csv.iloc[0]
    further_machine_uprof = AMDuProfPcm_further_machine_info(
        profiling_session=context.session_id,
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


def _load_core_metrics(context: MetricContext) -> list[AMDuProfPcm_core_metrics]:
    try:
        core_metrics_csv = pd.read_csv(context.path, header=None, index_col=0).T
    except FileNotFoundError:
        return []

    instances_to_add: list[AMDuProfPcm_core_metrics] = list()
    for _, row in core_metrics_csv.iterrows():
        for name, value in row.items():
            if name == "Metric":
                continue

            if name not in InMemoryTables.metrics_dict.keys():
                metric = AMDuProfPcm_metrics_dict(name=name)
                context.db_session.add(metric)
                context.db_session.commit()
                InMemoryTables.update_metrics_dict(context.db_session)

            instance = AMDuProfPcm_core_metrics(
                profiling_session=context.session_id,
                core=int(row.get("Metric", default=-1)[5:]),
                metric=InMemoryTables.metrics_dict[str(name)],
                value=value,
            )
            instances_to_add.append(instance)
    return instances_to_add


def _load_l3_metrics(context: MetricContext) -> list[AMDuProfPcm_l3_metrics]:
    try:
        l3_metrics_csv = pd.read_csv(context.path, header=None, index_col=0).T
    except FileNotFoundError:
        return []

    instances_to_add: list[AMDuProfPcm_l3_metrics] = list()
    for _, row in l3_metrics_csv.iterrows():
        instance = AMDuProfPcm_l3_metrics(
            profiling_session=context.session_id,
            ccx_number=int(row.get("Metric", default=-1)[4:]),
            l3_access=row.get("L3 Access", default=None),
            l3_miss=row.get("L3 Miss", default=None),
            l3_miss_percent=row.get("L3 Miss %", default=None),
            ave_l3_miss_latency=row.get("Ave L3 Miss Latency", default=None),
        )
        instances_to_add.append(instance)
    return instances_to_add


def load_amduprofpcm(db_session: Session, data_dir_path: Path) -> None:
    InMemoryTables.update_metrics_dict(db_session)

    FILE_SUFFIXES: list[tuple[str, Callable[[MetricContext], list]]] = [
        ("machine_info.csv", _load_machine_info),
        ("machine_cpu_topology.csv", _load_machine_cpu_topology),
        ("further_machine_info.csv", _load_further_machine_info),
        ("core_metrics.csv", _load_core_metrics),
        ("l3_metrics.csv", _load_l3_metrics),
    ]

    walk_through_sessions(data_dir_path, db_session, FILE_SUFFIXES)
