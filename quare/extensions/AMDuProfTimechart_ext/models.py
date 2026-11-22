"""
ORM models for the AMD uProf Timechart (power) extension.

Each sample of the node power trace is one row of the generic metric table:
the metric name is ``Node <n> power`` (unit ``W``), the processing unit is
``sample`` and ``processing_unit_idx`` is the zero-based sample number
(100 ms apart for the default uProf sampling interval).

Authors: Marcin Lawenda, Łukasz Szustak
"""

from __future__ import annotations

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from ...models import MetricsBase, MetricsDictBase


class AMDuProfTimechart_metrics_dict(MetricsDictBase):
    """Dictionary of the power metrics (``Node <n> power``)."""

    __table_args__ = {"extend_existing": True}
    __tablename__ = "AMDuProfTimechart_metrics_dict"


class AMDuProfTimechart_metrics(MetricsBase):
    """Power samples of one repetition.

    :ivar metric: Foreign key into :class:`AMDuProfTimechart_metrics_dict`.
    :vartype metric: int
    """

    __table_args__ = {"extend_existing": True}
    __tablename__ = "AMDuProfTimechart_metrics"
    metric: Mapped[int] = mapped_column(ForeignKey(AMDuProfTimechart_metrics_dict.id))
