from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class DBBase(DeclarativeBase):
    pass


# "Profiling" prefix in the name added due to "Session"
# class from SQLAlchemy (solution easier than aliases):
class ProfilingSession(DBBase):
    __tablename__ = "Profiling_session"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(256), unique=True)
    desc: Mapped[str | None] = mapped_column(String(4096))


class Machine(DBBase):
    __tablename__ = "Machine"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(256), unique=True)
    desc: Mapped[str | None] = mapped_column(String(1024))


class UseCase(DBBase):
    __tablename__ = "Use_case"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(256), unique=True)
    desc: Mapped[str | None] = mapped_column(String(1024))


class TaskSizesDict(DBBase):
    __tablename__ = "Task_sizes_dict"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(32), unique=True)
    size: Mapped[int | None]


class Repetition(DBBase):
    __tablename__ = "Repetition"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    # desc: Mapped[str | None] = mapped_column(String(1024))
    profiling_session: Mapped[int] = mapped_column(ForeignKey(ProfilingSession.id))
    machine: Mapped[int] = mapped_column(ForeignKey(Machine.id))
    use_case: Mapped[int] = mapped_column(ForeignKey(UseCase.id))
    task_size: Mapped[int] = mapped_column(ForeignKey(TaskSizesDict.id))
    date: Mapped[datetime | None]
    exec_time_s: Mapped[float | None]
    # Length set according to some default linux limits:
    file_dir: Mapped[str] = mapped_column(String(4096 - 255))
