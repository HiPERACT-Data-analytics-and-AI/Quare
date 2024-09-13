from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TypeVar

import pandas as pd
from sqlalchemy import exists, select
from sqlalchemy.orm import InstrumentedAttribute, Session

from .models import (
    DBBase,
    Machine,
    MetricsBase,
    MetricsDictBase,
    ProfilingSession,
    Repetition,
    TaskSizesDict,
    UseCase,
)
from .utils import InMemoryMetricsDict, InMemoryTaskSizesDict, load_settings


@dataclass
class MetricContext:
    """_summary_"""

    file_path: Path
    """member description"""
    repetition_id: int
    """member description"""


DBBaseGeneric = TypeVar("DBBaseGeneric", bound=DBBase)
# MetricsBaseGeneric = TypeVar("MetricsBaseGeneric", bound=MetricsBase)


# TODO Make an ABC from the class below - load method must be implemented.
# Then another ABC won' be needed.
class DataLoader:
    """_summary_"""

    T = TypeVar("T")

    def __init__(
        self,
        db_session: Session,
        data_dir_path: Path,
        metrics_table: type[MetricsBase],
        metrics_dict_table: type[MetricsDictBase],
    ) -> None:
        """_summary_

        :param db_session: _description_
        :param data_dir_path: _description_
        """
        self._db_session: Session = db_session
        self._data_dir_path: Path = data_dir_path
        self._metrics_table: type[MetricsBase] = metrics_table
        self._metrics_dict_table: type[MetricsDictBase] = metrics_dict_table

        self.in_memory_metrics = InMemoryMetricsDict(db_session, metrics_dict_table)

    def extract_from_path(self, key: str, file_path: Path) -> str:
        """_summary_

        :param key: _description_
        :param file_path: _description_
        :return: _description_
        """
        path_struct: dict[str, tuple[int, ...]] = {
            "session": (0,),
            "machine": (1,),
            "use_case": (2,),
            "task_size": (3,),
            "repetition_&_date": (4,),
        }
        file_path = file_path.relative_to(self._data_dir_path)
        return ".".join(file_path.parts[i] for i in path_struct[key])

    def create_if_not_exists(
        self,
        to_create: DBBaseGeneric,
        where_column: InstrumentedAttribute[T],
        equal_to: T,
    ) -> DBBaseGeneric:
        """_summary_

        :param to_create: _description_
        :param where_column: _description_
        :param equal_to: _description_
        :return: _description_
        """
        selected_row = self._db_session.execute(
            select(where_column.parent).where(where_column == equal_to)
        ).first()

        if not selected_row:
            # TODO It needs a commit after returning <- add to docs
            # (or change the function to context manager)
            self._db_session.add(to_create)
            return to_create
        return selected_row[0]

    def record_exists(
        self,
        where_column: InstrumentedAttribute[T],
        is_equal_to: T,
    ) -> bool:
        """_summary_

        :param where_column: _description_
        :param equal_to: _description_
        :return: _description_
        """
        return bool(
            self._db_session.query(exists().where(where_column == is_equal_to)).scalar()
        )

    def create_metric_instance(
        self,
        context: MetricContext,
        name: str,
        value: float,
        unit: str,
        processing_unit_idx: int | None,
        processing_unit: str,
    ) -> MetricsBase:
        """_summary_

        :param context: _description_
        :param name: _description_
        :param value: _description_
        :param unit: _description_
        :param processing_unit_idx: _description_
        :param processing_unit: _description_
        :param in_memory_metrics: _description_
        :param metrics_table: _description_
        :param metrics_dict_table: _description_
        :return: _description_
        """

        if name + str(unit) + processing_unit not in self.in_memory_metrics.rows.keys():
            metric = self._metrics_dict_table(
                name=name, unit=unit, processing_unit=processing_unit
            )
            self._db_session.add(metric)
            self._db_session.commit()
            self.in_memory_metrics.update()

        instance = self._metrics_table(
            repetition=context.repetition_id,
            processing_unit_idx=processing_unit_idx,
            metric=self.in_memory_metrics.rows[str(name) + str(unit) + processing_unit],
            value=value,
        )
        return instance

    def load_generic_metrics(
        self,
        context: MetricContext,
        metrics_csv: pd.DataFrame,
        index_trimmer: int,
        processing_unit: str,
    ) -> list[MetricsBase]:
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
        instances_to_add: list[MetricsBase] = list()
        for _, row in metrics_csv.iterrows():
            for name, value in row.items():
                instance = self.create_metric_instance(
                    context,
                    str(name),
                    value,
                    "",
                    int(str(row.name)[index_trimmer:]),
                    processing_unit,
                )
                instances_to_add.append(instance)
        return instances_to_add

    def walk_through_data(
        self,
        dir_name_pattern: str,
        file_suffixes: list[tuple[str, Callable[["DataLoader", MetricContext], list]]],
    ) -> None:
        """
        Walks through files from input directory and adds data to a DB,
        based on provided function for directory name pattern.

        :param dir_name_pattern: _description_
        :param file_suffixes: _description_
        """

        in_memory_task_sizes = InMemoryTaskSizesDict(self._db_session)
        settings = load_settings()

        for input_path in Path(self._data_dir_path).glob(
            f"**/{dir_name_pattern}/**/*.{file_suffixes[0][0]}"
        ):
            repetition_name = (
                self.extract_from_path("repetition_&_date", input_path)
                + "."
                + self.extract_from_path("session", input_path)
            )
            if self.record_exists(
                where_column=Repetition.name,
                is_equal_to=repetition_name,
            ):
                continue

            name_base: str = input_path.name[: -len(file_suffixes[0][0])]

            session_name = self.extract_from_path("session", input_path)
            profiling_session = ProfilingSession(name=session_name)
            profiling_session = self.create_if_not_exists(
                to_create=profiling_session,
                where_column=ProfilingSession.name,
                equal_to=session_name,
            )

            machine_name = self.extract_from_path("machine", input_path)
            try:
                num_of_cores = int(machine_name.split("_")[-1])
            except ValueError:
                num_of_cores = None
            machine = Machine(name=machine_name, num_of_cores=num_of_cores)
            machine = self.create_if_not_exists(
                to_create=machine,
                where_column=Machine.name,
                equal_to=machine_name,
            )

            use_case_name = self.extract_from_path("use_case", input_path)
            use_case = UseCase(name=use_case_name)
            use_case = self.create_if_not_exists(
                to_create=use_case,
                where_column=UseCase.name,
                equal_to=use_case_name,
            )

            task_size_name = self.extract_from_path("task_size", input_path)
            task_size_size = settings["task_sizes"].get(task_size_name, None)
            try:
                task_size_size = int(task_size_name)
            except ValueError:
                pass
            if task_size_name not in in_memory_task_sizes.rows.keys():
                task_size = TaskSizesDict(name=task_size_name, size=task_size_size)
                self._db_session.add(task_size)
                self._db_session.commit()
                in_memory_task_sizes.update()

            self._db_session.commit()  # a commit to a DB needed
            # to obtain the ids of the added objects

            repetition_date = repetition_name.split(".")[0]
            repetition = Repetition(
                name=repetition_name,
                profiling_session=profiling_session.id,
                machine=machine.id,
                use_case=use_case.id,
                task_size=in_memory_task_sizes.rows[task_size_name][0],
                date=datetime.strptime(repetition_date, "%Y%m%d_%H%M%S"),
                file_dir=input_path.parent.resolve().as_posix(),
            )
            repetition = self.create_if_not_exists(
                to_create=repetition,
                where_column=Repetition.name,
                equal_to=repetition_name,
            )

            self._db_session.commit()

            general_path: Path = input_path.parent
            for suffix, function in file_suffixes:
                path: Path = general_path / (name_base + suffix)
                self._db_session.add_all(
                    function(self, MetricContext(path, repetition.id))
                )

            repetition.data_consistent = True
            self._db_session.commit()
