from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class DBBase(DeclarativeBase):
    pass


class Machine(DBBase):
    __tablename__ = "Machine"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))


class ProfilingSession(DBBase):
    __tablename__ = "Profiling_session"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str | None] = mapped_column(String(128))
    use_case: Mapped[str] = mapped_column(String(128))
    use_case_size: Mapped[str] = mapped_column(String(32))
    date: Mapped[datetime | None]


class AMDuProfPcm_machine_info(DBBase):
    __tablename__ = "AMDuProfPcm_machine_info"
    id: Mapped[int] = mapped_column(primary_key=True)
    system: Mapped[str] = mapped_column(String(256))
    num_of_sockets: Mapped[int]
    num_of_ccds: Mapped[int]
    num_of_cores: Mapped[int]
    num_of_threads: Mapped[int]
    smt_enabled_in_hw: Mapped[bool]
    smt_enabled_in_os: Mapped[bool]
    num_of_threads_sharing_l3: Mapped[int]


class AMDuProfPcm_machine_cpu_topology(DBBase):
    __tablename__ = "AMDuProfPcm_machine_cpu_topology"
    id: Mapped[int] = mapped_column(primary_key=True)
    socket: Mapped[int]
    ccd: Mapped[int]
    cores: Mapped[str] = mapped_column(String(128))


class AMDuProfPcm_further_machine_info(DBBase):
    __tablename__ = "AMDuProfPcm_further_machine_info"
    id: Mapped[int] = mapped_column(primary_key=True)
    core_p0_state_freq: Mapped[float]
    multiplex_interval_for_core: Mapped[float]
    multiplex_interval_for_l3: Mapped[float]
    multiplex_interval_for_df: Mapped[float]
    version: Mapped[str] = mapped_column(String(16))


class AMDuProfPcm_core_metrics(DBBase):
    __tablename__ = "AMDuProfPcm_core_metrics"
    id: Mapped[int] = mapped_column(primary_key=True)
    core: Mapped[int]
    utilization_percent: Mapped[float | None]
    eff_freq: Mapped[float | None]
    ipc_sys_and_user: Mapped[float | None]
    cpi_sys_and_user: Mapped[float | None]
    branch_misprediction_ratio: Mapped[float | None]
    ic_fetch_miss_ratio: Mapped[float | None]
    op_cache_fetch_miss_ratio: Mapped[float | None]
    ic_access: Mapped[float | None]
    ic_miss: Mapped[float | None]
    dc_access: Mapped[float | None]
    dc_fills_from_same_ccx: Mapped[float | None]
    dc_fills_from_different_ccx_in_same_node: Mapped[float | None]
    dc_fills_from_local_memory: Mapped[float | None]
    dc_fills_from_remote_ccx_cache: Mapped[float | None]
    dc_fills_from_remote_memory: Mapped[float | None]
    all_dc_fills: Mapped[float | None]
    swpf_dc_fills_from_dram_or_io_connected_in_remote_node: Mapped[float | None]
    swpf_dc_fills_from_ccx_cache_in_remote_node: Mapped[float | None]
    swpf_dc_fills_from_dram_or_io_connected_in_local_node: Mapped[float | None]
    swpf_dc_fills_from_cache_of_another_ccx_in_local_node: Mapped[float | None]
    swpf_dc_fills_from_l3_or_different_l2_in_same_ccx: Mapped[float | None]
    swpf_dc_fills_from_l2: Mapped[float | None]
    hwpf_dc_fills_from_dram_or_io_connected_in_remote_node: Mapped[float | None]
    hwpf_dc_fills_from_ccx_cache_in_remote_node: Mapped[float | None]
    hwpf_dc_fills_from_dram_or_io_connected_in_local_node: Mapped[float | None]
    hwpf_dc_fills_from_cache_of_another_ccx_in_local_node: Mapped[float | None]
    hwpf_dc_fills_from_l3_or_different_l2_in_same_ccx: Mapped[float | None]
    hwpf_dc_fills_from_l2: Mapped[float | None]
    l2_access: Mapped[float | None]
    l2_access_from_ic_miss: Mapped[float | None]
    l2_access_from_dc_miss: Mapped[float | None]
    l2_access_from_hwpf: Mapped[float | None]
    l2_miss: Mapped[float | None]
    l2_miss_from_ic_miss: Mapped[float | None]
    l2_miss_from_dc_miss: Mapped[float | None]
    l2_miss_from_hwpf: Mapped[float | None]
    l2_hit: Mapped[float | None]
    l2_hit_from_ic_miss: Mapped[float | None]
    l2_hit_from_dc_miss: Mapped[float | None]
    l2_hit_from_hwpf: Mapped[float | None]
    l1_itlb_miss: Mapped[float | None]
    l2_itlb_miss: Mapped[float | None]
    l1_dtlb_miss: Mapped[float | None]
    l2_dtlb_miss: Mapped[float | None]
    all_tlbs_flushed: Mapped[float | None]
    total_dispatch_slots: Mapped[float | None]
    smt_disp_contention: Mapped[float | None]
    frontend_bound: Mapped[float | None]
    bad_speculation: Mapped[float | None]
    backend_bound: Mapped[float | None]
    retiring: Mapped[float | None]
    ipc: Mapped[float | None]
    frontend_bound_latency: Mapped[float | None]
    frontend_bound_bw: Mapped[float | None]
    bad_speculation_mispredicts: Mapped[float | None]
    bad_speculation_pipeline_restarts: Mapped[float | None]
    backend_bound_memory: Mapped[float | None]
    backend_bound_cpu: Mapped[float | None]
    retiring_fastpath: Mapped[float | None]
    retiring_microcode: Mapped[float | None]


class AMDuProfPcm_l3_metrics(DBBase):
    __tablename__ = "AMDuProfPcm_l3_metrics"
    id: Mapped[int] = mapped_column(primary_key=True)
    ccx: Mapped[int]
    l3_access: Mapped[float]
    l3_miss: Mapped[float]
    l3_miss_percent: Mapped[float]
    ave_l3_miss_latency: Mapped[float]


class MPIuProf_environment(DBBase):
    __tablename__ = "MPIuProf_environment"
    id: Mapped[int] = mapped_column(primary_key=True)
    total_ranks: Mapped[int]
    lib_version: Mapped[str] = mapped_column(String(256))
    std_version: Mapped[str] = mapped_column(String(16))


class MPIuProf_functions_summary(DBBase):
    __tablename__ = "MPIuProf_functions_summary"
    id: Mapped[int] = mapped_column(primary_key=True)
    function: Mapped[str] = mapped_column(String(32))
    min_time: Mapped[float]
    max_time: Mapped[float]
    average_time: Mapped[float]
    mpi_time_percent: Mapped[float]
    volume: Mapped[int]
    calls: Mapped[int]
    total_time: Mapped[float]


class MPIuProf_rank_summary(DBBase):
    __tablename__ = "MPIuProf_rank_summary"
    id: Mapped[int] = mapped_column(primary_key=True)
    rank: Mapped[int]
    pid: Mapped[int]
    mpi_time: Mapped[float]
    mpi_time_percent: Mapped[float]
    wait_time: Mapped[float]
    call_count: Mapped[int]
    volume: Mapped[int]
