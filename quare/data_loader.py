"""
Generic database-loading infrastructure for preprocessed profiler data.

:class:`DataLoader` is the main workhorse: it walks a preprocessed-data
directory tree, resolves or creates the relevant contextual rows
(:class:`~quare.models.ProfilingSession`, :class:`~quare.models.Machine`,
:class:`~quare.models.UseCase`, :class:`~quare.models.TaskSizesDict`,
:class:`~quare.models.Repetition`), and delegates the actual metric parsing to
extension-supplied callback functions.

:class:`MetricContext` is a lightweight value object that bundles the
information a loader callback needs to create metric rows.

Expected directory layout
--------------------------
::

    <preprocessed_data_path>/
    └── <session>/
        └── <machine>/
            └── <use_case>/
                └── <task_size>/
                    └── <YYYYMMDD_HHMMSS>/
                        └── <profiler>/
                            ├── <stem>.machine_info.csv
                            ├── <stem>.core_metrics.csv
                            └── …
"""

from __future__ import annotations

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
    """
    Lightweight bundle passed to extension loader callbacks.

    Carries the two pieces of information that every callback needs to create
    :class:`~quare.models.MetricsBase` rows: which file to read and which
    :class:`~quare.models.Repetition` the resulting rows belong to.

    :ivar file_path: Path to the specific CSV file to be loaded by the callback.
    :vartype file_path: pathlib.Path
    :ivar repetition_id: Primary-key ID of the :class:`~quare.models.Repetition`
        row that owns the metrics in *file_path*.
    :vartype repetition_id: int
    """

    file_path: Path
    repetition_id: int


DBBaseGeneric = TypeVar("DBBaseGeneric", bound=DBBase)


class DataLoader:
    """
    Orchestrates the loading of preprocessed profiler files into the database.

    Walks a preprocessed-data directory, derives contextual metadata from the
    directory structure, ensures the required
    :class:`~quare.models.ProfilingSession`, :class:`~quare.models.Machine`,
    :class:`~quare.models.UseCase`, :class:`~quare.models.TaskSizesDict`, and
    :class:`~quare.models.Repetition` rows exist, then calls the
    extension-supplied functions to parse individual CSV files and insert
    metric rows.

    :ivar in_memory_metrics: Cache of metric-dictionary rows used to avoid
        repeated DB round-trips during bulk loading.
    :vartype in_memory_metrics: quare.utils.InMemoryMetricsDict
    """

    T = TypeVar("T")

    def __init__(
        self,
        db_session: Session,
        preprocessed_data_path: Path,
        metrics_table: type[MetricsBase],
        metrics_dict_table: type[MetricsDictBase],
    ) -> None:
        """
        Initialise a DataLoader for a specific extension's metric tables.

        :param db_session: Active SQLAlchemy session used for all DB operations.
        :type db_session: sqlalchemy.orm.Session
        :param preprocessed_data_path: Root directory of preprocessed data,
            used both as the glob root and as the base for
            :meth:`extract_from_path`.
        :type preprocessed_data_path: pathlib.Path
        :param metrics_table: The extension's concrete
            :class:`~quare.models.MetricsBase` subclass (e.g.
            ``AMDuProfPCM_metrics``).
        :type metrics_table: type[quare.models.MetricsBase]
        :param metrics_dict_table: The extension's concrete
            :class:`~quare.models.MetricsDictBase` subclass (e.g.
            ``AMDuProfPCM_metrics_dict``).
        :type metrics_dict_table: type[quare.models.MetricsDictBase]
        """
        self._db_session: Session = db_session
        self._data_path: Path = preprocessed_data_path
        self._metrics_table: type[MetricsBase] = metrics_table
        self._metrics_dict_table: type[MetricsDictBase] = metrics_dict_table

        self.in_memory_metrics = InMemoryMetricsDict(db_session, metrics_dict_table)

    def extract_from_path(self, key: str, file_path: Path) -> str:
        """
        Extract a specific path component from a preprocessed data file path.

        The preprocessed directory hierarchy is expected to follow the
        canonical layout::

            <preprocessed_root>/<session>/<machine>/<use_case>/<task_size>/<date>/…

        The *key* selects which path segment(s) to return, joined by ``"."``.

        :param key: One of ``"session"``, ``"machine"``, ``"use_case"``,
            ``"task_size"``, or ``"repetition_&_date"`` (the date/timestamp
            directory).
        :type key: str
        :param file_path: Absolute or relative path to the file whose components
            should be extracted.  Must be located inside
            :attr:`_data_path`.
        :type file_path: pathlib.Path
        :returns: The dot-joined path segment(s) corresponding to *key*.
        :rtype: str
        :raises KeyError: If *key* is not one of the recognised component names.
        :raises ValueError: If *file_path* is not relative to :attr:`_data_path`.
        """
        path_struct: dict[str, tuple[int, ...]] = {
            "session": (0,),
            "machine": (1,),
            "use_case": (2,),
            "task_size": (3,),
            "repetition_&_date": (4,),
        }
        file_path = file_path.relative_to(self._data_path)
        return ".".join(file_path.parts[i] for i in path_struct[key])

    def create_if_not_exists(
        self,
        to_create: DBBaseGeneric,
        where_column: InstrumentedAttribute[T],
        equal_to: T,
    ) -> DBBaseGeneric:
        """
        Return the existing DB row matching *equal_to*, or stage *to_create*.

        Queries *where_column* for a row where the column equals *equal_to*.
        If a row is found it is returned unchanged.  If no row is found,
        *to_create* is added to the session (but **not** committed — the caller
        must call ``session.commit()`` before using the returned object's ``id``).

        :param to_create: ORM instance to add to the session if no matching
            row exists.
        :type to_create: DBBaseGeneric
        :param where_column: The column to filter on
            (e.g. ``ProfilingSession.name``).
        :type where_column: sqlalchemy.orm.InstrumentedAttribute[T]
        :param equal_to: The value to match against *where_column*.
        :type equal_to: T
        :returns: Either the existing ORM instance fetched from the DB or
            *to_create* if it was freshly staged.
        :rtype: DBBaseGeneric
        """
        selected_row = self._db_session.execute(
            select(where_column.parent).where(where_column == equal_to)
        ).first()

        if not selected_row:
            self._db_session.add(to_create)
            return to_create
        return selected_row[0]

    def record_exists(
        self,
        where_column: InstrumentedAttribute[T],
        is_equal_to: T,
    ) -> bool:
        """
        Check whether a row with the given column value exists in the database.

        :param where_column: The column to filter on
            (e.g. ``Repetition.name``).
        :type where_column: sqlalchemy.orm.InstrumentedAttribute[T]
        :param is_equal_to: The value to match.
        :type is_equal_to: T
        :returns: ``True`` if at least one matching row exists, ``False``
            otherwise.
        :rtype: bool
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
        """
        Build a single metric-value ORM instance, creating the dictionary
        entry if it does not yet exist.

        Looks up ``(name, unit, processing_unit)`` in the in-memory metrics
        cache.  On a cache miss, inserts a new row into the metrics-dictionary
        table, commits, and refreshes the cache before proceeding.

        :param context: Bundle containing the source file path and the
            repetition ID to associate with the new metric row.
        :type context: MetricContext
        :param name: Metric name as it appears in the profiler's output
            (e.g. ``"L2 Miss (pti)"``).
        :type name: str
        :param value: Numerical measurement value.
        :type value: float
        :param unit: Physical unit string (e.g. ``"%"``, ``"MHz"``, or ``""``).
        :type unit: str
        :param processing_unit_idx: Zero-based index of the hardware entity
            (e.g. core 0) this measurement belongs to, or ``None`` when not
            applicable.
        :type processing_unit_idx: int or None
        :param processing_unit: Hardware entity category this measurement
            belongs to (e.g. ``"core"``, ``"ccx"``).
        :type processing_unit: str
        :returns: An unsaved :class:`~quare.models.MetricsBase` ORM instance
            ready to be added to the session.
        :rtype: quare.models.MetricsBase
        """
        metric_key = f"{name}\x00{unit}\x00{processing_unit}"
        if metric_key not in self.in_memory_metrics.rows:
            metric = self._metrics_dict_table(
                name=name, unit=unit, processing_unit=processing_unit
            )
            self._db_session.add(metric)
            self._db_session.commit()
            self.in_memory_metrics.update()

        instance = self._metrics_table(
            repetition=context.repetition_id,
            processing_unit_idx=processing_unit_idx,
            metric=self.in_memory_metrics.rows[metric_key],
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
        Convert a wide-format metrics DataFrame into a list of ORM instances.

        The DataFrame is expected to have:

        * **Rows** — one per hardware processing unit (core, CCX, …).  The
          row index (``row.name``) must be a string where the numeric suffix
          starting at position *index_trimmer* gives the unit's index.
        * **Columns** — one per metric name.

        Each (row, column) cell becomes one :class:`~quare.models.MetricsBase`
        instance via :meth:`create_metric_instance`.

        :param context: Bundle of file path and repetition ID.
        :type context: MetricContext
        :param metrics_csv: Wide-format DataFrame of metric values.
        :type metrics_csv: pandas.DataFrame
        :param index_trimmer: Number of leading characters to strip from the
            row-index string to obtain the integer processing-unit index
            (e.g. ``5`` strips ``"Core "`` from ``"Core 0"`` → ``0``).
        :type index_trimmer: int
        :param processing_unit: Processing-unit category name stored in the
            metrics-dictionary (e.g. ``"core"``, ``"ccx"``).
        :type processing_unit: str
        :returns: List of unsaved :class:`~quare.models.MetricsBase` ORM
            instances, one per (row, column) cell.
        :rtype: list[quare.models.MetricsBase]
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
        file_suffixes: list[tuple[str, Callable[[DataLoader, MetricContext], list]]],
    ) -> None:
        """
        Walk the preprocessed-data directory tree and load all new repetitions.

        For each file matching
        ``<preprocessed_root>/**/<dir_name_pattern>/**/*.<first_suffix>``
        the method:

        1. Derives the repetition name from the path.
        2. Skips the repetition if it already exists in the DB
           (:meth:`record_exists`).
        3. Ensures :class:`~quare.models.ProfilingSession`,
           :class:`~quare.models.Machine`, :class:`~quare.models.UseCase`, and
           :class:`~quare.models.TaskSizesDict` rows exist.
        4. Creates a :class:`~quare.models.Repetition` row.
        5. Calls each ``(suffix, function)`` pair in *file_suffixes*, passing a
           :class:`MetricContext` pointing at ``<stem><suffix>``.
        6. Sets ``repetition.data_consistent = True`` and commits.

        :param dir_name_pattern: Glob pattern for the profiler directory name
            inside the data tree (e.g. ``"AMDuProfPCM"``).
        :type dir_name_pattern: str
        :param file_suffixes: Ordered list of ``(file_suffix, loader_function)``
            pairs.  The first entry's suffix is used to discover repetitions via
            glob.  Each *loader_function* receives this :class:`DataLoader`
            instance and a :class:`MetricContext`, and must return a list of
            ORM instances to add to the session.
        :type file_suffixes: list[tuple[str, Callable[[DataLoader, MetricContext],
            list]]]
        """
        in_memory_task_sizes = InMemoryTaskSizesDict(self._db_session)
        settings = load_settings()

        for input_path in Path(self._data_path).glob(
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
            if task_size_size is None:
                try:
                    task_size_size = int(task_size_name)
                except ValueError:
                    pass
            if task_size_name not in in_memory_task_sizes.rows.keys():
                task_size = TaskSizesDict(name=task_size_name, size=task_size_size)
                self._db_session.add(task_size)
                self._db_session.commit()
                in_memory_task_sizes.update()

            # Commit to obtain auto-generated IDs for the rows added above.
            self._db_session.commit()

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
