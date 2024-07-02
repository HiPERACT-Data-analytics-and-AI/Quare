from collections.abc import Callable
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from db_models.amduprofpcm_models import (
    AMDuProfPCM_further_machine_info,
    AMDuProfPCM_machine_cpu_topology,
    AMDuProfPCM_machine_info,
    AMDuProfPCM_metrics,
    AMDuProfPCM_metrics_dict,
)

from .amduprof_utils import MetricContext, load_generic_metrics, walk_through_data


def _load_machine_info(context: MetricContext) -> list[AMDuProfPCM_machine_info]:
    try:
        machine_csv = pd.read_csv(context.path, header=None, index_col=0).T
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


def _load_machine_cpu_topology(
    context: MetricContext,
) -> list[AMDuProfPCM_machine_cpu_topology]:
    try:
        cpu_csv = pd.read_csv(context.path)
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


def _load_further_machine_info(
    context: MetricContext,
) -> list[AMDuProfPCM_further_machine_info]:
    try:
        further_machine_csv = pd.read_csv(context.path, header=None, index_col=0).T
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


def _load_core_metrics(context: MetricContext) -> list[AMDuProfPCM_metrics]:
    try:
        metrics_csv = pd.read_csv(context.path, header=0, index_col=0).T
    except FileNotFoundError:
        return []

    name: str = "core"
    return load_generic_metrics(
        context, metrics_csv, 5, name, AMDuProfPCM_metrics, AMDuProfPCM_metrics_dict
    )


def _load_l3_metrics(context: MetricContext) -> list[AMDuProfPCM_metrics]:
    try:
        metrics_csv = pd.read_csv(context.path, header=0, index_col=0).T
    except FileNotFoundError:
        return []

    name: str = "ccx"
    return load_generic_metrics(
        context, metrics_csv, 4, name, AMDuProfPCM_metrics, AMDuProfPCM_metrics_dict
    )


def load_amduprofpcm(db_session: Session, data_dir_path: Path) -> None:
    FILE_SUFFIXES: list[tuple[str, Callable[[MetricContext], list]]] = [
        ("machine_info.csv", _load_machine_info),
        ("machine_cpu_topology.csv", _load_machine_cpu_topology),
        ("further_machine_info.csv", _load_further_machine_info),
        ("core_metrics.csv", _load_core_metrics),
        ("l3_metrics.csv", _load_l3_metrics),
    ]

    walk_through_data(data_dir_path, db_session, "AMDuProfPCM", FILE_SUFFIXES)
