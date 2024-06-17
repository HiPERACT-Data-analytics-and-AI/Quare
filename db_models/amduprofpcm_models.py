from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .quare_models import DBBase, Repetition


# machine_info refers to repetition
# as machine_info file is generated repetition-wise
class AMDuProfPCM_machine_info(DBBase):
    __tablename__ = "AMDuProfPCM_machine_info"
    id: Mapped[int] = mapped_column(primary_key=True)
    repetition: Mapped[int] = mapped_column(ForeignKey(Repetition.id))
    system: Mapped[str] = mapped_column(String(256))
    num_of_sockets: Mapped[int | None]
    num_of_ccds: Mapped[int | None]
    num_of_ccxs: Mapped[int | None]
    num_of_cores: Mapped[int | None]
    num_of_threads: Mapped[int | None]
    smt_enabled_in_hw: Mapped[bool]
    smt_enabled_in_os: Mapped[bool]
    num_of_threads_sharing_l3: Mapped[int | None]


class AMDuProfPCM_machine_cpu_topology(DBBase):
    __tablename__ = "AMDuProfPCM_machine_cpu_topology"
    id: Mapped[int] = mapped_column(primary_key=True)
    repetition: Mapped[int] = mapped_column(ForeignKey(Repetition.id))
    socket: Mapped[int | None]
    ccd: Mapped[int | None]
    ccx: Mapped[int | None]
    cores: Mapped[str | None] = mapped_column(String(128))


class AMDuProfPCM_further_machine_info(DBBase):
    __tablename__ = "AMDuProfPCM_further_machine_info"
    id: Mapped[int] = mapped_column(primary_key=True)
    repetition: Mapped[int] = mapped_column(ForeignKey(Repetition.id))
    core_p0_state_freq: Mapped[float | None]
    multiplex_interval_for_core: Mapped[float | None]
    multiplex_interval_for_l3: Mapped[float | None]
    multiplex_interval_for_df: Mapped[float | None]
    measured_df_frequency: Mapped[float | None]
    multiplex_interval: Mapped[float | None]
    version: Mapped[str | None] = mapped_column(String(16))


class AMDuProfPCM_metrics_dict(DBBase):
    __tablename__ = "AMDuProfPCM_metrics_dict"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    processing_unit: Mapped[str] = mapped_column(String(16))
    desc: Mapped[str | None] = mapped_column(String(1024))

    __table_args__ = (
        UniqueConstraint(name, processing_unit)
    )


class AMDuProfPCM_metrics(DBBase):
    __tablename__ = "AMDuProfPCM_metrics"
    id: Mapped[int] = mapped_column(primary_key=True)
    repetition: Mapped[int] = mapped_column(ForeignKey(Repetition.id))
    unit_idx: Mapped[int]
    metric: Mapped[int] = mapped_column(ForeignKey(AMDuProfPCM_metrics_dict.id))
    value: Mapped[float]
