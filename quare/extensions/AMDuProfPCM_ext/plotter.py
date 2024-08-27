from numpy import asarray
from sqlalchemy.orm import Session

from quare.models import MetricsBase, MetricsDictBase

from ...data_retriever import DataRetriever, MetricValue, RepetitionIDs, UniqueMetricKey
from ...extensions_abcs import ExtensionDataPlotter
from ...plotter import Plotter
from ..amduprof_data_retriever import AMDuProfDataRetriever
from .models import AMDuProfPCM_metrics, AMDuProfPCM_metrics_dict


class AMDuProfPCMAnalyzer(AMDuProfDataRetriever):
    def __init__(
        self,
        db_session: Session,
        metrics_table: type[MetricsBase],
        metrics_dict_table: type[MetricsDictBase],
    ) -> None:
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
        l2_miss = UniqueMetricKey("L2 Miss (pti)", "", "core")
        l2_access = UniqueMetricKey("L2 Access (pti)", "", "core")
        metrics = self.get_metrics(repetition_ids, [l2_miss, l2_access])

        result = asarray(metrics[l2_miss]) / asarray(metrics[l2_access]) * 100.0
        return result.tolist()

    def _calc_L2DC_miss_ratio(self, repetition_ids: RepetitionIDs) -> list[MetricValue]:
        l2_miss = UniqueMetricKey("L2 Miss from DC Miss (pti)", "", "core")
        l2_access = UniqueMetricKey("L2 Access from DC Miss (pti)", "", "core")
        metrics = self.get_metrics(repetition_ids, [l2_miss, l2_access])

        result = asarray(metrics[l2_miss]) / asarray(metrics[l2_access]) * 100.0
        return result.tolist()

    def _calc_L2_HWPF_miss_ratio(
        self, repetition_ids: RepetitionIDs
    ) -> list[MetricValue]:
        l2_miss = UniqueMetricKey("L2 Miss from HWPF (pti)", "", "core")
        l2_access = UniqueMetricKey("L2 Access from HWPF (pti)", "", "core")
        metrics = self.get_metrics(repetition_ids, [l2_miss, l2_access])

        result = asarray(metrics[l2_miss]) / asarray(metrics[l2_access]) * 100.0
        return result.tolist()

    def _calc_L2_hit_ratio_total(
        self, repetition_ids: RepetitionIDs
    ) -> list[MetricValue]:
        l2_hit = UniqueMetricKey("L2 Hit (pti)", "", "core")
        l2_access = UniqueMetricKey("L2 Access (pti)", "", "core")
        metrics = self.get_metrics(repetition_ids, [l2_hit, l2_access])

        result = asarray(metrics[l2_hit]) / asarray(metrics[l2_access]) * 100.0
        return result.tolist()

    def _calc_L2DC_hit_ratio(self, repetition_ids: RepetitionIDs) -> list[MetricValue]:
        l2_hit = UniqueMetricKey("L2 Hit from DC Miss (pti)", "", "core")
        l2_access = UniqueMetricKey("L2 Access from DC Miss (pti)", "", "core")
        metrics = self.get_metrics(repetition_ids, [l2_hit, l2_access])

        result = asarray(metrics[l2_hit]) / asarray(metrics[l2_access]) * 100.0
        return result.tolist()

    def _calc_L2_HWPF_hit_ratio(
        self, repetition_ids: RepetitionIDs
    ) -> list[MetricValue]:
        l2_hit = UniqueMetricKey("L2 Hit from HWPF (pti)", "", "core")
        l2_access = UniqueMetricKey("L2 Access from HWPF (pti)", "", "core")
        metrics = self.get_metrics(repetition_ids, [l2_hit, l2_access])

        result = asarray(metrics[l2_hit]) / asarray(metrics[l2_access]) * 100.0
        return result.tolist()


__extension_data_retriever__: type[DataRetriever] = AMDuProfPCMAnalyzer
__extension_metrics_table__ = AMDuProfPCM_metrics
__extension_metrics_dict__ = AMDuProfPCM_metrics_dict


class ExtensionDataPlotterImpl(ExtensionDataPlotter):
    @staticmethod
    def plot() -> None:
        Plotter("AMDuProfPCM").make_all()
