from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from .quare_models import DBBase, ProfilingSession


# machine_info refers to profiling_session
# as machine_info file is generated in each session
class AMDuProfPcm_machine_info(DBBase):
    __tablename__ = "AMDuProfPcm_machine_info"
    id: Mapped[int] = mapped_column(primary_key=True)
    profiling_session: Mapped[int] = mapped_column(ForeignKey(ProfilingSession.id))
    system: Mapped[str] = mapped_column(String(256))
    num_of_sockets: Mapped[int]
    num_of_ccds: Mapped[int]
    num_of_cores: Mapped[int]
    num_of_threads: Mapped[int]
    smt_enabled_in_hw: Mapped[bool]
    smt_enabled_in_os: Mapped[bool]
    num_of_threads_sharing_l3: Mapped[int]


class AMDuProfPcm_machine_cpu_topology(DBBase):
    __tablename__ = "AMDuProfPcm_machine_cpu_topology"
    id: Mapped[int] = mapped_column(primary_key=True)
    profiling_session: Mapped[int] = mapped_column(ForeignKey(ProfilingSession.id))
    socket: Mapped[int]
    ccd: Mapped[int]
    cores: Mapped[str] = mapped_column(String(128))


class AMDuProfPcm_further_machine_info(DBBase):
    __tablename__ = "AMDuProfPcm_further_machine_info"
    id: Mapped[int] = mapped_column(primary_key=True)
    profiling_session: Mapped[int] = mapped_column(ForeignKey(ProfilingSession.id))
    core_p0_state_freq: Mapped[float]
    multiplex_interval_for_core: Mapped[float]
    multiplex_interval_for_l3: Mapped[float]
    multiplex_interval_for_df: Mapped[float]
    version: Mapped[str] = mapped_column(String(16))


class AMDuProfPcm_metrics_dict(DBBase):
    __tablename__ = "AMDuProfPcm_metrics_dict"
    name: Mapped[str] = mapped_column(String(128), primary_key=True)
    desc: Mapped[str | None] = mapped_column(String(1024))


class AMDuProfPcm_core_metrics(DBBase):
    __tablename__ = "AMDuProfPcm_core_metrics"
    id: Mapped[int] = mapped_column(primary_key=True)
    profiling_session: Mapped[int] = mapped_column(ForeignKey(ProfilingSession.id))
    core: Mapped[int]
    metric: Mapped[str] = mapped_column(ForeignKey(AMDuProfPcm_metrics_dict.name))
    value: Mapped[float]


class AMDuProfPcm_l3_metrics(DBBase):
    __tablename__ = "AMDuProfPcm_l3_metrics"
    id: Mapped[int] = mapped_column(primary_key=True)
    profiling_session: Mapped[int] = mapped_column(ForeignKey(ProfilingSession.id))
    ccx: Mapped[int]
    l3_access: Mapped[float]
    l3_miss: Mapped[float]
    l3_miss_percent: Mapped[float]
    ave_l3_miss_latency: Mapped[float]
