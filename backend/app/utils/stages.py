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


# Initialize the conversation stage
conversation_stage = "Goal Identification"


# Function to update the stage
def update_stage(current_stage, user_input):
    if "workout" in user_input.lower():
        return "Workout Recommendation"
    elif "nutrition" in user_input.lower():
        return "Nutrition Advice"
    elif "motivation" in user_input.lower() or "struggling" in user_input.lower():
        return "Motivation & Follow-Up"
    elif "form" in user_input.lower() or "technique" in user_input.lower():
        return "Technique & Form Guidance"
    return current_stage  # Default: keep the current stage


# Update stage based on user input
conversation_stage = update_stage(conversation_stage, user_input)
