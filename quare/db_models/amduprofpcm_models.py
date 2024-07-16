from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from .quare_models import DBBase, MetricsBase, MetricsDictBase, Repetition


# machine_info refers to a repetition
# as machine_info file is generated repetition-wise
class AMDuProfPCM_machine_info(DBBase):
    """_summary_"""

    __tablename__ = "AMDuProfPCM_machine_info"
    id: Mapped[int] = mapped_column(primary_key=True)
    repetition: Mapped[int] = mapped_column(ForeignKey(Repetition.id))
    """column description"""
    system: Mapped[str] = mapped_column(String(256))
    """column description"""
    num_of_sockets: Mapped[int | None]
    """column description"""
    num_of_ccds: Mapped[int | None]
    """column description"""
    num_of_ccxs: Mapped[int | None]
    """column description"""
    num_of_cores: Mapped[int | None]
    """column description"""
    num_of_threads: Mapped[int | None]
    """column description"""
    smt_enabled_in_hw: Mapped[bool]
    """column description"""
    smt_enabled_in_os: Mapped[bool]
    """column description"""
    num_of_threads_sharing_l3: Mapped[int | None]
    """column description"""


class AMDuProfPCM_machine_cpu_topology(DBBase):
    """_summary_"""

    __tablename__ = "AMDuProfPCM_machine_cpu_topology"
    id: Mapped[int] = mapped_column(primary_key=True)
    repetition: Mapped[int] = mapped_column(ForeignKey(Repetition.id))
    """column description"""
    socket: Mapped[int | None]
    """column description"""
    ccd: Mapped[int | None]
    """column description"""
    ccx: Mapped[int | None]
    """column description"""
    cores: Mapped[str | None] = mapped_column(String(128))
    """column description"""


class AMDuProfPCM_further_machine_info(DBBase):
    """_summary_"""

    __tablename__ = "AMDuProfPCM_further_machine_info"
    id: Mapped[int] = mapped_column(primary_key=True)
    repetition: Mapped[int] = mapped_column(ForeignKey(Repetition.id))
    """column description"""
    core_p0_state_freq: Mapped[float | None]
    """column description"""
    multiplex_interval_for_core: Mapped[float | None]
    """column description"""
    multiplex_interval_for_l3: Mapped[float | None]
    """column description"""
    multiplex_interval_for_df: Mapped[float | None]
    """column description"""
    measured_df_frequency: Mapped[float | None]
    """column description"""
    multiplex_interval: Mapped[float | None]
    """column description"""
    version: Mapped[str | None] = mapped_column(String(16))
    """column description"""


class AMDuProfPCM_metrics_dict(MetricsDictBase):
    __tablename__ = "AMDuProfPCM_metrics_dict"


class AMDuProfPCM_metrics(MetricsBase):
    __tablename__ = "AMDuProfPCM_metrics"
    metric: Mapped[int] = mapped_column(ForeignKey(AMDuProfPCM_metrics_dict.id))
