from ...data_retriever import DataRetrieversManager
from ...extensions_abcs import ExtensionDataPlotter
from ...plotter import Plotter
from ..amduprof_data_retriever import AMDuProfDataRetriever
from .models import AMDuProfMPI_metrics, AMDuProfMPI_metrics_dict

__extension_data_retriever__ = AMDuProfDataRetriever
__extension_metrics_table__ = AMDuProfMPI_metrics
__extension_metrics_dict__ = AMDuProfMPI_metrics_dict


class ExtensionDataPlotterImpl(ExtensionDataPlotter):
    @staticmethod
    def plot() -> None:
        Plotter(
            DataRetrieversManager.get_retriever("AMDuProfMPI"),
            "AMDuProfMPI",
        ).make_all()
