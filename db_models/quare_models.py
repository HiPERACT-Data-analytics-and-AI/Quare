from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class DBBase(DeclarativeBase):
    pass


class Machine(DBBase):
    __tablename__ = "Machine"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))

    # sessions: Mapped[list["ProfilingSession"]] = relationship()


class UseCase(DBBase):
    __tablename__ = "Use_case"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(256))

    # sessions: Mapped[list["ProfilingSession"]] = relationship()


class ProfilingSession(DBBase):
    __tablename__ = "Profiling_session"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(256))
    use_case: Mapped[int] = mapped_column(ForeignKey(UseCase.id))
    task_size: Mapped[str] = mapped_column(String(32))
    date: Mapped[datetime | None]
    machine: Mapped[int] = mapped_column(ForeignKey(Machine.id))
