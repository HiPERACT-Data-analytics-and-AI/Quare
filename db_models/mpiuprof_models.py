from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from .quare_models import DBBase, ProfilingSession


class MPIuProf_environment(DBBase):
    __tablename__ = "MPIuProf_environment"
    id: Mapped[int] = mapped_column(primary_key=True)
    profiling_session: Mapped[int] = mapped_column(ForeignKey(ProfilingSession.name))
    total_ranks: Mapped[int]
    lib_version: Mapped[str] = mapped_column(String(256))
    std_version: Mapped[str] = mapped_column(String(16))


class MPIuProf_functions_dict(DBBase):
    __tablename__ = "MPIuProf_functions_dict"
    name: Mapped[str] = mapped_column(String(128), primary_key=True)
    desc: Mapped[str | None] = mapped_column(String(1024))


class MPIuProf_functions_summary(DBBase):
    __tablename__ = "MPIuProf_functions_summary"
    id: Mapped[int] = mapped_column(primary_key=True)
    profiling_session: Mapped[int] = mapped_column(ForeignKey(ProfilingSession.name))
    function: Mapped[str] = mapped_column(ForeignKey(MPIuProf_functions_dict.name))
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
    profiling_session: Mapped[int] = mapped_column(ForeignKey(ProfilingSession.name))
    rank: Mapped[int]
    pid: Mapped[int]
    mpi_time: Mapped[float]
    mpi_time_percent: Mapped[float]
    wait_time: Mapped[float]
    call_count: Mapped[int]
    volume: Mapped[int]
