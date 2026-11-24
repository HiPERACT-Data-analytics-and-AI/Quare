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

`motorBike_2024/128_ROME`, `192_GENOA` and `256_BERGAMO` hold the `xsmall`
size only (timing and counters, MPI trace, and top-down where measured; Rome
has no top-down run), reduced in the same way.  For Bergamo the trace log is
`log.simpleFoam.MPItrace1_Delay_22`, because `mpi.trace0` belongs to that run.

`motorBike_2024/128_GENOA/Lik_AOCC_9554_Sumup03_06_2024_17_43_02` holds the
LIKWID output (`prof.lik.L2/L3/NUMA_<size>.txt`, unchanged apart from trailing whitespace) of `xsmall` and
`small`; of `log.simpleFoam.likL2` only the banner with the run date is kept.

`motorBike_2026/192_GENOA_2026` is the `xsmall` size of one 2026 run
configuration (2 nodes, 192 ranks, 4 ranks per CCX): timing, power-run and MPI
trace logs, the top-down counter file (with a `System (Aggregated)` column),
the MPI summary and the power timecharts.  The solver logs are reduced as for
2024 and also lose the `MCW rank` binding lines of the banner.

`UAP/Rome` holds the sizes `uxlow` and `ulow` of the UAP measurements on a
2x64-core AMD EPYC 7742 (Rome) node: the runs `1n1r` to `1n6r` and the LIKWID
runs. The solver logs keep the banner, the `ExecutionTime` lines and the
`Total Time` line, `log.renumberMesh` keeps the `Mesh region0 size` line; the
uProf profile (`1n4r`, `1n5r`), `mpi-summary.csv` and the LIKWID files of
simpleFoam and pimpleFoam are unchanged. The Rome node has no top-down counters.
