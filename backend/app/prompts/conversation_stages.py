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
            if stage_type.lower() == "inbound"
            else ConversationStages.OUTBOUND
        )
        try:
            return stages[current_stage + 1]
        except KeyError:
            return None  # No further stage


def determine_stage(stage_type: str, current_stage: int, user_input: str) -> int:
    """
    Determine the next conversation stage based on user input.

    Args:
        stage_type (str): 'inbound' or 'outbound'.
        current_stage (int): Current stage ID.
        user_input (str): User's latest input.

    Returns:
        int: Updated stage ID.
    """
    user_input = user_input.lower()

    if stage_type == "inbound":
        if "workout" in user_input:
            return 2  # Workout Recommendation
        elif "nutrition" in user_input or "diet" in user_input:
            return 3  # Nutrition Advice
        elif "form" in user_input or "technique" in user_input:
            return 4  # Technique & Form Guidance
        elif "motivation" in user_input or "struggling" in user_input:
            return 5  # Motivation & Follow-Up
    else:  # Outbound logic
        next_stage = ConversationStages.next_stage(stage_type, current_stage)
        return current_stage + 1 if next_stage else current_stage

    return current_stage
