from collections.abc import Callable
from pathlib import Path


def _csvize_uprof_amd(raw_data_path: Path, csvized_path: Path) -> int:
    file_counter: int = 0
    for path in raw_data_path.glob("**/prof.AMD.*.csv"):
        # print(
        #     "New path: ", Path.cwd().as_posix()[:-9] + "/csvized" + path.as_posix()[2:]
        # )
        print("New path: ", (csvized_path / path).as_posix())
        # if "parsed.csv" in path.as_posix():
        #     continue
        # file_counter += 1
        # with path.open() as file, open(
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

    work_dir: Path = Path(__file__).resolve().parent


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
