from argparse import Namespace
from importlib import util
from pathlib import Path

from .models import DBBase
from .utils import (
    _create_db_engine,
    close_db_session,
    discover_extensions,
    get_db_session,
    load_settings,
)


def create_db(_: Namespace):
    """
    Creates Quare's DB using custom loaders for different profilers.

    The data is loaded by profiler-specific extensions.
    The extensions are discovered automatically and currently there is no possibility
    to load the data only by chosen extensions (however it is possible to temporarily
    change extension's name - remove "_ext" suffix - to hide extension from Quare).
    """
    settings = load_settings()
    data_dir_path = Path(settings["preprocessed_data_directory_path"])

    for extension_path in discover_extensions():
        path = extension_path / "models.py"
        if not path.exists():
            continue
        spec = util.spec_from_file_location(path.stem, path)
        if spec is not None:
            module = util.module_from_spec(spec)
            if spec.loader is not None:
                module.__package__ = "quare.extensions." + extension_path.stem
                spec.loader.exec_module(module)

    DBBase.metadata.create_all(_create_db_engine())

    for extension_path in discover_extensions():
        path = extension_path / "loader.py"
        if not path.exists():
            continue
        spec = util.spec_from_file_location(path.stem, path)
        if spec is not None:
            module = util.module_from_spec(spec)
            if spec.loader is not None:
                module.__package__ = "quare.extensions." + extension_path.stem
                spec.loader.exec_module(module)
                module.ExtensionDataLoaderImpl().load(data_dir_path)

        get_db_session().commit()
    close_db_session()


if __name__ == "__main__":
    create_db(Namespace())
