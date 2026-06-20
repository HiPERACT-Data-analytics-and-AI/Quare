"""
Data-retrieval layer: querying the database and computing derived analyses.

This module provides:

* :class:`UniqueMetricKey` — hashable identifier for a metric type.
* :class:`DataRetriever` — base class for querying raw metrics and computed
  analyses from the database.
* :class:`DataRetrieversManager` — lazy registry that loads the appropriate
  :class:`DataRetriever` subclass for each extension on demand.

Type aliases
------------
:data:`MetricValue`
    A single aggregated measurement value, or ``None`` when data is absent.
:data:`MetricsData`
    Mapping from :class:`UniqueMetricKey` to a per-task-size list of values.
:data:`RepetitionIDs`
    Mapping from task-size name to the list of
    :class:`~quare.models.Repetition` IDs that belong to it.
"""

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


@dataclass
class UniqueMetricKey:
    """
    Hashable identifier for a unique metric type.

    The combination of *name*, *unit*, and *processing_unit* uniquely
    identifies a metric within a profiler's metrics-dictionary table.  This
    dataclass is used as a dictionary key throughout the retrieval and caching
    layers.

    :ivar name: Metric name as stored in the database
        (e.g. ``"L2 Miss (pti)"``).
    :vartype name: str
    :ivar unit: Physical unit of the metric
        (e.g. ``"%"``, ``"MHz"``, or ``""`` for dimensionless).
    :vartype unit: str
    :ivar processing_unit: Hardware entity the metric is measured per
        (e.g. ``"core"``, ``"ccx"``).
    :vartype processing_unit: str
    """

    name: str
    unit: str
    processing_unit: str

    def __hash__(self) -> int:
        """
        Return a hash based on all three identifying fields.

        Uses a tuple hash to avoid the ambiguity that bare string
        concatenation would introduce.

        :returns: Integer hash of ``(name, unit, processing_unit)``.
        :rtype: int
        """
        return hash((self.name, self.unit, self.processing_unit))

    def __repr__(self) -> str:
        """
        Return a human-readable representation for labels and plot titles.

        :returns: String of the form ``"<name> | <unit> | <processing_unit>"``.
        :rtype: str
        """
        return f"{self.name} | {self.unit} | {self.processing_unit}"


MetricValue = float | int | None
"""
A single task-size-level aggregated (averaged) metric value, or ``None``
when the data for that task size is absent.

:alias of: ``float | int | None``
"""

MetricsData = dict[UniqueMetricKey, list[MetricValue]]
"""
Full result set for one or more metrics across all requested task sizes.

Each key unambiguously identifies a metric type; the corresponding value is
a list ordered by the task-size sequence that was requested — one element per
task size, with ``None`` where no data exists.

:alias of: ``dict[UniqueMetricKey, list[MetricValue]]``
"""

RepetitionIDs = dict[str, list[int]]
"""
Mapping from task-size name to the list of
:class:`~quare.models.Repetition` primary-key IDs belonging to that size.

Used throughout :class:`DataRetriever` to scope queries to a specific
(session, machine, use-case) context.

:alias of: ``dict[str, list[int]]``
"""


class DataRetriever:
    """
    Query engine for raw profiler metrics and computed analyses.

    Subclasses register derived analyses in :attr:`AVAILABLE_ANALYTICS` and
    may override :meth:`get_result_info` to include profiler-specific metadata
    in the INFO plot.

    :ivar in_memory_task_sizes: Cache of task-size records used to resolve
        symbolic names to numeric values.
    :vartype in_memory_task_sizes: quare.utils.InMemoryTaskSizesDict
    :ivar AVAILABLE_ANALYTICS: Registry of computed analyses.  Keys are
        :class:`UniqueMetricKey` instances; values are callables that accept a
        :data:`RepetitionIDs` mapping and return a per-task-size
        :data:`MetricsData` value list.
    :vartype AVAILABLE_ANALYTICS: dict[UniqueMetricKey, Callable[[RepetitionIDs], list[MetricValue]]]
    """

    def __init__(
        self,
        db_session: Session,
        metrics_table: type[MetricsBase],
        metrics_dict_table: type[MetricsDictBase],
    ) -> None:
        """
        Initialise the retriever for a specific extension's metric tables.

        :param db_session: Active SQLAlchemy session used for all queries.
        :type db_session: sqlalchemy.orm.Session
        :param metrics_table: The extension's concrete
            :class:`~quare.models.MetricsBase` subclass.
        :type metrics_table: type[quare.models.MetricsBase]
        :param metrics_dict_table: The extension's concrete
            :class:`~quare.models.MetricsDictBase` subclass.
        :type metrics_dict_table: type[quare.models.MetricsDictBase]
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
        Retrieve repetition IDs for the given experimental context.

        For each task size in *task_size_names*, executes a join query across
        :class:`~quare.models.Repetition`, :class:`~quare.models.ProfilingSession`,
        :class:`~quare.models.Machine`, :class:`~quare.models.UseCase`, and
        :class:`~quare.models.TaskSizesDict` with the supplied filter criteria.

        :param session_name_contains: Substring that the session name must
            contain (case-sensitive).
        :type session_name_contains: str
        :param machine_name: Exact machine name to match.
        :type machine_name: str
        :param use_case_name: Exact use-case name to match.
        :type use_case_name: str
        :param task_size_names: Ordered list of task-size names to retrieve;
            determines the order of elements in the returned lists.
        :type task_size_names: list[str]
        :param repetition_name_contains: Substring that the repetition name
            must contain (case-sensitive).
        :type repetition_name_contains: str
        :returns: :data:`RepetitionIDs` mapping each task-size name to the
            list of matching repetition IDs (empty list if none found).
        :rtype: RepetitionIDs
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
        Build a human-readable metadata dictionary for the INFO plot.

        Iterates *repetition_ids* in order and returns on the first repetition
        that can be successfully joined with :class:`~quare.models.Machine`,
        :class:`~quare.models.UseCase`, and
        :class:`~quare.models.ProfilingSession`.

        Subclasses (e.g. :class:`~quare.extensions.amduprof_data_retriever.AMDuProfDataRetriever`)
        can override this method to include profiler-specific fields and merge
        the result with ``super().get_result_info()``.

        :param repetition_ids: Mapping produced by :meth:`get_repetitions`.
        :type repetition_ids: RepetitionIDs
        :returns: Dictionary whose keys are display labels and values are the
            corresponding metadata strings (or numbers coerced to strings by
            the plot layer).  Returns an empty dict if no valid repetition is
            found.
        :rtype: dict[str, str]
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
        Resolve metric names to :class:`UniqueMetricKey` objects via the DB.

        When *metric_names* is non-empty, only metrics whose ``name`` column
        appears in the list are returned.  When *metric_names* is empty, every
        metric in the dictionary table is returned.

        The returned list may differ in length from *metric_names* because:

        * A requested name may not exist in the database.
        * A single name may match multiple rows (different units or
          processing-unit categories).

        :param metric_names: List of metric names to look up, or ``[]`` to
            return all metrics.
        :type metric_names: list[str]
        :returns: List of :class:`UniqueMetricKey` instances for all matching
            rows in the metrics-dictionary table.
        :rtype: list[UniqueMetricKey]
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
        """
        Store freshly-fetched metrics in the two-level in-memory cache.

        The cache is keyed first by :class:`UniqueMetricKey` and then by the
        sorted tuple of all repetition IDs (flattened across all task sizes)
        that were used to fetch the data.

        :param data: Metrics data to cache, as returned by a DB query loop.
        :type data: MetricsData
        :param repetition_ids: The :data:`RepetitionIDs` that were used to
            fetch *data*; used to construct the inner cache key.
        :type repetition_ids: RepetitionIDs
        """
        flattened_repetition_ids: tuple[int, ...] = tuple(
            chain(*repetition_ids.values())
        )
        for key, val in data.items():
            if key not in self._cache:
                self._cache[key] = {}
            self._cache[key][flattened_repetition_ids] = val

    def get_metrics(
        self,
        repetition_ids: RepetitionIDs,
        metric_keys: list[UniqueMetricKey],
        use_cache: bool = True,
    ) -> MetricsData:
        """
        Fetch raw metric values from the database (or the cache).

        For each key in *metric_keys* and each task size in *repetition_ids*,
        queries all metric rows for the matching repetitions, averages them
        using :func:`numpy.mean`, and appends the result to the per-key list.
        ``None`` is appended for task sizes with no data.

        :param repetition_ids: Scope returned by :meth:`get_repetitions`.
        :type repetition_ids: RepetitionIDs
        :param metric_keys: List of metrics to fetch.
        :type metric_keys: list[UniqueMetricKey]
        :param use_cache: Whether to consult and populate the in-memory cache.
            Pass ``False`` to force a fresh database query.
        :type use_cache: bool
        :returns: :data:`MetricsData` mapping each key to a per-task-size list
            of averaged values (or ``None`` for missing data).
        :rtype: MetricsData
        """
        flattened_repetition_ids: tuple[int, ...] = tuple(
            chain(*repetition_ids.values())
        )
        metrics_to_get: MetricsData = {}
        metrics_from_cache: MetricsData = {}
        for key in metric_keys:
            if use_cache:
                metric = self._cache.get(key, {}).get(flattened_repetition_ids, None)
                if metric is not None:
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
        """
        Resolve analysis names to :class:`UniqueMetricKey` objects.

        Searches :attr:`AVAILABLE_ANALYTICS` for entries whose ``name``
        matches any item in *metric_names*.  When *metric_names* is empty,
        all registered analyses are returned.

        :param metric_names: List of analysis names to look up, or ``[]`` to
            return all registered analyses.
        :type metric_names: list[str]
        :returns: List of :class:`UniqueMetricKey` instances for all matching
            registered analyses.
        :rtype: list[UniqueMetricKey]
        """
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
        """
        Compute derived analyses and return them as :data:`MetricsData`.

        For each key in *analyses_keys*, looks up its callable in
        :attr:`AVAILABLE_ANALYTICS` and invokes it with *repetition_ids*.
        Results are cached after computation.

        :param repetition_ids: Scope returned by :meth:`get_repetitions`.
        :type repetition_ids: RepetitionIDs
        :param analyses_keys: List of analysis keys to compute.
        :type analyses_keys: list[UniqueMetricKey]
        :param use_cache: Whether to consult and populate the in-memory cache.
        :type use_cache: bool
        :returns: :data:`MetricsData` mapping each analysis key to its
            per-task-size value list.
        :rtype: MetricsData
        """
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
                if metric is not None:
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
        """
        Convenience method: fetch raw metrics and computed analyses in one call.

        Delegates to :meth:`get_metrics` (via :meth:`discover_metric_keys`)
        and :meth:`get_analyses` (via :meth:`discover_analysis_keys`), then
        merges the results into a single :data:`MetricsData` dict.

        :param repetition_ids: Scope returned by :meth:`get_repetitions`.
        :type repetition_ids: RepetitionIDs
        :param metrics_names: Names of raw metrics to fetch, or ``[]`` for
            all metrics in the dictionary table.
        :type metrics_names: list[str]
        :param analyses_names: Names of derived analyses to compute, or ``[]``
            for all registered analyses.
        :type analyses_names: list[str]
        :returns: Merged :data:`MetricsData` containing both raw metrics and
            computed analyses.
        :rtype: MetricsData
        """
        metrics: MetricsData = self.get_metrics(
            repetition_ids, self.discover_metric_keys(metrics_names)
        )
        metrics |= self.get_analyses(
            repetition_ids, self.discover_analysis_keys(analyses_names)
        )
        return metrics

    def get_machine_cores_count(self, machine_name: str) -> int | None:
        """
        Look up the core count for a machine by name.

        :param machine_name: Exact machine name as stored in the
            :class:`~quare.models.Machine` table.
        :type machine_name: str
        :returns: Number of physical cores, or ``None`` if the machine is not
            found or the value was not recorded.
        :rtype: int or None
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
        """
        Compute the x-axis values and tick labels for a scaling plot.

        Each x value is the ratio ``task_size / num_of_cores``, expressing
        the problem size *per core* — the natural independent variable in
        strong-scaling studies.

        :param sizes: Ordered list of task-size names (must all exist in
            :attr:`in_memory_task_sizes`).
        :type sizes: list[str]
        :param machine_name: Exact machine name used to look up the core count.
        :type machine_name: str
        :returns: A 2-tuple of:

            * ``x_range`` — list of ``task_size / num_of_cores`` float values,
              one per entry in *sizes*.
            * ``x_tick_labels`` — list of task-size name strings, matching the
              order of *sizes*.
        :rtype: tuple[list[float], list[str]]
        :raises Exception: If *machine_name* has no recorded core count in the
            database.
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
    """
    Lazy registry of :class:`DataRetriever` instances, one per extension.

    Retriever objects are loaded on first access by dynamically importing each
    extension's ``plotter.py`` module.  The shared ``retrievers`` dict is a
    class variable, making this a global registry for the process lifetime.

    :cvar retrievers: Maps extension names to their instantiated
        :class:`DataRetriever` subclasses.
    :vartype retrievers: dict[str, DataRetriever]
    """

    retrievers: dict[str, DataRetriever] = {}

    @classmethod
    def init_retriever(cls, name: str) -> None:
        """
        Dynamically load and instantiate the :class:`DataRetriever` for *name*.

        Imports the extension's ``plotter.py``, reads the
        ``__extension_data_retriever__``, ``__extension_metrics_table__``, and
        ``__extension_metrics_dict__`` module-level attributes, and stores the
        resulting instance in :attr:`retrievers`.

        :param name: Bare extension name without the ``_ext`` suffix
            (e.g. ``"AMDuProfPCM"``).
        :type name: str
        :raises RuntimeError: If the extension's ``plotter.py`` cannot be
            imported (spec is ``None`` or has no loader).
        :raises ValueError: If no extension directory named ``<name>_ext``
            exists (propagated from :func:`~quare.utils.get_extension_path`).
        """
        path = get_extension_path(name) / "plotter.py"
        spec = util.spec_from_file_location(path.stem, path)
        if spec is None:
            raise RuntimeError(f"Could not load spec for extension '{name}' at {path}")
        module = util.module_from_spec(spec)
        if spec.loader is None:
            raise RuntimeError(f"Spec for extension '{name}' has no loader")
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
        """
        Return the :class:`DataRetriever` for *name*, loading it if necessary.

        On the first call for a given *name*, delegates to
        :meth:`init_retriever`.  Subsequent calls return the cached instance.

        :param name: Bare extension name without the ``_ext`` suffix.
        :type name: str
        :returns: The :class:`DataRetriever` (or subclass) instance for the
            requested extension.
        :rtype: DataRetriever
        :raises RuntimeError: If loading the extension fails (propagated from
            :meth:`init_retriever`).
        """
        retriever = cls.retrievers.get(name, None)
        if not retriever:
            cls.init_retriever(name)
            retriever = cls.retrievers[name]
        return retriever
