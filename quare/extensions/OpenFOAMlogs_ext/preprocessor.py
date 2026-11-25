"""
Preprocessor for the OpenFOAM logs extension.

OpenFOAM logs need no transformation: they are parsed by the loader.  The
base :class:`~quare.preprocessor.Preprocessor` therefore only copies the
``OpenFOAMlogs`` directories from the raw-data tree to the preprocessed-data
tree.

Expected raw layout (one run per date directory)::

    <session>/<machine>/<use_case>/<task_size>/<date>[_<tag>]/OpenFOAMlogs/
        <run>.checkMesh.log      mesh size and number of MPI ranks
        <run>.<solver>.log       solver log, e.g. ``run.simpleFoam.log``

Module-level attribute
----------------------
``__extension_data_preprocessor__``
    Set to :class:`~quare.preprocessor.Preprocessor` so that
    :func:`~quare.preprocess.preprocess` can discover and instantiate it.
"""

from ...preprocessor import Preprocessor

__extension_data_preprocessor__: type[Preprocessor] = Preprocessor
