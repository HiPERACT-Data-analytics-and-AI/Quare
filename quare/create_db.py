from argparse import Namespace
from importlib import util
from pathlib import Path

from sqlalchemy.orm import Session

from .models import DBBase
from .utils import create_db_engine, discover_extensions, load_settings


def create_db(_: Namespace):
    """
    Creates Quare's DB using custom loaders for different profilers.

    The data is loaded by profiler-specific extensions.
    The extensions are discovered automatically and currently there is no possibility
    to load the data only by chosen extensions (however it is possible to temporarily
    change extension's name - remove "_ext" suffix - to hide extension from Quare).
    """
    db_engine = create_db_engine()
    settings = load_settings()
    data_dir_path = Path(settings["csvized_data_directory_path"])

    with Session(db_engine) as db_session:
        for extension_path in discover_extensions():
            path = extension_path / "models.py"
            spec = util.spec_from_file_location(path.stem, path.resolve())
            if spec is not None:
                module = util.module_from_spec(spec)
                if spec.loader is not None:
                    module.__package__ = "quare.extensions." + extension_path.stem
                    spec.loader.exec_module(module)

    DBBase.metadata.create_all(db_engine)

    with Session(db_engine) as db_session:
        for extension_path in discover_extensions():
            path = extension_path / "loader.py"
            spec = util.spec_from_file_location(path.stem, path.resolve())
            if spec is not None:
                module = util.module_from_spec(spec)
                if spec.loader is not None:
                    module.__package__ = "quare.extensions." + extension_path.stem
                    spec.loader.exec_module(module)
                    module.load(db_session, data_dir_path)

        db_session.commit()


if __name__ == "__main__":
    create_db(Namespace())
