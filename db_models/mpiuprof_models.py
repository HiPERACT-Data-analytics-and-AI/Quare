from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from .quare_models import DBBase, ProfilingSession


class MPIuProf_environment(DBBase):
    __tablename__ = "MPIuProf_environment"
    id: Mapped[int] = mapped_column(primary_key=True)
    profiling_session: Mapped[int] = mapped_column(ForeignKey(ProfilingSession.id))
    total_ranks: Mapped[int | None]
    lib_version: Mapped[str | None] = mapped_column(String(256))
    std_version: Mapped[str | None] = mapped_column(String(16))


class MPIuProf_functions_dict(DBBase):
    __tablename__ = "MPIuProf_functions_dict"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True)
    desc: Mapped[str | None] = mapped_column(String(1024))


class MPIuProf_functions_summary(DBBase):
    __tablename__ = "MPIuProf_functions_summary"
    id: Mapped[int] = mapped_column(primary_key=True)
    profiling_session: Mapped[int] = mapped_column(ForeignKey(ProfilingSession.id))
    function: Mapped[int] = mapped_column(ForeignKey(MPIuProf_functions_dict.id))
    min_time: Mapped[float | None]
    max_time: Mapped[float | None]
    average_time: Mapped[float | None]
    mpi_time_percent: Mapped[float | None]
    volume: Mapped[int | None]
    calls: Mapped[int | None]
    total_time: Mapped[float | None]


class MPIuProf_rank_summary(DBBase):
    __tablename__ = "MPIuProf_rank_summary"
    id: Mapped[int] = mapped_column(primary_key=True)
    profiling_session: Mapped[int] = mapped_column(ForeignKey(ProfilingSession.id))
    rank: Mapped[int | None]
    pid: Mapped[int | None]
    mpi_time: Mapped[float | None]
    mpi_time_percent: Mapped[float | None]
    wait_time: Mapped[float | None]
    call_count: Mapped[int | None]
    volume: Mapped[int | None]
