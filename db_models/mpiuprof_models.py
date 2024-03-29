from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from .quare_models import DBBase


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
