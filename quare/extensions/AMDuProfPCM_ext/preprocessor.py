from ...preprocessor import Preprocessor


class AMDuProfPCMPreprocessor(Preprocessor):
    def preprocess(self) -> None:
        FILE_BLOCKS: dict[str, tuple[str, bool]] = {
            "machine_info": ("System:,", True),
            "machine_cpu_topology": ("CPU Topology", False),
            "further_machine_info": ("Core P0 state frequency", True),
            "core_metrics": ("CORE METRICS", False),
            "l3_metrics": ("L3 METRICS", False),
        }
        for path in self.get_raw_profiler_files("*", "csv"):
            self.split_multi_block_csv(path, FILE_BLOCKS)


__extension_data_preprocessor__: type[Preprocessor] = AMDuProfPCMPreprocessor
