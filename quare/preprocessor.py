from pathlib import Path
from shutil import copytree


class Preprocessor:
    def __init__(
        self,
        profiler_name: str,
        raw_data_path: Path,
        preprocessed_data_path: Path,
    ) -> None:
        self.profiler_name: str = profiler_name
        self._raw_data_path: Path = raw_data_path
        self._preprocessed_data_path: Path = preprocessed_data_path

    def copy_directories(self, dirname_pattern: str) -> int:
        """_summary_"""
        counter: int = 0
        for input_file_path in self._raw_data_path.glob(f"**/{dirname_pattern}"):
            output_file_path: Path = (
                self._preprocessed_data_path
                / input_file_path.relative_to(self._raw_data_path)
            )
            try:
                copytree(input_file_path, output_file_path)
            except FileExistsError as e:
                print(e)
                continue
            counter += 1
        return counter

    def split_multi_block_csv(
        self,
        input_file_path: Path,
        file_blocks: dict[str, tuple[str, bool]],
    ) -> None:
        with input_file_path.open() as input_file:
            # TODO: Check each block per line - with this it will be lacking-block-prone
            for filename_suffix, (
                csv_block_prefix,
                part_of_data,
            ) in file_blocks.items():
                new_filename: str = f"{input_file_path.stem}.{filename_suffix}.csv"
                output_file_path: Path = (
                    self._preprocessed_data_path
                    / input_file_path.relative_to(self._raw_data_path)
                ).parent / new_filename

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

    def get_raw_profiler_files(
        self, filename_pattern: str, extension: str
    ) -> list[Path]:
        return list(
            self._raw_data_path.glob(
                f"**/{self.profiler_name}/**/{filename_pattern}.{extension}"
            )
        )

    def preprocess(self) -> None:
        self.copy_directories(self.profiler_name)
