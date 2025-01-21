# Gym-Specific Conversation Stages
class ConversationStages:
    INBOUND = {
        1: "Goal Identification",
        2: "Workout Recommendation",
        3: "Nutrition Advice",
        4: "Technique & Form Guidance",
        5: "Motivation & Follow-Up",
    }

    OUTBOUND = {
        1: "Lead Qualification",
        2: "Gym Tour Invitation",
        3: "Membership Discussion",
        4: "Closing Membership Sale",
    }

    @staticmethod
    def next_stage(stage_type: str, current_stage: int):
        """Get the next stage for inbound or outbound."""
        stages = (
            ConversationStages.INBOUND
            if stage_type == "inbound"
            else ConversationStages.OUTBOUND
        )
        try:
            return stages[current_stage + 1]
        except KeyError:
            return None  # No further stage


def update_stage(stage_type: str, current_stage: int, user_input: str) -> int:
    """Update the current stage based on user input."""
    if stage_type == "inbound":
        if "workout" in user_input.lower():
            return 2  # Workout Recommendation
        elif "nutrition" in user_input.lower():
            return 3  # Nutrition Advice
        elif "motivation" in user_input.lower() or "struggling" in user_input.lower():
            return 5  # Motivation & Follow-Up
        elif "form" in user_input.lower() or "technique" in user_input.lower():
            return 4  # Technique & Form Guidance
    else:  # Outbound logic
        return current_stage + 1  # Proceed to the next stage

    return current_stage  # Default: keep the current stage
