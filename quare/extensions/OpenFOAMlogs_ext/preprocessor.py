"""
Preprocessor stub for the OpenFOAM logs extension (work in progress).

This extension is currently a placeholder.  The base
:class:`~quare.preprocessor.Preprocessor` implementation is used, which
copies the profiler's raw-data subdirectory to the preprocessed-data
area without any further transformation.

When this extension is fully implemented, this module should be replaced with
a subclass of :class:`~quare.preprocessor.Preprocessor` that parses
OpenFOAM log files and converts them into the canonical CSV layout expected by
:class:`~quare.data_loader.DataLoader`.

Module-level attribute
----------------------
``__extension_data_preprocessor__``
    Set to :class:`~quare.preprocessor.Preprocessor` (the no-op base class)
    so that :func:`~quare.preprocess.preprocess` can discover and instantiate
    it without errors.
"""

from ...preprocessor import Preprocessor

__extension_data_preprocessor__: type[Preprocessor] = Preprocessor
