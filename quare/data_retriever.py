from dataclasses import dataclass

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import (
    Machine,
    MetricsBase,
    MetricsDictBase,
    ProfilingSession,
    Repetition,
    TaskSizesDict,
    UseCase,
)
from .utils import InMemoryTaskSizesDict


@dataclass
class UniqueMetricKey:
    """_summary_"""

    name: str
    """member description"""
    unit: str
    """member description"""
    processing_unit: str
    """member description"""

    def __hash__(self) -> int:
        return hash(self.name + self.unit + self.processing_unit)

    def __repr__(self) -> str:
        return f"{self.name} | {self.unit} | {self.processing_unit}"


MetricsData = dict[UniqueMetricKey, list[float | int | None]]


class DataRetriever:
    """_summary_"""

    def __init__(
        self,
        db_session: Session,
        metrics_table: type[MetricsBase],
        metrics_dict_table: type[MetricsDictBase],
    ) -> None:
        """_summary_

        :param db_session: _description_
        :param metrics_table: _description_
        :param metrics_dict_table: _description_
        """
        self._db_session: Session = db_session
        self._metrics_table: type[MetricsBase] = metrics_table
        self._metrics_dict_table: type[MetricsDictBase] = metrics_dict_table

        InMemoryTaskSizesDict.initialize(db_session)

    def get_repetitions(
        self,
        session_name_contains: str,
        machine_name: str,
        use_case_name: str,
        task_size_names: list[str],
        repetition_name_contains: str,
    ) -> dict[str, list[int]]:
        """
        _summary_

        :param session_name_contains: _description_
        :param machine_name: _description_
        :param use_case_name: _description_
        :param task_size_names: _description_
        :param repetition_name_contains: _description_
        :return: _description_
        """
        result: dict[str, list[int]] = {}
        for size_name in task_size_names:
            stmt = (
                select(Repetition.id)
                .join(ProfilingSession)
                .join(Machine)
                .join(UseCase)
                .join(TaskSizesDict)
                .where(
                    ProfilingSession.name.contains(session_name_contains),
                    Machine.name == machine_name,
                    UseCase.name == use_case_name,
                    TaskSizesDict.name == size_name,
                    Repetition.name.contains(repetition_name_contains),
                )
            )

            rows = self._db_session.execute(stmt).all()
            if rows:
                ids: list[int] = [row.id for row in rows]
            else:
                ids: list[int] = []
            result[size_name] = ids
        return result

    def get_result_info(self, repetition_ids: dict[str, list[int]]) -> dict[str, str]:
        """
        _summary_

        :param repetition_ids: _description_
        :return: _description_
        """
        result_info: dict[str, str] = {}
        for size_repetition_ids in repetition_ids.values():
            for repetition_id in size_repetition_ids:
                stmt = (
                    select(
                        Repetition,
                        Machine,
                        UseCase,
                        ProfilingSession,
                    )
                    .where(Repetition.id == repetition_id)
                    .join(Machine)
                    .join(UseCase)
                    .join(ProfilingSession)
                )
                row = self._db_session.execute(stmt).first()
                if row:
                    result_info = {
                        "Session": row[3].name,
                        "Machine name": row[1].name,
                        "Use case": row[2].name,
                        "Num. of cores": row[1].num_of_cores,
                        "Num. of threads": row[1].num_of_threads,
                    }
                    return result_info
        return {}

    def get_data(
        self, repetition_ids: dict[str, list[int]], metric_names: list[str]
    ) -> MetricsData:
        """_summary_

        :param repetition_ids: _description_
        :param metric_names: _description_
        :return: _description_
        """
        metrics: MetricsData = {}

        if metric_names:
            stmt = select(
                self._metrics_dict_table.name,
                self._metrics_dict_table.unit,
                self._metrics_dict_table.processing_unit,
            ).where(self._metrics_dict_table.name.in_(metric_names))
        else:
            stmt = select(
                self._metrics_dict_table.name,
                self._metrics_dict_table.unit,
                self._metrics_dict_table.processing_unit,
            )
        metrics_data: list = list(self._db_session.execute(stmt).all())

        validated_metric_names: list[str] = [row[0] for row in metrics_data]
        metric_units: list[str] = [row[1] for row in metrics_data]
        metric_processing_units: list[str] = [row[2] for row in metrics_data]

        for metric_data in zip(
            validated_metric_names, metric_units, metric_processing_units
        ):
            metrics[UniqueMetricKey(*metric_data)] = []

        for size_repetition_ids in repetition_ids.values():
            for metric_data in zip(
                validated_metric_names, metric_units, metric_processing_units
            ):
                stmt = (
                    select(self._metrics_table)
                    .where(self._metrics_table.repetition.in_(size_repetition_ids))
                    .join(self._metrics_dict_table)
                    .where(
                        self._metrics_dict_table.name == metric_data[0],
                        self._metrics_dict_table.unit == metric_data[1],
                        self._metrics_dict_table.processing_unit == metric_data[2],
                    )
                )
                rows = self._db_session.execute(stmt).all()
                if not rows:
                    metrics[UniqueMetricKey(*metric_data)].append(None)
                else:
                    values = [row[0].value for row in rows]
                    metrics[UniqueMetricKey(*metric_data)].append(
                        float(np.mean(values))
                    )
        return metrics

    def get_machine_cores_count(self, machine_name: str) -> int | None:
        """_summary_

        :param machine_name: _description_
        :return: _description_
        """
        stmt = select(Machine.num_of_cores).where(Machine.name == machine_name)
        row = self._db_session.execute(stmt).first()
        if row:
            return row[0]
        else:
            return None

    def get_x_range_and_labels(
        self, sizes: list[str], machine_name: str
    ) -> tuple[list[float], list[str]]:
        """_summary_

        :param sizes: _description_
        :param machine_name: _description_
        :raises Exception: _description_
        :return: _description_
        """
        machine_num_of_cores = self.get_machine_cores_count(machine_name)
        if not machine_num_of_cores:
            raise Exception(f'No num_of_cores for "{machine_name}" machine')

        x_range: list[float] = []
        x_tick_labels: list[str] = []
        for task_size_name in sizes:
            x_range.append(
                InMemoryTaskSizesDict.rows[task_size_name][1] / machine_num_of_cores
            )
            x_tick_labels.append(task_size_name)
        return x_range, x_tick_labels
