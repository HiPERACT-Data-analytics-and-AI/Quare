"""
Plotter and analyser for the AMD uProf Performance Counter Monitor (PCM) extension.

:class:`AMDuProfPCMAnalyzer` extends
:class:`~quare.extensions.amduprof_data_retriever.AMDuProfDataRetriever` with
six L2 cache ratio analyses (miss ratios and hit ratios, broken down by data
cache misses and hardware prefetcher activity).

Helper
------
:func:`_safe_ratio` performs element-wise division with explicit handling of
``None`` denominators and zero denominators, returning ``None`` instead of
``inf`` or ``nan``.

Module-level attributes
-----------------------
``__extension_data_retriever__``
    :class:`AMDuProfPCMAnalyzer` — the retriever class used by
    :class:`~quare.data_retriever.DataRetrieversManager`.
``__extension_data_plotter__``
    :class:`~quare.plotter.Plotter` — the generic plotter (no PCM-specific
    plot customisation needed beyond the analyses).
``__extension_metrics_table__``
    :class:`~quare.extensions.AMDuProfPCM_ext.models.AMDuProfPCM_metrics`.
``__extension_metrics_dict__``
    :class:`~quare.extensions.AMDuProfPCM_ext.models.AMDuProfPCM_metrics_dict`.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from ...data_retriever import DataRetriever, MetricValue, RepetitionIDs, UniqueMetricKey
from ...models import MetricsBase, MetricsDictBase
from ...plotter import Plotter
from ..amduprof_data_retriever import AMDuProfDataRetriever
from .models import AMDuProfPCM_metrics, AMDuProfPCM_metrics_dict


def _safe_ratio(
    numerator: list[MetricValue], denominator: list[MetricValue]
) -> list[MetricValue]:
    """
    Compute element-wise ``numerator / denominator * 100``, guarding against
    zero and ``None`` denominators.

    :param numerator: Per-task-size numerator values.  ``None`` entries produce
        ``None`` in the output.
    :type numerator: list[MetricValue]
    :param denominator: Per-task-size denominator values.  ``None`` or ``0``
        entries produce ``None`` in the output (no division is performed).
    :type denominator: list[MetricValue]
    :returns: List of percentage ratios with the same length as *numerator* /
        *denominator*.  Each element is either a :class:`float` percentage or
        ``None`` where the ratio is undefined.
    :rtype: list[MetricValue]
    """
    result: list[MetricValue] = []
    for n, d in zip(numerator, denominator):
        if n is None or d is None or d == 0:
            result.append(None)
        else:
            result.append(float(n) / float(d) * 100.0)
    return result


class AMDuProfPCMAnalyzer(AMDuProfDataRetriever):
    """
    Data retriever with L2 cache ratio analyses for AMD uProf PCM data.

    Registers six derived analyses in
    :attr:`~quare.data_retriever.DataRetriever.AVAILABLE_ANALYTICS`
    upon construction.  Each analysis is a ratio (miss or hit percentage)
    computed from pairs of raw PCM performance counters.

    Registered analyses
    -------------------
    ============================== ===========================
    Name                           Formula
    ============================== ===========================
    L2 miss ratio (total)          L2 Miss / L2 Access × 100
    L2DC miss ratio                L2 Miss from DC Miss / L2 Access from DC Miss × 100
    L2 HWPF miss ratio             L2 Miss from HWPF / L2 Access from HWPF × 100
    L2 hit ratio (total)           L2 Hit / L2 Access × 100
    L2DC hit ratio                 L2 Hit from DC Miss / L2 Access from DC Miss × 100
    L2 HWPF hit ratio              L2 Hit from HWPF / L2 Access from HWPF × 100
    ============================== ===========================
    """

    def __init__(
        self,
        db_session: Session,
        metrics_table: type[MetricsBase],
        metrics_dict_table: type[MetricsDictBase],
    ) -> None:
        """
        Initialise the analyser and register all L2 cache ratio analyses.

        :param db_session: Active SQLAlchemy session.
        :type db_session: sqlalchemy.orm.Session
        :param metrics_table: Concrete :class:`~quare.models.MetricsBase`
            subclass for this extension.
        :type metrics_table: type[quare.models.MetricsBase]
        :param metrics_dict_table: Concrete
            :class:`~quare.models.MetricsDictBase` subclass for this extension.
        :type metrics_dict_table: type[quare.models.MetricsDictBase]
        """
        super().__init__(db_session, metrics_table, metrics_dict_table)
        # fmt: off
        self.AVAILABLE_ANALYTICS |= {
            UniqueMetricKey(
                "L2 miss ratio (total)", "%", "core"
            ): self._calc_L2_miss_ratio_total,
            UniqueMetricKey(
                "L2DC miss ratio", "%", "core"
            ): self._calc_L2DC_miss_ratio,
            UniqueMetricKey(
                "L2 HWPF miss ratio", "%", "core"
            ): self._calc_L2_HWPF_miss_ratio,
            UniqueMetricKey(
                "L2 hit ratio (total)", "%", "core"
            ): self._calc_L2_hit_ratio_total,
            UniqueMetricKey(
                "L2DC hit ratio", "%", "core"
            ): self._calc_L2DC_hit_ratio,
            UniqueMetricKey(
                "L2 HWPF hit ratio", "%", "core"
            ): self._calc_L2_HWPF_hit_ratio,
        }
        # fmt: on

    def _calc_L2_miss_ratio_total(
        self, repetition_ids: RepetitionIDs
    ) -> list[MetricValue]:
        """
        Compute the total L2 cache miss ratio per task size.

        Formula: ``L2 Miss (pti) / L2 Access (pti) × 100``

        :param repetition_ids: Repetition scope from
            :meth:`~quare.data_retriever.DataRetriever.get_repetitions`.
        :type repetition_ids: RepetitionIDs
        :returns: Per-task-size list of L2 total miss ratios in percent, with
            ``None`` where the denominator is zero or data is absent.
        :rtype: list[MetricValue]
        """
        l2_miss = UniqueMetricKey("L2 Miss (pti)", "", "core")
        l2_access = UniqueMetricKey("L2 Access (pti)", "", "core")
        metrics = self.get_metrics(repetition_ids, [l2_miss, l2_access])
        return _safe_ratio(metrics[l2_miss], metrics[l2_access])

    def _calc_L2DC_miss_ratio(self, repetition_ids: RepetitionIDs) -> list[MetricValue]:
        """
        Compute the L2 data-cache (DC) miss ratio per task size.

        Formula: ``L2 Miss from DC Miss (pti) / L2 Access from DC Miss (pti) × 100``

        :param repetition_ids: Repetition scope.
        :type repetition_ids: RepetitionIDs
        :returns: Per-task-size list of L2 DC miss ratios in percent.
        :rtype: list[MetricValue]
        """
        l2_miss = UniqueMetricKey("L2 Miss from DC Miss (pti)", "", "core")
        l2_access = UniqueMetricKey("L2 Access from DC Miss (pti)", "", "core")
        metrics = self.get_metrics(repetition_ids, [l2_miss, l2_access])
        return _safe_ratio(metrics[l2_miss], metrics[l2_access])

    def _calc_L2_HWPF_miss_ratio(
        self, repetition_ids: RepetitionIDs
    ) -> list[MetricValue]:
        """
        Compute the L2 hardware-prefetcher (HWPF) miss ratio per task size.

        Formula: ``L2 Miss from HWPF (pti) / L2 Access from HWPF (pti) × 100``

        :param repetition_ids: Repetition scope.
        :type repetition_ids: RepetitionIDs
        :returns: Per-task-size list of L2 HWPF miss ratios in percent.
        :rtype: list[MetricValue]
        """
        l2_miss = UniqueMetricKey("L2 Miss from HWPF (pti)", "", "core")
        l2_access = UniqueMetricKey("L2 Access from HWPF (pti)", "", "core")
        metrics = self.get_metrics(repetition_ids, [l2_miss, l2_access])
        return _safe_ratio(metrics[l2_miss], metrics[l2_access])

    def _calc_L2_hit_ratio_total(
        self, repetition_ids: RepetitionIDs
    ) -> list[MetricValue]:
        """
        Compute the total L2 cache hit ratio per task size.

        Formula: ``L2 Hit (pti) / L2 Access (pti) × 100``

        :param repetition_ids: Repetition scope.
        :type repetition_ids: RepetitionIDs
        :returns: Per-task-size list of L2 total hit ratios in percent.
        :rtype: list[MetricValue]
        """
        l2_hit = UniqueMetricKey("L2 Hit (pti)", "", "core")
        l2_access = UniqueMetricKey("L2 Access (pti)", "", "core")
        metrics = self.get_metrics(repetition_ids, [l2_hit, l2_access])
        return _safe_ratio(metrics[l2_hit], metrics[l2_access])

    def _calc_L2DC_hit_ratio(self, repetition_ids: RepetitionIDs) -> list[MetricValue]:
        """
        Compute the L2 data-cache (DC) hit ratio per task size.

        Formula: ``L2 Hit from DC Miss (pti) / L2 Access from DC Miss (pti) × 100``

        :param repetition_ids: Repetition scope.
        :type repetition_ids: RepetitionIDs
        :returns: Per-task-size list of L2 DC hit ratios in percent.
        :rtype: list[MetricValue]
        """
        l2_hit = UniqueMetricKey("L2 Hit from DC Miss (pti)", "", "core")
        l2_access = UniqueMetricKey("L2 Access from DC Miss (pti)", "", "core")
        metrics = self.get_metrics(repetition_ids, [l2_hit, l2_access])
        return _safe_ratio(metrics[l2_hit], metrics[l2_access])

    def _calc_L2_HWPF_hit_ratio(
        self, repetition_ids: RepetitionIDs
    ) -> list[MetricValue]:
        """
        Compute the L2 hardware-prefetcher (HWPF) hit ratio per task size.

        Formula: ``L2 Hit from HWPF (pti) / L2 Access from HWPF (pti) × 100``

        :param repetition_ids: Repetition scope.
        :type repetition_ids: RepetitionIDs
        :returns: Per-task-size list of L2 HWPF hit ratios in percent.
        :rtype: list[MetricValue]
        """
        l2_hit = UniqueMetricKey("L2 Hit from HWPF (pti)", "", "core")
        l2_access = UniqueMetricKey("L2 Access from HWPF (pti)", "", "core")
        metrics = self.get_metrics(repetition_ids, [l2_hit, l2_access])
        return _safe_ratio(metrics[l2_hit], metrics[l2_access])


__extension_data_retriever__: type[DataRetriever] = AMDuProfPCMAnalyzer
__extension_data_plotter__: type[Plotter] = Plotter
__extension_metrics_table__ = AMDuProfPCM_metrics
__extension_metrics_dict__ = AMDuProfPCM_metrics_dict
