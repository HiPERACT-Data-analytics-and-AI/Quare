"""
Preprocessor for the AMD uProf MPI profiler extension.

AMD uProf MPI writes all profiling data for a single run into one CSV that
concatenates three logically distinct sections.
:class:`AMDuProfMPIPreprocessor` uses
:meth:`~quare.preprocessor.Preprocessor.split_multi_block_csv` to produce
one CSV per section.

Module-level attribute
----------------------
``__extension_data_preprocessor__``
    Set to :class:`AMDuProfMPIPreprocessor` so that
    :func:`~quare.preprocess.preprocess` can discover and instantiate it.
"""

from ...preprocessor import Preprocessor


class AMDuProfMPIPreprocessor(Preprocessor):
    """
    Splits raw AMD uProf MPI CSV files into per-section files.

    Overrides :meth:`~quare.preprocessor.Preprocessor.preprocess` to locate
    all ``*.csv`` files produced by the MPI profiler and split each one into
    three separate CSV files.

    Section mapping
    ---------------
    ========================= ========================== =================
    Output suffix             Header prefix              Include header?
    ========================= ========================== =================
    ``environment``           ``"ENVIRONMENT"``          No
    ``functions_summary``     ``"MPI FUNCTIONS SUMMARY"``  No
    ``rank_summary``          ``"MPI RANK SUMMARY"``     No
    ========================= ========================== =================
    """

    def preprocess(self) -> None:
        """
        Find all raw AMD uProf MPI CSV files and split each into section files.

        Iterates over every ``*.csv`` file found under the profiler's raw-data
        subdirectory and calls
        :meth:`~quare.preprocessor.Preprocessor.split_multi_block_csv` for
        each file using the predefined section blocks.
        """
        FILE_BLOCKS: dict[str, tuple[str, bool]] = {
            "environment": ("ENVIRONMENT", False),
            "functions_summary": ("MPI FUNCTIONS SUMMARY", False),
            "rank_summary": ("MPI RANK SUMMARY", False),
        }
        for path in self.get_raw_profiler_files("*", "csv"):
            self.split_multi_block_csv(path, FILE_BLOCKS)


__extension_data_preprocessor__: type[Preprocessor] = AMDuProfMPIPreprocessor
