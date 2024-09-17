from ...data_retriever import DataRetriever
from ...plotter import Plotter
from ..amduprof_data_retriever import AMDuProfDataRetriever
from .models import AMDuProfMPI_metrics, AMDuProfMPI_metrics_dict

__extension_data_retriever__: type[DataRetriever] = AMDuProfDataRetriever
__extension_data_plotter__: type[Plotter] = Plotter
__extension_metrics_table__ = AMDuProfMPI_metrics
__extension_metrics_dict__ = AMDuProfMPI_metrics_dict
