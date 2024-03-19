from collections.abc import Callable
from pathlib import Path


def _csvize_uprof_amd(raw_data_path: Path, csvized_path: Path) -> int:
    FILE_BLOCKS: dict[str, tuple[str, bool]] = {
        "machine_info": ("System:,", True),
        "machine_cpu_topology": ("CPU Topology", False),
        "further_machine_info": ("Core P0 state frequency", True),
        "core metrics": ("CORE METRICS", False),
        "l3_metrics": ("L3 METRICS", False),
    }
    # False means that string is not included in the first line of data
    # True means that specified string is already a part of data
    # Order of entries must be preserved

    file_counter: int = 0
    for input_file_path in raw_data_path.glob("**/prof.AMD.*.csv"):
        print("New path: ", csvized_path / input_file_path.relative_to(raw_data_path))
        file_counter += 1
        with input_file_path.open() as input_file:
            for key, block_prefix in FILE_BLOCKS.items():
                resulting_file_path: tuple[str, ...] = (
                    csvized_path / input_file_path.relative_to(raw_data_path)
                ).parts
                # open(
                #     path.as_posix()[:-3] + "parsed.csv", mode="w"
                # ) as out_file:
            #     core_metrics_flag: bool = False
            #     for line in file:
            #         if line.startswith("CORE METRICS"):
            #             core_metrics_flag = True
            #             continue
            #         if core_metrics_flag:
            #             if not line.strip():
            #                 core_metrics_flag = False
            #                 continue
            #             out_file.write(line)
    return file_counter


def _csvize_uprof_mpi(raw_data_path: Path, csvized_path: Path) -> int:
    file_counter: int = 0
    return file_counter


def csvize() -> None:
    CSVIZERS: dict[str, Callable[[Path, Path], int]] = {
        "AMDuProfPcm": _csvize_uprof_amd,
        "MPIuProf": _csvize_uprof_mpi,
    }

    raw_data_path: Path = Path("raw_data")
    if not raw_data_path.exists():
        raise FileNotFoundError(raw_data_path.resolve().as_posix())

    csvized_data_path: Path = Path("csvized_data")
    if not csvized_data_path.exists():
        csvized_data_path.mkdir()

    file_counter: int = 0
    for _, csvizer in CSVIZERS.items():
        file_counter += csvizer(raw_data_path, csvized_data_path)


if __name__ == "__main__":
    csvize()
