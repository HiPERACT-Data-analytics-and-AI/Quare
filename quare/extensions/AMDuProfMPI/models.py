from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from ...models import DBBase, MetricsBase, MetricsDictBase, Repetition


class AMDuProfMPI_environment(DBBase):
    """_summary_"""

    __tablename__ = "AMDuProfMPI_environment"
    id: Mapped[int] = mapped_column(primary_key=True)
    repetition: Mapped[int] = mapped_column(ForeignKey(Repetition.id))
    """column description"""
    total_ranks: Mapped[int | None]
    """column description"""
    lib_version: Mapped[str | None] = mapped_column(String(256))
    """column description"""
    std_version: Mapped[str | None] = mapped_column(String(16))
    """column description"""


class AMDuProfMPI_metrics_dict(MetricsDictBase):
    __tablename__ = "AMDuProfMPI_metrics_dict"


class AMDuProfMPI_metrics(MetricsBase):
    __tablename__ = "AMDuProfMPI_metrics"
    metric: Mapped[int] = mapped_column(ForeignKey(AMDuProfMPI_metrics_dict.id))
