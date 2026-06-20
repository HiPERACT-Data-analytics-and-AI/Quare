"""
ORM models for the AMD uProf MPI profiler extension.

These tables capture MPI environment metadata and per-function / per-rank
timing and communication metrics collected by the AMD uProf MPI profiler.

All tables use ``extend_existing=True`` so that they can be safely re-imported
during dynamic extension discovery.
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from ...models import DBBase, MetricsBase, MetricsDictBase, Repetition


class AMDuProfMPI_environment(DBBase):
    """
    MPI environment metadata for one profiling repetition.

    One row is inserted per :class:`~quare.models.Repetition`.  The data
    originates from the ``ENVIRONMENT`` section of the raw AMD uProf MPI CSV.

    :ivar id: Auto-incremented primary key.
    :vartype id: int
    :ivar repetition: Foreign key into :class:`~quare.models.Repetition`.
    :vartype repetition: int
    :ivar total_ranks: Total number of MPI ranks used in the run.
    :vartype total_ranks: int or None
    :ivar lib_version: MPI library version string (max 256 chars).
    :vartype lib_version: str or None
    :ivar std_version: MPI standard version string, e.g. ``"3.1"``
        (max 16 chars).
    :vartype std_version: str or None
    """

    __table_args__ = {"extend_existing": True}
    __tablename__ = "AMDuProfMPI_environment"
    id: Mapped[int] = mapped_column(primary_key=True)
    repetition: Mapped[int] = mapped_column(ForeignKey(Repetition.id))
    total_ranks: Mapped[int | None]
    lib_version: Mapped[str | None] = mapped_column(String(256))
    std_version: Mapped[str | None] = mapped_column(String(16))


class AMDuProfMPI_metrics_dict(MetricsDictBase):
    """
    Metric-dictionary table for the AMD uProf MPI profiler.

    Enumerates all metric types produced by AMD uProf MPI (e.g.
    ``"MPI Time(seconds)"``, ``"MPI_Allreduce"``, ``"Volume(Bytes)"``).
    Inherits the unique constraint on ``(name, unit, processing_unit)``
    from :class:`~quare.models.MetricsDictBase`.
    """

    __table_args__ = {"extend_existing": True}
    __tablename__ = "AMDuProfMPI_metrics_dict"


class AMDuProfMPI_metrics(MetricsBase):
    """
    Metric-value table for the AMD uProf MPI profiler.

    Each row stores one aggregated MPI metric value for a single
    (repetition, processing-unit, metric) combination.  The processing
    unit is either ``"function"`` (for function-level summaries) or
    ``"rank"`` (for per-rank summaries).

    :ivar metric: Foreign key into :class:`AMDuProfMPI_metrics_dict`.
    :vartype metric: int
    """

    __table_args__ = {"extend_existing": True}
    __tablename__ = "AMDuProfMPI_metrics"
    metric: Mapped[int] = mapped_column(ForeignKey(AMDuProfMPI_metrics_dict.id))
