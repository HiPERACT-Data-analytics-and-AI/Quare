from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TypeVar

import pandas as pd
from sqlalchemy.orm import Session

from ..loader_utils import create_if_not_exists, extract_from_path, record_exists
from ..models import (
    Machine,
    MetricsBase,
    MetricsDictBase,
    ProfilingSession,
    Repetition,
    TaskSizesDict,
    UseCase,
)
from ..utils import InMemoryMetricsDict, InMemoryTaskSizesDict, load_settings


@dataclass
class MetricContext:
    """_summary_"""

    path: Path
    """member description"""
    repetition_id: int
    """member description"""
    db_session: Session
    """member description"""


MetricsBaseType = TypeVar("MetricsBaseType", bound=MetricsBase)


def create_metric_instance(
    context: MetricContext,
    name: str,
    value: float,
    unit: str,
    processing_unit_idx: int | None,
    processing_unit: str,
    metrics_table: type[MetricsBaseType],
    metrics_dict_table: type[MetricsDictBase],
) -> MetricsBaseType:
    """
    _summary_

    :param context: _description_
    :param name: _description_
    :param value: _description_
    :param unit: _description_
    :param processing_unit_idx: _description_
    :param processing_unit: _description_
    :param metrics_table: _description_
    :param metrics_dict_table: _description_
    :return: _description_
    """

    if name + str(unit) + processing_unit not in InMemoryMetricsDict.rows.keys():
        metric = metrics_dict_table(
            name=name, unit=unit, processing_unit=processing_unit
        )
        context.db_session.add(metric)
        context.db_session.commit()
        InMemoryMetricsDict.update()

    instance = metrics_table(
        repetition=context.repetition_id,
        processing_unit_idx=processing_unit_idx,
        metric=InMemoryMetricsDict.rows[str(name) + str(unit) + processing_unit],
        value=value,
    )
    return instance


def load_generic_metrics(
    context: MetricContext,
    metrics_csv: pd.DataFrame,
    index_trimmer: int,
    processing_unit: str,
    metrics_table: type[MetricsBaseType],
    metrics_dict_table: type[MetricsDictBase],
) -> list[MetricsBaseType]:
    """
    _summary_

    :param context: _description_
    :param metrics_csv: _description_
    :param index_trimmer: _description_
    :param processing_unit: _description_
    :param metrics_table: _description_
    :param metrics_dict_table: _description_
    :return: _description_
    """

    InMemoryMetricsDict.initialize(context.db_session, metrics_dict_table)
    instances_to_add: list[MetricsBaseType] = list()
    for _, row in metrics_csv.iterrows():
        for name, value in row.items():
            instance = create_metric_instance(
                context,
                str(name),
                value,
                "",
                int(str(row.name)[index_trimmer:]),
                processing_unit,
                metrics_table,
                metrics_dict_table,
            )
            instances_to_add.append(instance)
    return instances_to_add


def walk_through_data(
    data_dir_path: Path,
    db_session: Session,
    dir_name_pattern: str,
    file_suffixes: list[tuple[str, Callable[[MetricContext], list]]],
) -> None:
    """
    Walks through files from input directory and adds data to a DB,
    based on provided function for directory name pattern.

    :param data_dir_path: _description_
    :param db_session: _description_
    :param dir_name_pattern: _description_
    :param file_suffixes: _description_
    """

    InMemoryTaskSizesDict.initialize(db_session)
    settings = load_settings()

    for input_path in Path(data_dir_path).glob(
        f"**/{dir_name_pattern}/**/*.{file_suffixes[0][0]}"
    ):
        repetition_name = (
            extract_from_path("repetition_&_date", data_dir_path, input_path)
            + "."
            + extract_from_path("session", data_dir_path, input_path)
        )
        if record_exists(
            db_session=db_session,
            where_column=Repetition.name,
            equal_to=repetition_name,
        ):
            continue

        name_base: str = input_path.name[: -len(file_suffixes[0][0])]

        session_name = extract_from_path("session", data_dir_path, input_path)
        profiling_session = ProfilingSession(name=session_name)
        profiling_session = create_if_not_exists(
            db_session=db_session,
            to_create=profiling_session,
            where_column=ProfilingSession.name,
            equal_to=session_name,
        )

        machine_name = extract_from_path("machine", data_dir_path, input_path)
        try:
            num_of_cores = int(machine_name.split("_")[-1])
        except ValueError:
            num_of_cores = None
        machine = Machine(name=machine_name, num_of_cores=num_of_cores)
        machine = create_if_not_exists(
            db_session=db_session,
            to_create=machine,
            where_column=Machine.name,
            equal_to=machine_name,
        )

        use_case_name = extract_from_path("use_case", data_dir_path, input_path)
        use_case = UseCase(name=use_case_name)
        use_case = create_if_not_exists(
            db_session=db_session,
            to_create=use_case,
            where_column=UseCase.name,
            equal_to=use_case_name,
        )

        task_size_name = extract_from_path("task_size", data_dir_path, input_path)
        task_size_size = settings["task_sizes"].get(task_size_name, None)
        try:
            task_size_size = int(task_size_name)
        except ValueError:
            pass
        if task_size_name not in InMemoryTaskSizesDict.rows.keys():
            task_size = TaskSizesDict(name=task_size_name, size=task_size_size)
            db_session.add(task_size)
            db_session.commit()
            InMemoryTaskSizesDict.update()

        db_session.commit()  # the commit needed to obtain the ids of the added objects

        repetition_date = repetition_name.split(".")[0]
        repetition = Repetition(
            name=repetition_name,
            profiling_session=profiling_session.id,
            machine=machine.id,
            use_case=use_case.id,
            task_size=InMemoryTaskSizesDict.rows[task_size_name][0],
            date=datetime.strptime(repetition_date, "%Y%m%d_%H%M%S"),
            file_dir=input_path.parent.resolve().as_posix(),
        )
        repetition = create_if_not_exists(
            db_session=db_session,
            to_create=repetition,
            where_column=Repetition.name,
            equal_to=repetition_name,
        )

        db_session.commit()

        general_path: Path = input_path.parent
        for suffix, function in file_suffixes:
            path: Path = general_path / (name_base + suffix)
            db_session.add_all(
                function(
                    MetricContext(
                        path=path, repetition_id=repetition.id, db_session=db_session
                    )
                )
            )

        repetition.data_consistent = True
        db_session.commit()
