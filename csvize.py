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
        file_counter += 1
        with input_file_path.open() as input_file:
            # TODO: Check each block per line - with this it will be lacking-block-prone
            for filename_suffix, (
                csv_block_prefix,
                part_of_data,
            ) in FILE_BLOCKS.items():
                new_filename: str = f"{input_file_path.stem}.{filename_suffix}.csv"
                output_file_path: Path = (
                    csvized_path / input_file_path.relative_to(raw_data_path)
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
    print(f"Processed {file_counter} input files")


if __name__ == "__main__":
    csvize()
