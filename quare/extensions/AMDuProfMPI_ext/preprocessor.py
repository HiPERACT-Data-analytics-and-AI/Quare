from ...preprocessor import Preprocessor


class AMDuProfMPIPreprocessor(Preprocessor):
    def preprocess(self) -> None:
        FILE_BLOCKS: dict[str, tuple[str, bool]] = {
            "environment": ("ENVIRONMENT", False),
            "functions_summary": ("MPI FUNCTIONS SUMMARY", False),
            "rank_summary": ("MPI RANK SUMMARY", False),
        }
        for path in self.get_raw_profiler_files("*", "csv"):
            self.split_multi_block_csv(path, FILE_BLOCKS)


__extension_data_preprocessor__: type[Preprocessor] = AMDuProfMPIPreprocessor
