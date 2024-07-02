from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from .quare_models import DBBase, MetricsBase, MetricsDictBase, Repetition


class AMDuProfMPI_environment(DBBase):
    __tablename__ = "AMDuProfMPI_environment"
    id: Mapped[int] = mapped_column(primary_key=True)
    repetition: Mapped[int] = mapped_column(ForeignKey(Repetition.id))
    total_ranks: Mapped[int | None]
    lib_version: Mapped[str | None] = mapped_column(String(256))
    std_version: Mapped[str | None] = mapped_column(String(16))


class AMDuProfMPI_metrics_dict(MetricsDictBase):
    __tablename__ = "AMDuProfMPI_metrics_dict"


class AMDuProfMPI_metrics(MetricsBase):
    __tablename__ = "AMDuProfMPI_metrics"
    metric: Mapped[int] = mapped_column(ForeignKey(AMDuProfMPI_metrics_dict.id))
