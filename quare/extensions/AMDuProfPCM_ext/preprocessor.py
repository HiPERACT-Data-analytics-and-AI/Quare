"""
Preprocessor for the AMD uProf Performance Counter Monitor (PCM) extension.

AMD uProf PCM writes all profiling data for a single run into one CSV file
that concatenates several logically distinct sections separated by blank
lines.  :class:`AMDuProfPCMPreprocessor` uses
:meth:`~quare.preprocessor.Preprocessor.split_multi_block_csv` to split that
file into one CSV per section, making downstream loading straightforward.

Module-level attribute
----------------------
``__extension_data_preprocessor__``
    Set to :class:`AMDuProfPCMPreprocessor` so that
    :func:`~quare.preprocess.preprocess` can discover and instantiate it.
"""

from ...preprocessor import Preprocessor


class AMDuProfPCMPreprocessor(Preprocessor):
    """
    Splits raw AMD uProf PCM CSV files into per-section files.

    Overrides :meth:`~quare.preprocessor.Preprocessor.preprocess` to locate
    all ``*.csv`` files produced by the PCM profiler and split each one into
    five separate CSV files using the section header prefixes defined in
    ``FILE_BLOCKS``.

    Section mapping
    ---------------
    ======================= ====================== =================
    Output suffix           Header prefix          Include header?
    ======================= ====================== =================
    ``machine_info``        ``"System:,"``         Yes
    ``machine_cpu_topology``  ``"CPU Topology"``   No
    ``further_machine_info``  ``"Core P0 state…"`` Yes
    ``core_metrics``        ``"CORE METRICS"``     No
    ``l3_metrics``          ``"L3 METRICS"``       No
    ======================= ====================== =================
    """

    def preprocess(self) -> None:
        """
        Find all raw AMD uProf PCM CSV files and split each into section files.

        Iterates over every ``*.csv`` file found under the profiler's raw-data
        subdirectory (via
        :meth:`~quare.preprocessor.Preprocessor.get_raw_profiler_files`) and
        calls :meth:`~quare.preprocessor.Preprocessor.split_multi_block_csv`
        for each file using the predefined section blocks.
        """
        FILE_BLOCKS: dict[str, tuple[str, bool]] = {
            "machine_info": ("System:,", True),
            "machine_cpu_topology": ("CPU Topology", False),
            "further_machine_info": ("Core P0 state frequency", True),
            "core_metrics": ("CORE METRICS", False),
            "l3_metrics": ("L3 METRICS", False),
        }
        for path in self.get_raw_profiler_files("*", "csv"):
            self.split_multi_block_csv(path, FILE_BLOCKS)


__extension_data_preprocessor__: type[Preprocessor] = AMDuProfPCMPreprocessor
