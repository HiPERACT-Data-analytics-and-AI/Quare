"""
ORM models for the LIKWID extension.

Every ``STAT`` row of a LIKWID metric table is stored as four rows of the
generic metric table: the metric name is ``<group> <metric>`` (for example
``L2 data volume [GBytes]``), the processing unit is the statistic over the
hardware threads (``sum``, ``min``, ``max`` or ``avg``).

Authors: Marcin Lawenda, Łukasz Szustak
"""

from __future__ import annotations

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from ...models import MetricsBase, MetricsDictBase


class LIKWID_metrics_dict(MetricsDictBase):
    """Dictionary of the LIKWID metrics (``<group> <metric>``)."""

    __table_args__ = {"extend_existing": True}
    __tablename__ = "LIKWID_metrics_dict"


class LIKWID_metrics(MetricsBase):
    """LIKWID statistics of one repetition.

    :ivar metric: Foreign key into :class:`LIKWID_metrics_dict`.
    :vartype metric: int
    """

    __table_args__ = {"extend_existing": True}
    __tablename__ = "LIKWID_metrics"
    metric: Mapped[int] = mapped_column(ForeignKey(LIKWID_metrics_dict.id))
