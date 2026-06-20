"""
Core SQLAlchemy ORM models shared across all Quare extensions.

The tables defined here capture the experimental context (which session, on
which machine, for which application, at what task size) that frames every
individual profiling measurement.  Extension-specific metric tables reference
these via foreign keys.

Database layout
---------------
::

    ProfilingSession ─┐
    Machine          ─┤─ Repetition ─── <ext>_metrics
    UseCase          ─┤
    TaskSizesDict    ─┘

Abstract bases
--------------
:class:`MetricsDictBase` and :class:`MetricsBase` are *not* mapped to tables
directly.  Each extension subclasses them to produce its own
``<profiler>_metrics_dict`` and ``<profiler>_metrics`` tables.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class DBBase(DeclarativeBase):
    """
    Declarative base class for all Quare ORM models.

    All mapped classes (both core and extension-specific) inherit from this
    class so that ``DBBase.metadata.create_all(engine)`` creates every table
    in a single call.
    """


class ProfilingSession(DBBase):
    """
    Represents a named profiling campaign (a logical group of repetitions).

    A profiling session typically corresponds to one experimental study, e.g.
    ``"Session1_strongScaling"``.  Multiple repetitions across different
    machines and task sizes belong to the same session.

    :ivar id: Auto-incremented primary key.
    :vartype id: int
    :ivar name: Unique human-readable session identifier (max 256 chars).
    :vartype name: str
    :ivar desc: Optional free-text description of the session.
    :vartype desc: str or None
    """

    __tablename__ = "Profiling_session"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(256), unique=True)
    desc: Mapped[str | None] = mapped_column(String(4096))


class Machine(DBBase):
    """
    Represents a physical or virtual compute node on which profiling was done.

    :ivar id: Auto-incremented primary key.
    :vartype id: int
    :ivar name: Unique machine identifier, e.g. ``"ROME_128"`` (max 256 chars).
    :vartype name: str
    :ivar desc: Optional free-text description (max 1024 chars).
    :vartype desc: str or None
    :ivar num_of_cores: Total number of physical CPU cores, if known.
    :vartype num_of_cores: int or None
    :ivar num_of_threads: Total number of hardware threads (logical CPUs), if known.
    :vartype num_of_threads: int or None
    """

    __tablename__ = "Machine"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(256), unique=True)
    desc: Mapped[str | None] = mapped_column(String(1024))
    num_of_cores: Mapped[int | None]
    num_of_threads: Mapped[int | None]


class UseCase(DBBase):
    """
    Represents the application or workload being profiled.

    :ivar id: Auto-incremented primary key.
    :vartype id: int
    :ivar name: Unique workload identifier, e.g. ``"motorBike"`` (max 256 chars).
    :vartype name: str
    :ivar desc: Optional free-text description (max 1024 chars).
    :vartype desc: str or None
    """

    __tablename__ = "Use_case"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(256), unique=True)
    desc: Mapped[str | None] = mapped_column(String(1024))


class TaskSizesDict(DBBase):
    """
    Lookup table mapping symbolic task-size names to integer values.

    The integer value encodes the problem size in a domain-specific unit
    (e.g. number of mesh cells) and is used as the x-axis for scaling plots.

    :ivar id: Auto-incremented primary key.
    :vartype id: int
    :ivar name: Unique symbolic name, e.g. ``"small"``, ``"mid"`` (max 32 chars).
    :vartype name: str
    :ivar size: Numeric problem size corresponding to the symbolic name, if known.
    :vartype size: int or None
    """

    __tablename__ = "Task_sizes_dict"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(32), unique=True)
    size: Mapped[int | None]


class Repetition(DBBase):
    """
    Represents a single profiling run — one (session, machine, use-case, size) tuple.

    A *repetition* is the atomic unit of data in Quare: every metric value
    is ultimately associated with a repetition.  Multiple repetitions may share
    the same (session, machine, use-case, size) combination when an experiment
    is repeated for statistical reliability.

    :ivar id: Auto-incremented primary key.
    :vartype id: int
    :ivar name: Unique run identifier, typically
        ``"<YYYYMMDD_HHMMSS>.<session_name>"`` (max 64 chars).
    :vartype name: str
    :ivar profiling_session: Foreign key into :class:`ProfilingSession`.
    :vartype profiling_session: int
    :ivar machine: Foreign key into :class:`Machine`.
    :vartype machine: int
    :ivar use_case: Foreign key into :class:`UseCase`.
    :vartype use_case: int
    :ivar task_size: Foreign key into :class:`TaskSizesDict`.
    :vartype task_size: int
    :ivar date: Timestamp of the run, parsed from the directory name.
    :vartype date: datetime.datetime or None
    :ivar exec_time_s: Wall-clock execution time in seconds, if available.
    :vartype exec_time_s: float or None
    :ivar file_dir: Absolute POSIX path to the directory containing the raw
        preprocessed files for this run (max 3841 chars — 4096 minus 255 for
        the filename, matching default Linux limits).
    :vartype file_dir: str
    :ivar data_consistent: Set to ``True`` only after all metric rows for this
        repetition have been successfully committed, enabling detection of
        partial imports.
    :vartype data_consistent: bool
    """

    __tablename__ = "Repetition"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    profiling_session: Mapped[int] = mapped_column(ForeignKey(ProfilingSession.id))
    machine: Mapped[int] = mapped_column(ForeignKey(Machine.id))
    use_case: Mapped[int] = mapped_column(ForeignKey(UseCase.id))
    task_size: Mapped[int] = mapped_column(ForeignKey(TaskSizesDict.id))
    date: Mapped[datetime | None]
    exec_time_s: Mapped[float | None]
    # Length set according to some default Linux limits:
    file_dir: Mapped[str] = mapped_column(String(4096 - 255))
    data_consistent: Mapped[bool] = mapped_column(default=False)


class MetricsDictBase(DBBase):
    """
    Abstract base for profiler-specific metric-dictionary tables.

    Each extension subclasses this to create a ``<profiler>_metrics_dict``
    table that enumerates all metric types produced by that profiler.  A
    *unique constraint* on ``(name, unit, processing_unit)`` prevents
    duplicate entries.

    Subclasses must set ``__tablename__`` and optionally
    ``__table_args__ = {"extend_existing": True}``.

    :ivar id: Auto-incremented primary key.
    :vartype id: int
    :ivar name: Metric name as reported by the profiler (max 128 chars),
        e.g. ``"L2 Miss (pti)"``.
    :vartype name: str
    :ivar unit: Physical unit string (max 16 chars), e.g. ``"%"``, ``"MHz"``,
        or ``""`` when dimensionless.
    :vartype unit: str
    :ivar processing_unit: Hardware entity this metric is measured per
        (max 16 chars), e.g. ``"core"``, ``"ccx"``, ``"function"``.
    :vartype processing_unit: str
    :ivar desc: Optional human-readable description of the metric
        (max 1024 chars).
    :vartype desc: str or None
    """

    __abstract__ = True
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), name="name")
    unit: Mapped[str] = mapped_column(String(16), name="unit")
    processing_unit: Mapped[str] = mapped_column(String(16), name="processing_unit")
    desc: Mapped[str | None] = mapped_column(String(1024))

    __table_args__ = (UniqueConstraint(name, unit, processing_unit),)


class MetricsBase(DBBase):
    """
    Abstract base for profiler-specific metric-value tables.

    Each extension subclasses this to create a ``<profiler>_metrics`` table
    that stores individual numerical measurements.  Subclasses **must** define
    a ``metric`` column as a foreign key into the corresponding
    :class:`MetricsDictBase` subclass; this is enforced by
    :meth:`__init_subclass__`.

    Column ordering hints (``sort_order``) keep ``id`` and ``repetition``
    as the leading columns in the physical table, and ``value`` last.

    :ivar id: Auto-incremented primary key.
    :vartype id: int
    :ivar repetition: Foreign key into :class:`Repetition`.
    :vartype repetition: int
    :ivar processing_unit_idx: Zero-based index of the hardware entity
        (e.g. core number 0–127) this measurement belongs to.  ``None`` when
        the metric is not per-entity (e.g. a function-level MPI metric).
    :vartype processing_unit_idx: int or None
    :ivar metric: Foreign key into the extension's metrics-dictionary table.
        Must be defined by every concrete subclass.
    :vartype metric: int
    :ivar value: The recorded measurement value.
    :vartype value: float
    """

    __abstract__ = True
    id: Mapped[int] = mapped_column(primary_key=True, sort_order=-10)
    repetition: Mapped[int] = mapped_column(ForeignKey(Repetition.id), sort_order=-9)
    processing_unit_idx: Mapped[int | None] = mapped_column(sort_order=-8)
    metric: None = None
    value: Mapped[float] = mapped_column(sort_order=10)

    @classmethod
    def __raise_error(cls, name: str) -> None:
        raise NotImplementedError(
            f"{name} class must have a 'metric' attribute "
            + "as a foreign key to a MetricsDict model"
        )

    def __init_subclass__(cls, **kw: Any) -> None:
        """
        Validate that every concrete subclass defines a ``metric`` foreign key.

        Called automatically by Python when a class inherits from
        :class:`MetricsBase`.  Raises :exc:`NotImplementedError` if the
        subclass has not overridden the ``metric`` sentinel with a properly
        typed :class:`~sqlalchemy.orm.Mapped` column.

        :param kw: Keyword arguments forwarded to
            :meth:`object.__init_subclass__`.
        :raises NotImplementedError: If ``metric`` is absent or is not a
            :class:`~sqlalchemy.orm.Mapped` column descriptor.
        """
        if not hasattr(cls, "metric"):
            cls.__raise_error(cls.__name__)
        elif isinstance(Mapped, type) and not isinstance(cls.metric, Mapped):
            # Guard: when Mapped is mocked (docs build), skip the isinstance check.
            cls.__raise_error(cls.__name__)
        return super().__init_subclass__(**kw)
