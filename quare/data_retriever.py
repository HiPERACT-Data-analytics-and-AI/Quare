from collections.abc import Callable
from dataclasses import dataclass
from importlib import util
from itertools import chain

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
from .utils import InMemoryTaskSizesDict, get_db_session, get_extension_path


# TODO: Make it possible to keep individual values,
# not only aggregated ones in the UniqueMetricKey objects.
# Maybe repetition IDs should be also kept but not necessarily cached and hashed?
# Hashing way can be settable by a flag
# (but remember to make all hashed attributes immutable)
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


MetricValue = float | int | None
""""""

# TODO: Maybe convert MetricsData type to a class?

MetricsData = dict[UniqueMetricKey, list[MetricValue]]
"""
A key unambiguously points a particular metric. A single value in that dictionary
is a list of task-size-wise aggregated (averaged) metrics.

:alias of: dict[UniqueMetricKey, list[MetricValue]]
"""

RepetitionIDs = dict[str, list[int]]
"""
Type alias for pointing specific repetitions (task-size-wise).
A key is a name of the task size. A value is a list of Repetition IDs
belonging to that task size.

:alias of: dict[str, list[int]]
"""


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

        self.in_memory_task_sizes = InMemoryTaskSizesDict(db_session)
        self.AVAILABLE_ANALYTICS: dict[
            UniqueMetricKey, Callable[[RepetitionIDs], list[MetricValue]]
        ] = {}
        self._cache: dict[UniqueMetricKey, dict[tuple[int, ...], list[MetricValue]]] = (
            {}
        )

    def get_repetitions(
        self,
        session_name_contains: str,
        machine_name: str,
        use_case_name: str,
        task_size_names: list[str],
        repetition_name_contains: str,
    ) -> RepetitionIDs:
        """
        _summary_

        :param session_name_contains: _description_
        :param machine_name: _description_
        :param use_case_name: _description_
        :param task_size_names: _description_
        :param repetition_name_contains: _description_
        :return: _description_
        """
        result: RepetitionIDs = {}
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

    def get_result_info(self, repetition_ids: RepetitionIDs) -> dict[str, str]:
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

    def discover_metric_keys(self, metric_names: list[str]) -> list[UniqueMetricKey]:
        """
        _summary_

        :param metric_names: _description_
        :return: A list of the keys corresponding to existing metrics.
                 The length of the returned list can be different than the length
                 of the source list, as the metrics can be not found or multiple metrics
                 can be found for a particular name.
        """
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

        metric_keys: list[UniqueMetricKey] = []
        for metric_data in zip(
            validated_metric_names, metric_units, metric_processing_units
        ):
            metric_keys.append(UniqueMetricKey(*metric_data))
        return metric_keys

    def add_data_to_cache(
        self, data: MetricsData, repetition_ids: RepetitionIDs
    ) -> None:
        flattened_repetition_ids: tuple[int, ...] = tuple(
            chain(*repetition_ids.values())
        )
        for key, val in data.items():
            data_result_slot = self._cache.get(key, None)
            if not data_result_slot:
                self._cache[key] = {}
            self._cache[key][flattened_repetition_ids] = val

    def get_metrics(
        self,
        repetition_ids: RepetitionIDs,
        metric_keys: list[UniqueMetricKey],
        use_cache: bool = True,
    ) -> MetricsData:
        flattened_repetition_ids: tuple[int, ...] = tuple(
            chain(*repetition_ids.values())
        )
        metrics_to_get: MetricsData = {}
        metrics_from_cache: MetricsData = {}
        for key in metric_keys:
            if use_cache:
                metric = self._cache.get(key, {}).get(flattened_repetition_ids, None)
                if metric:
                    metrics_from_cache[key] = metric
                else:
                    metrics_to_get[key] = []
            else:
                metrics_to_get[key] = []

        for size_repetition_ids in repetition_ids.values():
            for key in metrics_to_get.keys():
                stmt = (
                    select(self._metrics_table)
                    .where(self._metrics_table.repetition.in_(size_repetition_ids))
                    .join(self._metrics_dict_table)
                    .where(
                        self._metrics_dict_table.name == key.name,
                        self._metrics_dict_table.unit == key.unit,
                        self._metrics_dict_table.processing_unit == key.processing_unit,
                    )
                )
                rows = self._db_session.execute(stmt).all()
                if not rows:
                    metrics_to_get[key].append(None)
                else:
                    values = [row[0].value for row in rows]
                    metrics_to_get[key].append(float(np.mean(values)))

        if use_cache:
            self.add_data_to_cache(metrics_to_get, repetition_ids)
        return metrics_from_cache | metrics_to_get

    def discover_analysis_keys(self, metric_names: list[str]) -> list[UniqueMetricKey]:
        keys: list[UniqueMetricKey] = []
        if not metric_names:
            keys = list(self.AVAILABLE_ANALYTICS.keys())
        else:
            for name in metric_names:
                for key in self.AVAILABLE_ANALYTICS.keys():
                    if name == key.name:
                        keys.append(key)
        return keys

    def get_analyses(
        self,
        repetition_ids: RepetitionIDs,
        analyses_keys: list[UniqueMetricKey],
        use_cache: bool = True,
    ) -> MetricsData:
        flattened_repetition_ids: tuple[int, ...] = tuple(
            chain(*repetition_ids.values())
        )
        analyses_to_get: MetricsData = {}
        analyses_from_cache: MetricsData = {}
        for analysis_key in analyses_keys:
            if use_cache:
                metric = self._cache.get(analysis_key, {}).get(
                    flattened_repetition_ids, None
                )
                if metric:
                    analyses_from_cache[analysis_key] = metric
                    continue
            func = self.AVAILABLE_ANALYTICS.get(analysis_key, None)
            if func is not None:
                analyses_to_get[analysis_key] = func(repetition_ids)

        if use_cache:
            self.add_data_to_cache(analyses_to_get, repetition_ids)
        return analyses_from_cache | analyses_to_get

    def get_data(
        self,
        repetition_ids: RepetitionIDs,
        metrics_names: list[str],
        analyses_names: list[str],
    ) -> MetricsData:
        metrics: MetricsData = self.get_metrics(
            repetition_ids, self.discover_metric_keys(metrics_names)
        )
        metrics |= self.get_analyses(
            repetition_ids, self.discover_analysis_keys(analyses_names)
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
                self.in_memory_task_sizes.rows[task_size_name][1] / machine_num_of_cores
            )
            x_tick_labels.append(task_size_name)
        return x_range, x_tick_labels


class DataRetrieversManager:
    retrievers: dict[str, DataRetriever] = {}

    @classmethod
    def init_retriever(cls, name: str) -> None:
        path = get_extension_path(name) / "plotter.py"
        spec = util.spec_from_file_location(path.stem, path)
        if spec is not None:
            module = util.module_from_spec(spec)
            if spec.loader is not None:
                module.__package__ = "quare.extensions." + path.parent.stem
                spec.loader.exec_module(module)
                retriever: DataRetriever = module.__extension_data_retriever__(
                    get_db_session(),
                    module.__extension_metrics_table__,
                    module.__extension_metrics_dict__,
                )
        cls.retrievers[name] = retriever

    @classmethod
    def get_retriever(cls, name: str) -> DataRetriever:
        retriever = cls.retrievers.get(name, None)
        if not retriever:
            cls.init_retriever(name)
            retriever = cls.retrievers[name]
        return retriever
