from sqlalchemy.orm import DeclarativeBase


class DBBase(DeclarativeBase):
    pass


class ProfilingSession(DBBase):
    __tablename__ = "Profiling_session"
    ...


class AMDuProfPcm_machine_info(DBBase):
    __tablename__ = "AMDuProfPcm_machine_info"
    ...


class AMDuProfPcm_machine_cpu_topology(DBBase):
    __tablename__ = "AMDuProfPcm_machine_cpu_topology"
    ...


class AMDuProfPcm_further_machine_info(DBBase):
    __tablename__ = "AMDuProfPcm_further_machine_info"
    ...


class AMDuProfPcm_core_metrics(DBBase):
    __tablename__ = "AMDuProfPcm_core_metrics"
    ...


class AMDuProfPcm_l3_metrics(DBBase):
    __tablename__ = "AMDuProfPcm_l3_metrics"
    ...


class MPIuProf_environment(DBBase):
    __tablename__ = "MPIuProf_environment"
    ...


class MPIuProf_functions_summary(DBBase):
    __tablename__ = "MPIuProf_functions_summary"
    ...


class MPIuProf_rank_summary(DBBase):
    __tablename__ = "MPIuProf_rank_summary"
    ...
