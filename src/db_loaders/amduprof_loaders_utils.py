from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TypeVar

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from db_models import (
    Machine,
    MetricsBase,
    MetricsDictBase,
    ProfilingSession,
    Repetition,
    TaskSizesDict,
    UseCase,
)

from .loaders_utils import create_if_not_exists, extract_from_path, record_exists


# TODO Change InMemoryTables to context manager or to standard class
# (there won't be a need to remember to call an update method for the first time to reload)
class InMemoryTables:
    task_sizes_dict: dict[str, int] = {}
    metrics_dict: dict[str, int] = {}

    @classmethod
    def update_task_sizes_dict(cls, db_session: Session) -> None:
        task_sizes_dict_list = db_session.execute(
            select(TaskSizesDict.id, TaskSizesDict.name)
        ).all()
        cls.task_sizes_dict = {row[1]: row[0] for row in task_sizes_dict_list}

    @classmethod
    def update_metrics_dict(
        cls, db_session: Session, table: type[MetricsDictBase]
    ) -> None:
        metrics_dict_list = db_session.execute(
            select(
                table.id,
                table.name,
                table.processing_unit,
            )
        ).all()
        cls.metrics_dict = {row[1] + row[2]: row[0] for row in metrics_dict_list}


@dataclass
class MetricContext:
    path: Path
    repetition_id: int
    db_session: Session


MetricsBaseType = TypeVar("MetricsBaseType", bound=MetricsBase)


def create_metric_instance(
    context: MetricContext,
    name: str,
    value: float,
    unit_idx: int | None,
    processing_unit: str,
    metrics_table: type[MetricsBaseType],
    metrics_dict_table: type[MetricsDictBase],
) -> MetricsBaseType:
    if str(name) + processing_unit not in InMemoryTables.metrics_dict.keys():
        metric = metrics_dict_table(name=name, processing_unit=processing_unit)
        context.db_session.add(metric)
        context.db_session.commit()
        InMemoryTables.update_metrics_dict(context.db_session, metrics_dict_table)

    instance = metrics_table(
        repetition=context.repetition_id,
        unit_idx=unit_idx,
        metric=InMemoryTables.metrics_dict[str(name) + processing_unit],
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
    """_summary_

    :param context: _description_
    :param metrics_csv: _description_
    :type metrics_csv: pd.DataFrame
    :param index_trimmer: _description_
    :type index_trimmer: int
    :param processing_unit: _description_
    :type processing_unit: str
    :param metrics_table: _description_
    :type metrics_table: type[MetricsBaseType]
    :param metrics_dict_table: _description_
    :type metrics_dict_table: type[MetricsDictBase]
    :return: _description_
    :rtype: list[MetricsBaseType]
    """
    InMemoryTables.update_metrics_dict(context.db_session, metrics_dict_table)
    instances_to_add: list[MetricsBaseType] = list()
    for _, row in metrics_csv.iterrows():
        for name, value in row.items():
            instance = create_metric_instance(
                context,
                str(name),
                value,
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
    """Walks through files from input directory and adds data to a DB,
    based on provided function for directory name pattern.

    :param data_dir_path: Path to a source directory with csvized data.
    :type data_dir_path: pathlib.Path
    :param db_session: _description_
    :type db_session: Session
    :param dir_name_pattern: _description_
    :type dir_name_pattern: str
    :param file_suffixes: _description_
    :type file_suffixes: list[tuple[str, Callable[[MetricContext], list]]]
    """
    InMemoryTables.update_task_sizes_dict(db_session)

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
        machine = Machine(name=machine_name)
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
        try:
            task_size_size = int(task_size_name)
        except ValueError:
            task_size_size = None
        if task_size_name not in InMemoryTables.task_sizes_dict.keys():
            task_size = TaskSizesDict(name=task_size_name, size=task_size_size)
            db_session.add(task_size)
            db_session.commit()
            InMemoryTables.update_task_sizes_dict(db_session)

        db_session.commit()  # the commit needed to obtain the ids of the added objects

        repetition_date = repetition_name.split(".")[0]
        repetition = Repetition(
            name=repetition_name,
            profiling_session=profiling_session.id,
            machine=machine.id,
            use_case=use_case.id,
            task_size=InMemoryTables.task_sizes_dict[task_size_name],
            date=datetime.strptime(repetition_date, "%Y%m%d_%H%M%S"),
            file_dir=input_path.parent.as_posix(),
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
