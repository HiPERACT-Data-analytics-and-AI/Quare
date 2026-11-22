"""
Importers that convert measurement trees with a foreign layout into the raw
data layout expected by ``preprocess-data``.

Each importer module provides ``add_arguments(parser)`` and
``run(args, raw_data_path)``; the modules are registered in
:data:`quare.import_data.IMPORTERS`.
"""
