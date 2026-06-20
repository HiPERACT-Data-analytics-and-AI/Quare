Supported analyses
==================

Quare computes derived analyses from raw profiler metrics stored in the
database.  Each analysis is registered in
:attr:`~quare.data_retriever.DataRetriever.AVAILABLE_ANALYTICS` and
produced automatically during the ``plot`` step.

General
-------

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Analysis
     - Formula
   * - **FVOPS** (Floating-point / Vector Operations Per Second)
     - ``task_sizes_dict.size / profiling_session.exec_time_s``

AMD uProf PCM — L2 cache ratios
---------------------------------

All ratios are expressed as percentages.  ``avg()`` denotes the mean across
repetitions; ``pti`` = per-thread iteration.

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Analysis
     - Formula
   * - **L2 miss ratio (total)** [%]
     - ``avg("L2 Miss (pti)") / avg("L2 Access (pti)") × 100``
   * - **L2DC miss ratio** [%]
     - ``avg("L2 Miss from DC Miss (pti)") / avg("L2 Access from DC Miss (pti)") × 100``
   * - **L2 HWPF miss ratio** [%]
     - ``avg("L2 Miss from HWPF (pti)") / avg("L2 Access from HWPF (pti)") × 100``
   * - **L2 hit ratio (total)** [%]
     - ``avg("L2 Hit (pti)") / avg("L2 Access (pti)") × 100``
   * - **L2DC hit ratio** [%]
     - ``avg("L2 Hit from DC Miss (pti)") / avg("L2 Access from DC Miss (pti)") × 100``
   * - **L2 HWPF hit ratio** [%]
     - ``avg("L2 Hit from HWPF (pti)") / avg("L2 Access from HWPF (pti)") × 100``

AMD uProf MPI
--------------

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Analysis
     - Description
   * - **MPI ratio based on avg comm time** [%]
     - Application-specific ratio derived from MPI communication time logs.
       Requires application-level MPI log data.

Time comparison
---------------

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Analysis
     - Description
   * - **Time Comparison**
     - Execution time and percent of total time plotted per machine,
       enabling cross-machine performance comparison.
