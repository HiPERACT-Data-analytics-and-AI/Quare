from argparse import Namespace
from importlib import util
from pathlib import Path

from .utils import discover_extensions, load_settings


def preprocess(__: Namespace) -> None:
    """
    Sometimes profilers does not produce proper files. The files are hard to consume
    by the DB loaders. The function preprocess the files (if necessary) and copy them
    to a location for preprocessed files.

    :raises FileNotFoundError: When provided source path does not exist.
    """
    settings = load_settings()
    raw_data_path: Path = Path(settings["raw_data_directory_path"])
    preprocessed_data_path: Path = Path(settings["preprocessed_data_directory_path"])

    if not raw_data_path.exists():
        raise FileNotFoundError(raw_data_path.resolve().as_posix())

    if not preprocessed_data_path.exists():
        preprocessed_data_path.mkdir()

    for extension_path in discover_extensions():
        path = extension_path / "preprocessor.py"
        spec = util.spec_from_file_location(path.stem, path)
        if spec is not None:
            module = util.module_from_spec(spec)
            if spec.loader is not None:
                module.__package__ = "quare.extensions." + extension_path.stem
                spec.loader.exec_module(module)
                module.__extension_data_preprocessor__(
                    extension_path.stem[: -len("_ext")],
                    raw_data_path,
                    preprocessed_data_path,
                ).preprocess()


if __name__ == "__main__":
    preprocess(Namespace())
