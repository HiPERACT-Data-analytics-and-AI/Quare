from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class DBBase(DeclarativeBase):
    """
    _summary_

    :param DeclarativeBase: _description_
    """

    pass


# "Profiling" prefix in the name added due to "Session"
# class from SQLAlchemy (solution easier than aliases):
class ProfilingSession(DBBase):
    """_summary__"""

    __tablename__ = "Profiling_session"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(256), unique=True)
    """column description"""
    desc: Mapped[str | None] = mapped_column(String(4096))
    """column description"""


class Machine(DBBase):
    """_summary__"""

    __tablename__ = "Machine"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(256), unique=True)
    """column description"""
    desc: Mapped[str | None] = mapped_column(String(1024))
    """column description"""
    num_of_cores: Mapped[int | None]
    """column description"""
    num_of_threads: Mapped[int | None]
    """column description"""


class UseCase(DBBase):
    """_summary__"""

    __tablename__ = "Use_case"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(256), unique=True)
    """column description"""
    desc: Mapped[str | None] = mapped_column(String(1024))
    """column description"""


class TaskSizesDict(DBBase):
    """_summary__"""

    __tablename__ = "Task_sizes_dict"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(32), unique=True)
    """column description"""
    size: Mapped[int | None]
    """column description"""


class Repetition(DBBase):
    """_summary__"""

    __tablename__ = "Repetition"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    """column description"""
    # desc: Mapped[str | None] = mapped_column(String(1024))
    profiling_session: Mapped[int] = mapped_column(ForeignKey(ProfilingSession.id))
    """column description"""
    machine: Mapped[int] = mapped_column(ForeignKey(Machine.id))
    """column description"""
    use_case: Mapped[int] = mapped_column(ForeignKey(UseCase.id))
    """column description"""
    task_size: Mapped[int] = mapped_column(ForeignKey(TaskSizesDict.id))
    """column description"""
    date: Mapped[datetime | None]
    """column description"""
    exec_time_s: Mapped[float | None]
    """column description"""
    # Length set according to some default linux limits:
    file_dir: Mapped[str] = mapped_column(String(4096 - 255))
    """column description"""
    data_consistent: Mapped[bool] = mapped_column(default=False)
    """column description"""


class MetricsDictBase(DBBase):
    """_summary__"""

    __abstract__ = True
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), name="name")
    """column description"""
    unit: Mapped[str] = mapped_column(String(16), name="unit")
    """column description"""
    processing_unit: Mapped[str] = mapped_column(String(16), name="processing_unit")
    """column description"""
    desc: Mapped[str | None] = mapped_column(String(1024))
    """column description"""

    __table_args__ = (UniqueConstraint(name, unit, processing_unit),)


class MetricsBase(DBBase):
    """_summary__"""

    __abstract__ = True
    id: Mapped[int] = mapped_column(primary_key=True, sort_order=-10)
    repetition: Mapped[int] = mapped_column(ForeignKey(Repetition.id), sort_order=-9)
    """column description"""
    processing_unit_idx: Mapped[int | None] = mapped_column(sort_order=-8)
    """column description"""
    metric: None = None
    """column description"""
    value: Mapped[float] = mapped_column(sort_order=10)
    """column description"""

    @classmethod
    def __raise_error(cls, name: str):
        raise NotImplementedError(
            f"{name} class must have a 'metric' attribute "
            + "as a foreign key to a MetricsDict model"
        )

    def __init_subclass__(cls, **kw: Any) -> None:
        """
        _summary_
        """
        if not hasattr(cls, "metric"):
            cls.__raise_error(cls.__name__)
        elif not isinstance(cls.metric, Mapped):
            cls.__raise_error(cls.__name__)
        return super().__init_subclass__(**kw)
