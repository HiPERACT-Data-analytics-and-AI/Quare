from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class DBBase(DeclarativeBase):
    pass


class Machine(DBBase):
    __tablename__ = "Machine"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))


class ProfilingSession(DBBase):
    __tablename__ = "Profiling_session"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str | None] = mapped_column(String(128))
    use_case: Mapped[str] = mapped_column(String(128))
    use_case_size: Mapped[str] = mapped_column(String(32))
    date: Mapped[datetime | None]


class AMDuProfPcm_machine_info(DBBase):
    __tablename__ = "AMDuProfPcm_machine_info"
    id: Mapped[int] = mapped_column(primary_key=True)
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
    socket: Mapped[int]
    ccd: Mapped[int]
    cores: Mapped[str] = mapped_column(String(128))


class AMDuProfPcm_further_machine_info(DBBase):
    __tablename__ = "AMDuProfPcm_further_machine_info"
    id: Mapped[int] = mapped_column(primary_key=True)
    core_p0_state_freq: Mapped[float]
    multiplex_interval_for_core: Mapped[float]
    multiplex_interval_for_l3: Mapped[float]
    multiplex_interval_for_df: Mapped[float]
    version: Mapped[str] = mapped_column(String(16))


class AMDuProfPcm_core_metrics(DBBase):
    __tablename__ = "AMDuProfPcm_core_metrics"
    id: Mapped[int] = mapped_column(primary_key=True)
    core: Mapped[int]
    metric: Mapped[str] = mapped_column(String(64))
    value: Mapped[float]


class AMDuProfPcm_l3_metrics(DBBase):
    __tablename__ = "AMDuProfPcm_l3_metrics"
    id: Mapped[int] = mapped_column(primary_key=True)
    ccx: Mapped[int]
    l3_access: Mapped[float]
    l3_miss: Mapped[float]
    l3_miss_percent: Mapped[float]
    ave_l3_miss_latency: Mapped[float]


class MPIuProf_environment(DBBase):
    __tablename__ = "MPIuProf_environment"
    id: Mapped[int] = mapped_column(primary_key=True)
    total_ranks: Mapped[int]
    lib_version: Mapped[str] = mapped_column(String(256))
    std_version: Mapped[str] = mapped_column(String(16))


class MPIuProf_functions_summary(DBBase):
    __tablename__ = "MPIuProf_functions_summary"
    id: Mapped[int] = mapped_column(primary_key=True)
    function: Mapped[str] = mapped_column(String(32))
    min_time: Mapped[float]
    max_time: Mapped[float]
    average_time: Mapped[float]
    mpi_time_percent: Mapped[float]
    volume: Mapped[int]
    calls: Mapped[int]
    total_time: Mapped[float]


class MPIuProf_rank_summary(DBBase):
    __tablename__ = "MPIuProf_rank_summary"
    id: Mapped[int] = mapped_column(primary_key=True)
    rank: Mapped[int]
    pid: Mapped[int]
    mpi_time: Mapped[float]
    mpi_time_percent: Mapped[float]
    wait_time: Mapped[float]
    call_count: Mapped[int]
    volume: Mapped[int]
