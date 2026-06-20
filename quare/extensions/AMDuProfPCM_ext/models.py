"""
ORM models for the AMD uProf Performance Counter Monitor (PCM) extension.

These tables capture AMD-specific hardware topology and per-core / per-CCX
performance counter metrics collected by the AMD uProf PCM profiler.

All tables use ``extend_existing=True`` so that they can be safely re-imported
if the module is loaded multiple times during the dynamic extension discovery
process in :func:`~quare.create_db.create_db`.
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from ...models import DBBase, MetricsBase, MetricsDictBase, Repetition


class AMDuProfPCM_machine_info(DBBase):
    """
    CPU topology summary for one profiling repetition (AMD uProf PCM).

    One row is inserted per :class:`~quare.models.Repetition`.  The data
    originates from the ``machine_info`` section of the raw AMD uProf CSV.

    :ivar id: Auto-incremented primary key.
    :vartype id: int
    :ivar repetition: Foreign key into :class:`~quare.models.Repetition`.
    :vartype repetition: int
    :ivar system: System / hostname string reported by AMD uProf (max 256 chars).
    :vartype system: str
    :ivar num_of_sockets: Number of physical CPU sockets on the node.
    :vartype num_of_sockets: int or None
    :ivar num_of_ccds: Number of Core Complex Dies (CCDs) across all sockets.
    :vartype num_of_ccds: int or None
    :ivar num_of_ccxs: Number of Core Complexes (CCXs) across all CCDs.
    :vartype num_of_ccxs: int or None
    :ivar num_of_cores: Total number of physical cores.
    :vartype num_of_cores: int or None
    :ivar num_of_threads: Total number of hardware threads (logical CPUs).
    :vartype num_of_threads: int or None
    :ivar smt_enabled_in_hw: Whether Simultaneous Multi-Threading is supported
        by the hardware.
    :vartype smt_enabled_in_hw: bool
    :ivar smt_enabled_in_os: Whether SMT is enabled at the OS level.
    :vartype smt_enabled_in_os: bool
    :ivar num_of_threads_sharing_l3: Number of hardware threads sharing a
        single L3 cache slice.
    :vartype num_of_threads_sharing_l3: int or None
    """

    __table_args__ = {"extend_existing": True}
    __tablename__ = "AMDuProfPCM_machine_info"
    id: Mapped[int] = mapped_column(primary_key=True)
    repetition: Mapped[int] = mapped_column(ForeignKey(Repetition.id))
    system: Mapped[str] = mapped_column(String(256))
    num_of_sockets: Mapped[int | None]
    num_of_ccds: Mapped[int | None]
    num_of_ccxs: Mapped[int | None]
    num_of_cores: Mapped[int | None]
    num_of_threads: Mapped[int | None]
    smt_enabled_in_hw: Mapped[bool]
    smt_enabled_in_os: Mapped[bool]
    num_of_threads_sharing_l3: Mapped[int | None]


class AMDuProfPCM_machine_cpu_topology(DBBase):
    """
    Per-socket / CCD / CCX topology row for one profiling repetition (AMD uProf PCM).

    Each row represents one line from the ``machine_cpu_topology`` section of
    the raw AMD uProf CSV (one row per CCD/CCX entry).

    :ivar id: Auto-incremented primary key.
    :vartype id: int
    :ivar repetition: Foreign key into :class:`~quare.models.Repetition`.
    :vartype repetition: int
    :ivar socket: Physical socket index.
    :vartype socket: int or None
    :ivar ccd: CCD index within the socket.
    :vartype ccd: int or None
    :ivar ccx: CCX index within the CCD.
    :vartype ccx: int or None
    :ivar cores: Comma-separated list of core indices that belong to this CCX
        (max 128 chars), e.g. ``"0,1,2,3"``.
    :vartype cores: str or None
    """

    __table_args__ = {"extend_existing": True}
    __tablename__ = "AMDuProfPCM_machine_cpu_topology"
    id: Mapped[int] = mapped_column(primary_key=True)
    repetition: Mapped[int] = mapped_column(ForeignKey(Repetition.id))
    socket: Mapped[int | None]
    ccd: Mapped[int | None]
    ccx: Mapped[int | None]
    cores: Mapped[str | None] = mapped_column(String(128))


class AMDuProfPCM_further_machine_info(DBBase):
    """
    Additional hardware configuration for one profiling repetition (AMD uProf PCM).

    Captures frequency and multiplexing-interval settings recorded in the
    ``further_machine_info`` section of the raw AMD uProf CSV.

    :ivar id: Auto-incremented primary key.
    :vartype id: int
    :ivar repetition: Foreign key into :class:`~quare.models.Repetition`.
    :vartype repetition: int
    :ivar core_p0_state_freq: Core P0-state (peak) frequency in MHz.
    :vartype core_p0_state_freq: float or None
    :ivar multiplex_interval_for_core: Performance-counter multiplexing
        interval for core events, in milliseconds.
    :vartype multiplex_interval_for_core: float or None
    :ivar multiplex_interval_for_l3: Multiplexing interval for L3 events, ms.
    :vartype multiplex_interval_for_l3: float or None
    :ivar multiplex_interval_for_df: Multiplexing interval for Data Fabric
        events, ms.
    :vartype multiplex_interval_for_df: float or None
    :ivar measured_df_frequency: Measured Data Fabric frequency in MHz.
    :vartype measured_df_frequency: float or None
    :ivar multiplex_interval: General multiplexing interval in milliseconds.
    :vartype multiplex_interval: float or None
    :ivar version: AMD uProf tool version string (max 16 chars).
    :vartype version: str or None
    """

    __table_args__ = {"extend_existing": True}
    __tablename__ = "AMDuProfPCM_further_machine_info"
    id: Mapped[int] = mapped_column(primary_key=True)
    repetition: Mapped[int] = mapped_column(ForeignKey(Repetition.id))
    core_p0_state_freq: Mapped[float | None]
    multiplex_interval_for_core: Mapped[float | None]
    multiplex_interval_for_l3: Mapped[float | None]
    multiplex_interval_for_df: Mapped[float | None]
    measured_df_frequency: Mapped[float | None]
    multiplex_interval: Mapped[float | None]
    version: Mapped[str | None] = mapped_column(String(16))


class AMDuProfPCM_metrics_dict(MetricsDictBase):
    """
    Metric-dictionary table for the AMD uProf PCM profiler.

    Enumerates all metric types produced by AMD uProf PCM (e.g.
    ``"L2 Miss (pti)"``, ``"L2 Access (pti)"``).  Inherits the unique
    constraint on ``(name, unit, processing_unit)`` from
    :class:`~quare.models.MetricsDictBase`.
    """

    __table_args__ = {"extend_existing": True}
    __tablename__ = "AMDuProfPCM_metrics_dict"


class AMDuProfPCM_metrics(MetricsBase):
    """
    Metric-value table for the AMD uProf PCM profiler.

    Each row stores one averaged performance counter value for a single
    (repetition, processing-unit, metric) combination.

    :ivar metric: Foreign key into :class:`AMDuProfPCM_metrics_dict`.
    :vartype metric: int
    """

    __table_args__ = {"extend_existing": True}
    __tablename__ = "AMDuProfPCM_metrics"
    metric: Mapped[int] = mapped_column(ForeignKey(AMDuProfPCM_metrics_dict.id))
