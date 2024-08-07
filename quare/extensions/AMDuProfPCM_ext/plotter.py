from numpy import asarray
from sqlalchemy.orm import Session

from ...data_retriever import MetricsData, UniqueMetricKey
from ...plotter import Plotter
from ..amduprof_data_retriever import AMDuProfDataRetriever
from .models import AMDuProfPCM_metrics, AMDuProfPCM_metrics_dict


class AMDuProfPCMAnalyzer(AMDuProfDataRetriever):
    def _calc_L2_miss_ratio_total(
        self, repetition_ids: dict[str, list[int]]
    ) -> MetricsData:
        metric_names_to_get: list[str] = [
            "L2 Miss (pti)",
            "L2 Access (pti)",
        ]
        metrics = self.get_data(repetition_ids, metric_names_to_get, analytics=False)
        l2_miss = metrics[UniqueMetricKey("L2 Miss (pti)", "", "core")]
        l2_access = metrics[UniqueMetricKey("L2 Access (pti)", "", "core")]

        result = asarray(l2_miss) / asarray(l2_access) * 100.0
        return {UniqueMetricKey("L2 miss ratio (total)", "%", "core"): result.tolist()}

    def _calc_L2DC_miss_ratio(
        self, repetition_ids: dict[str, list[int]]
    ) -> MetricsData:
        metric_names_to_get: list[str] = [
            "L2 Miss from DC Miss (pti)",
            "L2 Access from DC Miss (pti)",
        ]
        metrics = self.get_data(repetition_ids, metric_names_to_get, analytics=False)
        l2_miss = metrics[UniqueMetricKey("L2 Miss from DC Miss (pti)", "", "core")]
        l2_access = metrics[UniqueMetricKey("L2 Access from DC Miss (pti)", "", "core")]

        result = asarray(l2_miss) / asarray(l2_access) * 100.0
        return {UniqueMetricKey("L2DC miss ratio", "%", "core"): result.tolist()}

    def _calc_L2_HWPF_miss_ratio(
        self, repetition_ids: dict[str, list[int]]
    ) -> MetricsData:
        metric_names_to_get: list[str] = [
            "L2 Miss from HWPF (pti)",
            "L2 Access from HWPF (pti)",
        ]
        metrics = self.get_data(repetition_ids, metric_names_to_get, analytics=False)
        l2_miss = metrics[UniqueMetricKey("L2 Miss from HWPF (pti)", "", "core")]
        l2_access = metrics[UniqueMetricKey("L2 Access from HWPF (pti)", "", "core")]

        result = asarray(l2_miss) / asarray(l2_access) * 100.0
        return {UniqueMetricKey("L2 HWPF miss ratio", "%", "core"): result.tolist()}

    def _calc_L2_hit_ratio_total(
        self, repetition_ids: dict[str, list[int]]
    ) -> MetricsData:
        metric_names_to_get: list[str] = [
            "L2 Hit (pti)",
            "L2 Access (pti)",
        ]
        metrics = self.get_data(repetition_ids, metric_names_to_get, analytics=False)
        l2_hit = metrics[UniqueMetricKey("L2 Hit (pti)", "", "core")]
        l2_access = metrics[UniqueMetricKey("L2 Access (pti)", "", "core")]

        result = asarray(l2_hit) / asarray(l2_access) * 100.0
        return {UniqueMetricKey("L2 hit ratio (total)", "%", "core"): result.tolist()}

    def _calc_L2DC_hit_ratio(self, repetition_ids: dict[str, list[int]]) -> MetricsData:
        metric_names_to_get: list[str] = [
            "L2 Hit from DC Miss (pti)",
            "L2 Access from DC Miss (pti)",
        ]
        metrics = self.get_data(repetition_ids, metric_names_to_get, analytics=False)
        l2_hit = metrics[UniqueMetricKey("L2 Hit from DC Miss (pti)", "", "core")]
        l2_access = metrics[UniqueMetricKey("L2 Access from DC Miss (pti)", "", "core")]

        result = asarray(l2_hit) / asarray(l2_access) * 100.0
        return {UniqueMetricKey("L2DC hit ratio", "%", "core"): result.tolist()}

    def _calc_L2_HWPF_hit_ratio(
        self, repetition_ids: dict[str, list[int]]
    ) -> MetricsData:
        metric_names_to_get: list[str] = [
            "L2 Hit from HWPF (pti)",
            "L2 Access from HWPF (pti)",
        ]
        metrics = self.get_data(repetition_ids, metric_names_to_get, analytics=False)
        l2_hit = metrics[UniqueMetricKey("L2 Hit from HWPF (pti)", "", "core")]
        l2_access = metrics[UniqueMetricKey("L2 Access from HWPF (pti)", "", "core")]

        result = asarray(l2_hit) / asarray(l2_access) * 100.0
        return {UniqueMetricKey("L2 HWPF hit ratio", "%", "core"): result.tolist()}

    def get_analytics(self, repetition_ids: dict[str, list[int]]) -> MetricsData:
        metrics: MetricsData = {}
        metrics |= self._calc_L2_miss_ratio_total(repetition_ids)
        metrics |= self._calc_L2DC_miss_ratio(repetition_ids)
        metrics |= self._calc_L2_HWPF_miss_ratio(repetition_ids)
        metrics |= self._calc_L2_hit_ratio_total(repetition_ids)
        metrics |= self._calc_L2DC_hit_ratio(repetition_ids)
        metrics |= self._calc_L2_HWPF_hit_ratio(repetition_ids)

        return metrics


def plot(db_session: Session) -> None:
    """
    _summary_

    :param db_session: _description_
    """
    Plotter(
        AMDuProfPCMAnalyzer(
            db_session,
            AMDuProfPCM_metrics,
            AMDuProfPCM_metrics_dict,
        ),
        "AMDuProfPCM",
    ).make_all()
