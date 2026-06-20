"""
Shared data retriever for all AMD uProf profiler extensions.

:class:`AMDuProfDataRetriever` overrides
:meth:`~quare.data_retriever.DataRetriever.get_result_info` to include the
AMD-specific hardware metadata stored in
:class:`~quare.extensions.AMDuProfPCM_ext.models.AMDuProfPCM_machine_info`
and
:class:`~quare.extensions.AMDuProfPCM_ext.models.AMDuProfPCM_further_machine_info`.

Both the PCM extension and the MPI extension inherit from this class so that
their INFO plots display consistent AMD hardware information.
"""

from sqlalchemy import select

from ..data_retriever import DataRetriever, RepetitionIDs
from .AMDuProfPCM_ext.models import (
    AMDuProfPCM_further_machine_info,
    AMDuProfPCM_machine_info,
)


class AMDuProfDataRetriever(DataRetriever):
    """
    :class:`~quare.data_retriever.DataRetriever` subclass that enriches the
    result-info dictionary with AMD-specific hardware metadata.

    Queries :class:`~quare.extensions.AMDuProfPCM_ext.models.AMDuProfPCM_machine_info`
    and :class:`~quare.extensions.AMDuProfPCM_ext.models.AMDuProfPCM_further_machine_info`
    for the first matching repetition and merges the result with the base-class
    info dictionary.
    """

    def get_result_info(self, repetition_ids: RepetitionIDs) -> dict[str, str]:
        """
        Build a metadata dictionary that combines base-class fields with
        AMD-specific hardware topology and frequency information.

        Iterates *repetition_ids* and returns on the first repetition that
        has a corresponding row in both
        :class:`~quare.extensions.AMDuProfPCM_ext.models.AMDuProfPCM_machine_info`
        and
        :class:`~quare.extensions.AMDuProfPCM_ext.models.AMDuProfPCM_further_machine_info`.
        If no such repetition is found, returns an empty dict.

        The returned dict merges the fields from
        :meth:`~quare.data_retriever.DataRetriever.get_result_info` (session,
        machine name, use case, core/thread counts) with the following
        AMD-specific fields:

        * ``"System"`` — system/hostname string.
        * ``"# of sockets"`` — number of physical sockets.
        * ``"# of ccds"`` — number of CCDs.
        * ``"# of ccxs"`` — number of CCXs.
        * ``"# of cores"`` — total physical cores.
        * ``"# of threads"`` — total hardware threads.
        * ``"# of threads sharing L3"`` — threads per L3 slice.
        * ``"Core p0 state freq"`` — peak core frequency (MHz).
        * ``"Multiplex interval for core"`` — PMC multiplex interval (ms).
        * ``"Multiplex interval for df"`` — DF multiplex interval (ms).
        * ``"Multiplex interval for l3"`` — L3 multiplex interval (ms).
        * ``"Measured df frequency"`` — measured Data Fabric frequency (MHz).
        * ``"Multiplex interval"`` — general multiplex interval (ms).
        * ``"Version"`` — AMD uProf tool version.

        :param repetition_ids: Mapping produced by
            :meth:`~quare.data_retriever.DataRetriever.get_repetitions`.
        :type repetition_ids: RepetitionIDs
        :returns: Merged metadata dictionary, or ``{}`` if no AMD hardware
            info is available for any of the provided repetitions.
        :rtype: dict[str, str]
        """
        super_result_info: dict[str, str] = super().get_result_info(repetition_ids)
        for size_repetition_ids in repetition_ids.values():
            for repetition_id in size_repetition_ids:
                stmt = (
                    select(
                        AMDuProfPCM_machine_info,
                        AMDuProfPCM_further_machine_info,
                    )
                    .where(AMDuProfPCM_machine_info.repetition == repetition_id)
                    .join(
                        AMDuProfPCM_further_machine_info,
                        AMDuProfPCM_machine_info.repetition
                        == AMDuProfPCM_further_machine_info.repetition,
                    )
                )
                row = self._db_session.execute(stmt).first()
                if row:
                    result_info = {
                        "System": row[0].system,
                        "# of sockets": row[0].num_of_sockets,
                        "# of ccds": row[0].num_of_ccds,
                        "# of ccxs": row[0].num_of_ccxs,
                        "# of cores": row[0].num_of_cores,
                        "# of threads": row[0].num_of_threads,
                        "# of threads sharing L3": row[0].num_of_threads_sharing_l3,
                        "Core p0 state freq": row[1].core_p0_state_freq,
                        "Multiplex interval for core": row[
                            1
                        ].multiplex_interval_for_core,
                        "Multiplex interval for df": row[1].multiplex_interval_for_df,
                        "Multiplex interval for l3": row[1].multiplex_interval_for_l3,
                        "Measured df frequency": row[1].measured_df_frequency,
                        "Multiplex interval": row[1].multiplex_interval,
                        "Version": row[1].version,
                    }
                    return super_result_info | result_info
        return {}
