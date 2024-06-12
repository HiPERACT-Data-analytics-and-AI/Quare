from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class DBBase(DeclarativeBase):
    pass


class Machine(DBBase):
    __tablename__ = "Machine"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True)
    desc: Mapped[str | None] = mapped_column(String(1024))

    # sessions: Mapped[list["ProfilingSession"]] = relationship()


class UseCase(DBBase):
    __tablename__ = "Use_case"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(256), unique=True)
    desc: Mapped[str | None] = mapped_column(String(1024))

    # sessions: Mapped[list["ProfilingSession"]] = relationship()


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
    use_case: Mapped[int] = mapped_column(ForeignKey(UseCase.id))
    task_size: Mapped[int] = mapped_column(ForeignKey(TaskSizesDict.id))
    date: Mapped[datetime | None]
    machine: Mapped[int] = mapped_column(ForeignKey(Machine.id))
    exec_time_s: Mapped[float | None]
