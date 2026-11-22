# Test data

`motorBike_2024/128_GENOA` is a small subset of the 2024 OpenFOAM motorBike
measurements on a 2x64-core AMD EPYC 9554 (Genoa) node: mesh sizes `xsmall`
and `small` of three measurement variants (timing and counters, MPI trace,
top-down counters).

The AMD uProf files are unchanged apart from whitespace at line and file ends.  `log.checkMesh` keeps only the lines with
the mesh size and the number of ranks, and the solver logs keep the lines up to the
banner (with the date and time), the `ExecutionTime` lines and the
`Total Time` line.  The original analysis scripts give identical results on
the full and the reduced files.
