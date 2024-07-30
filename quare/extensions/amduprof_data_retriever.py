from sqlalchemy import select

from ..plotter import DataRetriever
from .AMDuProfPCM_ext.models import (
    AMDuProfPCM_further_machine_info,
    AMDuProfPCM_machine_info,
)


class AMDuProfDataRetriever(DataRetriever):
    def get_result_info(self, repetition_ids: dict[str, list[int]]) -> dict[str, str]:
        """
        _summary_

        :param repetition_ids: _description_
        :return: _description_
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
