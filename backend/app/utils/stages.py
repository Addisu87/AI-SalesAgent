class SalesStages:
    LEAD_QUALIFICATION = "lead_qualification"
    SALES_PITCH = "sales_pitch"
    NEGOTIATION = "negotiation"
    CLOSING = "closing"

    @staticmethod
    def next_stage(current_stage):
        stages = [
            SalesStages.LEAD_QUALIFICATION,
            SalesStages.SALES_PITCH,
            SalesStages.NEGOTIATION,
            SalesStages.CLOSING,
        ]
        try:
            return stages[stages.index(current_stage) + 1]
        except (ValueError, IndexError):
            return None
