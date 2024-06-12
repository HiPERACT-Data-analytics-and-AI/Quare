from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from .quare_models import DBBase, Repetition


class AMDuProfMPI_environment(DBBase):
    __tablename__ = "AMDuProfMPI_environment"
    id: Mapped[int] = mapped_column(primary_key=True)
    repetition: Mapped[int] = mapped_column(ForeignKey(Repetition.id))
    total_ranks: Mapped[int | None]
    lib_version: Mapped[str | None] = mapped_column(String(256))
    std_version: Mapped[str | None] = mapped_column(String(16))


class AMDuProfMPI_functions_dict(DBBase):
    __tablename__ = "AMDuProfMPI_functions_dict"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True)
    desc: Mapped[str | None] = mapped_column(String(1024))


class AMDuProfMPI_functions_summary(DBBase):
    __tablename__ = "AMDuProfMPI_functions_summary"
    id: Mapped[int] = mapped_column(primary_key=True)
    repetition: Mapped[int] = mapped_column(ForeignKey(Repetition.id))
    function: Mapped[int] = mapped_column(ForeignKey(AMDuProfMPI_functions_dict.id))
    min_time: Mapped[float | None]
    max_time: Mapped[float | None]
    average_time: Mapped[float | None]
    mpi_time_percent: Mapped[float | None]
    volume: Mapped[int | None]
    calls: Mapped[int | None]
    total_time: Mapped[float | None]


class AMDuProfMPI_rank_summary(DBBase):
    __tablename__ = "AMDuProfMPI_rank_summary"
    id: Mapped[int] = mapped_column(primary_key=True)
    repetition: Mapped[int] = mapped_column(ForeignKey(Repetition.id))
    rank: Mapped[int | None]
    pid: Mapped[int | None]
    mpi_time: Mapped[float | None]
    mpi_time_percent: Mapped[float | None]
    wait_time: Mapped[float | None]
    call_count: Mapped[int | None]
    volume: Mapped[int | None]
