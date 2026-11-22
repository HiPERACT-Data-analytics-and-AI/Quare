"""
ORM models for the OpenFOAM logs extension.

The extension stores *run-level* values taken from OpenFOAM log files
(mesh size, number of MPI ranks, number of time steps and solver times) in the
generic metric tables, with the processing unit ``"run"`` and no index.

All tables use ``extend_existing=True`` so that they can be safely re-imported
during dynamic extension discovery.
"""

from __future__ import annotations

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from ...models import MetricsBase, MetricsDictBase


class OpenFOAMlogs_metrics_dict(MetricsDictBase):
    """
    Dictionary of the metrics extracted from OpenFOAM logs.

    Names used by the loader: ``cells``, ``ranks`` and, per solver (for
    example ``simpleFoam``), ``<solver> time steps``,
    ``<solver> first step time``, ``<solver> last step time`` and
    ``<solver> total time`` (times in seconds).
    """

    __table_args__ = {"extend_existing": True}
    __tablename__ = "OpenFOAMlogs_metrics_dict"


class OpenFOAMlogs_metrics(MetricsBase):
    """
    Run-level values extracted from the OpenFOAM logs of one repetition.

    :ivar metric: Foreign key into :class:`OpenFOAMlogs_metrics_dict`.
    :vartype metric: int
    """

    __table_args__ = {"extend_existing": True}
    __tablename__ = "OpenFOAMlogs_metrics"
    metric: Mapped[int] = mapped_column(ForeignKey(OpenFOAMlogs_metrics_dict.id))
