from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

import pandas as pd
from sqlalchemy import Engine, create_engine, select
from sqlalchemy.orm import InstrumentedAttribute, Session

from db_models import DBBase, Machine, ProfilingSession, UseCase
from db_models.amduprofpcm_models import (
    AMDuProfPcm_core_metrics,
    AMDuProfPcm_further_machine_info,
    AMDuProfPcm_l3_metrics,
    AMDuProfPcm_machine_cpu_topology,
    AMDuProfPcm_machine_info,
    AMDuProfPcm_metrics_dict,
)


@dataclass
class MetricContext:
    path: Path
    session_id: int
    db_session: Session


def extract_from_path(key: str, path: Path) -> str:
    path_struct: dict[str, tuple[int, ...]] = {
        "use_case": (2,),
        "machine": (3,),
        "task_size": (5,),
        "session": (4, 5, 6),
    }
    return ".".join(path.parts[i] for i in path_struct[key])


DBBaseModel = TypeVar("DBBaseModel", bound=DBBase)
T = TypeVar("T")


def create_if_not_exists(
    db_session: Session,
    to_create: DBBaseModel,
    where_column: InstrumentedAttribute[T],
    equal_to: T,
) -> DBBaseModel:
    selected_row = db_session.execute(
        select(where_column.parent).where(where_column == equal_to)
    ).first()

    if not selected_row:
        db_session.add(to_create)  # needs a commit after returning <- add to docs
        return to_create
    return selected_row[0]


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

            metric = AMDuProfPcm_metrics_dict(name=name)
            metric = create_if_not_exists(
                db_session=context.db_session,
                to_create=metric,
                where_column=AMDuProfPcm_metrics_dict.name,
                equal_to=str(name),
            )
            context.db_session.commit()

            instance = AMDuProfPcm_core_metrics(
                profiling_session=context.session_id,
                core=int(row.get("Metric", default=-1)[5:]),
                metric=metric.id,
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


def load_uprof_pcm(db_session: Session) -> None:
    FILE_SUFFIXES: list[tuple[str, Callable[[MetricContext], list]]] = [
        ("machine_info.csv", _load_machine_info),
        ("machine_cpu_topology.csv", _load_machine_cpu_topology),
        ("further_machine_info.csv", _load_further_machine_info),
        ("core_metrics.csv", _load_core_metrics),
        ("l3_metrics.csv", _load_l3_metrics),
    ]

    for input_path in Path("csvized_data").glob(f"**/*.{FILE_SUFFIXES[0][0]}"):
        general_path: Path = input_path.parent
        name_base: str = input_path.name[: -len(FILE_SUFFIXES[0][0])]

        machine_name = extract_from_path("machine", input_path)
        machine = Machine(name=machine_name)
        machine = create_if_not_exists(
            db_session=db_session,
            to_create=machine,
            where_column=Machine.name,
            equal_to=machine_name,
        )

        use_case_name = extract_from_path("use_case", input_path)
        use_case = UseCase(name=use_case_name)
        use_case = create_if_not_exists(
            db_session=db_session,
            to_create=use_case,
            where_column=UseCase.name,
            equal_to=use_case_name,
        )

        db_session.commit()  # commit needed to obtain the ids of the added objects

        session_name = extract_from_path("session", input_path)
        session = ProfilingSession(
            name=session_name,
            use_case=use_case.id,
            task_size=extract_from_path("task_size", input_path),
            machine=machine.id,
        )
        session = create_if_not_exists(
            db_session=db_session,
            to_create=session,
            where_column=ProfilingSession.name,
            equal_to=session_name,
        )

        db_session.commit()

        for suffix, function in FILE_SUFFIXES:
            path: Path = general_path / (name_base + suffix)
            db_session.add_all(
                function(
                    MetricContext(
                        path=path, session_id=session.id, db_session=db_session
                    )
                )
            )


def main():
    db_engine: Engine = create_engine("sqlite:///quare.sqlite3", echo=False)
    DBBase.metadata.create_all(db_engine)

    with Session(db_engine) as db_session:
        load_uprof_pcm(db_session)
        db_session.commit()


if __name__ == "__main__":
    main()
