"""
Plotter configuration for the AMD uProf MPI extension.

This module wires the AMD uProf MPI extension into the Quare plotting
pipeline by assigning the required module-level attributes.

No MPI-specific analyses are currently registered beyond those provided by
:class:`~quare.extensions.amduprof_data_retriever.AMDuProfDataRetriever`.

Module-level attributes
-----------------------
``__extension_data_retriever__``
    :class:`~quare.extensions.amduprof_data_retriever.AMDuProfDataRetriever`
    — augments :meth:`~quare.data_retriever.DataRetriever.get_result_info`
    with AMD-specific hardware metadata from the PCM machine-info tables.
``__extension_data_plotter__``
    :class:`~quare.plotter.Plotter` — the generic plotter (no MPI-specific
    customisation needed).
``__extension_metrics_table__``
    :class:`~quare.extensions.AMDuProfMPI_ext.models.AMDuProfMPI_metrics`.
``__extension_metrics_dict__``
    :class:`~quare.extensions.AMDuProfMPI_ext.models.AMDuProfMPI_metrics_dict`.
"""

from __future__ import annotations

from ...data_retriever import DataRetriever
from ...plotter import Plotter
from ..amduprof_data_retriever import AMDuProfDataRetriever
from .models import AMDuProfMPI_metrics, AMDuProfMPI_metrics_dict

__extension_data_retriever__: type[DataRetriever] = AMDuProfDataRetriever
__extension_data_plotter__: type[Plotter] = Plotter
__extension_metrics_table__ = AMDuProfMPI_metrics
__extension_metrics_dict__ = AMDuProfMPI_metrics_dict
