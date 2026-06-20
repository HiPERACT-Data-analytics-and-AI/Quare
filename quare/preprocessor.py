"""
Base preprocessor for raw profiler output files.

:class:`Preprocessor` provides two generic operations that most profiler
extensions need:

* :meth:`copy_directories` — mirror a subtree from the raw-data area to the
  preprocessed-data area without modification.
* :meth:`split_multi_block_csv` — parse a single multi-section CSV file (as
  produced by AMD uProf) and write each section to its own file.

Extension preprocessors subclass :class:`Preprocessor`, override
:meth:`preprocess`, and call these helpers as needed.
"""

import logging
from pathlib import Path
from shutil import copytree

_log = logging.getLogger(__name__)


class Preprocessor:
    """
    Base class for profiler-specific data preprocessors.

    Provides filesystem helpers used by extension subclasses to copy or
    split raw profiler output into the canonical preprocessed directory layout.

    :ivar profiler_name: Identifier of the profiler this preprocessor handles
        (e.g. ``"AMDuProfPCM"``).  Used as a directory-name pattern when
        discovering raw files.
    :vartype profiler_name: str
    """

    def __init__(
        self,
        profiler_name: str,
        raw_data_path: Path,
        preprocessed_data_path: Path,
    ) -> None:
        """
        Initialise the preprocessor with source and destination paths.

        :param profiler_name: Name of the profiler whose data this instance
            handles.  Also used as the subdirectory pattern when searching for
            raw files (see :meth:`get_raw_profiler_files`).
        :type profiler_name: str
        :param raw_data_path: Root directory that contains raw profiler output,
            typically the value of ``raw_data_directory_path`` in
            ``settings.json``.
        :type raw_data_path: pathlib.Path
        :param preprocessed_data_path: Root directory where preprocessed files
            should be written, typically ``preprocessed_data_directory_path``
            from ``settings.json``.
        :type preprocessed_data_path: pathlib.Path
        """
        self.profiler_name: str = profiler_name
        self._raw_data_path: Path = raw_data_path
        self._preprocessed_data_path: Path = preprocessed_data_path

    def copy_directories(self, dirname_pattern: str) -> int:
        """
        Recursively copy matching directories from the raw area to the
        preprocessed area.

        Walks :attr:`_raw_data_path` recursively, finds every directory whose
        name matches *dirname_pattern*, and copies it (together with its
        contents) to the mirrored location under
        :attr:`_preprocessed_data_path`.  Directories that already exist at
        the destination are skipped and a debug message is logged.

        :param dirname_pattern: Glob pattern for directory names to copy
            (e.g. the profiler name ``"AMDuProfPCM"``).
        :type dirname_pattern: str
        :returns: Number of directories successfully copied (not counting
            skipped ones).
        :rtype: int
        """
        counter: int = 0
        for input_file_path in self._raw_data_path.glob(f"**/{dirname_pattern}"):
            output_file_path: Path = (
                self._preprocessed_data_path
                / input_file_path.relative_to(self._raw_data_path)
            )
            try:
                copytree(input_file_path, output_file_path)
            except FileExistsError as e:
                _log.debug("Skipping existing directory: %s", e)
                continue
            counter += 1
        return counter

    def split_multi_block_csv(
        self,
        input_file_path: Path,
        file_blocks: dict[str, tuple[str, bool]],
    ) -> None:
        """
        Split a multi-section CSV file into one file per section.

        AMD uProf produces a single CSV that concatenates several logically
        distinct sections (machine info, CPU topology, performance counters,
        etc.) separated by blank lines.  This method reads the file once,
        locates each section by its header prefix, and writes the section's
        lines to a new file named ``<stem>.<block_name>.csv`` in the
        corresponding preprocessed-data directory.

        Because the full file is loaded into memory before processing, sections
        may appear in any order and missing sections are silently skipped.

        :param input_file_path: Absolute or relative path to the raw CSV file
            to split.  Must be located within :attr:`_raw_data_path`.
        :type input_file_path: pathlib.Path
        :param file_blocks: Mapping from output file suffix to a
            ``(header_prefix, include_header)`` tuple:

            * ``header_prefix`` — the string that the section's first line
              must start with (used to locate the section boundary).
            * ``include_header`` — if ``True``, the header line is written as
              the first line of the output file; if ``False``, parsing starts
              on the line *after* the header.
        :type file_blocks: dict[str, tuple[str, bool]]
        """
        lines: list[str] = input_file_path.read_text().splitlines(keepends=True)

        for filename_suffix, (csv_block_prefix, part_of_data) in file_blocks.items():
            new_filename: str = f"{input_file_path.stem}.{filename_suffix}.csv"
            output_file_path: Path = (
                self._preprocessed_data_path
                / input_file_path.relative_to(self._raw_data_path)
            ).parent / new_filename

            # Find the header line for this block (search the full file each time).
            start_idx: int = -1
            for i, line in enumerate(lines):
                if line.startswith(csv_block_prefix):
                    start_idx = i
                    break

            if start_idx == -1:
                continue

            output_file_path.parent.mkdir(parents=True, exist_ok=True)
            with output_file_path.open("w") as output_file:
                if part_of_data:
                    output_file.write(lines[start_idx])
                for line in lines[start_idx + 1 :]:
                    if not line.strip():
                        break
                    output_file.write(line)

    def get_raw_profiler_files(
        self, filename_pattern: str, extension: str
    ) -> list[Path]:
        """
        Return a list of raw profiler files matching a name and extension pattern.

        Searches recursively under the profiler's subdirectory within
        :attr:`_raw_data_path`.  The glob pattern is::

            **/<profiler_name>/**/<filename_pattern>.<extension>

        :param filename_pattern: Glob pattern for the file stem
            (e.g. ``"*"`` to match all files).
        :type filename_pattern: str
        :param extension: File extension without the leading dot
            (e.g. ``"csv"``).
        :type extension: str
        :returns: List of :class:`~pathlib.Path` objects for all matching
            files.  May be empty if no files are found.
        :rtype: list[pathlib.Path]
        """
        return list(
            self._raw_data_path.glob(
                f"**/{self.profiler_name}/**/{filename_pattern}.{extension}"
            )
        )

    def preprocess(self) -> None:
        """
        Execute the preprocessing workflow for this profiler.

        The base implementation simply copies directories matching the profiler
        name from the raw-data area to the preprocessed-data area using
        :meth:`copy_directories`.

        Extension subclasses should override this method to perform additional
        transformations (e.g. :meth:`split_multi_block_csv`) before or after
        calling ``super().preprocess()``.
        """
        self.copy_directories(self.profiler_name)
