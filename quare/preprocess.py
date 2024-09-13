from argparse import Namespace
from collections.abc import Callable
from pathlib import Path
from shutil import copytree

from .utils import load_settings


def _split_multi_block_csv(
    raw_data_path: Path,
    preprocessed_path: Path,
    filename_pattern: str,
    file_blocks: dict[str, tuple[str, bool]],
) -> int:
    """_summary_

    :param raw_data_path: _description_
    :param preprocessed_path: _description_
    :param filename_pattern: _description_
    :param file_blocks: _description_
    :return: _description_
    """
    file_counter: int = 0
    for input_file_path in raw_data_path.glob(filename_pattern):
        file_counter += 1
        with input_file_path.open() as input_file:
            # TODO: Check each block per line - with this it will be lacking-block-prone
            for filename_suffix, (
                csv_block_prefix,
                part_of_data,
            ) in file_blocks.items():
                new_filename: str = f"{input_file_path.stem}.{filename_suffix}.csv"
                output_file_path: Path = (
                    preprocessed_path / input_file_path.relative_to(raw_data_path)
                ).parent / new_filename
                # print(output_file_path)

                previous_line: str = ""
                for line in input_file:
                    if line.startswith(csv_block_prefix):
                        previous_line = line
                        break
                else:
                    continue

                output_file_path.parent.mkdir(parents=True, exist_ok=True)
                with output_file_path.open("w") as output_file:
                    if part_of_data:
                        output_file.write(previous_line)
                    for line in input_file:
                        if not line.strip():
                            break
                        output_file.write(line)
    return file_counter


def _split_uprof_pcm(raw_data_path: Path, preprocessed_path: Path) -> int:
    FILE_BLOCKS: dict[str, tuple[str, bool]] = {
        "machine_info": ("System:,", True),
        "machine_cpu_topology": ("CPU Topology", False),
        "further_machine_info": ("Core P0 state frequency", True),
        "core_metrics": ("CORE METRICS", False),
        "l3_metrics": ("L3 METRICS", False),
    }
    """_summary_

    :return: _description_
    """
    # False means that string is not included in the first line of data
    # True means that specified string is already a part of data
    # Order of entries must be preserved

    return _split_multi_block_csv(
        raw_data_path, preprocessed_path, "**/AMDuProfPCM/**/*.csv", FILE_BLOCKS
    )


def _split_uprof_mpi(raw_data_path: Path, preprocessed_path: Path) -> int:
    """_summary_

    :param raw_data_path: _description_
    :param preprocessed_path: _description_
    :return: _description_
    """
    FILE_BLOCKS: dict[str, tuple[str, bool]] = {
        "environment": ("ENVIRONMENT", False),
        "functions_summary": ("MPI FUNCTIONS SUMMARY", False),
        "rank_summary": ("MPI RANK SUMMARY", False),
    }

    return _split_multi_block_csv(
        raw_data_path, preprocessed_path, "**/AMDuProfMPI/**/*.csv", FILE_BLOCKS
    )


def _copy_app_logs(raw_data_path: Path, preprocessed_path: Path) -> int:
    """_summary_

    :param raw_data_path: _description_
    :param preprocessed_path: _description_
    :return: _description_
    """
    counter: int = 0
    for input_file_path in raw_data_path.glob("**/app_logs"):
        # print(input_file_path)
        output_file_path: Path = preprocessed_path / input_file_path.relative_to(
            raw_data_path
        )
        # print(output_file_path)
        try:
            copytree(input_file_path, output_file_path)
        except FileExistsError as e:
            print(e)
            continue
        counter += 1
    return counter


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

    PREPROCESSORS: dict[str, Callable[[Path, Path], int]] = {
        "AMDuProfPCM": _split_uprof_pcm,
        "AMDuProfMPI": _split_uprof_mpi,
        "app_logs": _copy_app_logs,
    }

    if not raw_data_path.exists():
        raise FileNotFoundError(raw_data_path.resolve().as_posix())

    if not preprocessed_data_path.exists():
        preprocessed_data_path.mkdir()

    file_counter: int = 0
    for _, preprocessor in PREPROCESSORS.items():
        file_counter += preprocessor(raw_data_path, preprocessed_data_path)
    print(f"Processed {file_counter} input files")


if __name__ == "__main__":
    preprocess(Namespace())
