import requests

tools_info = {
    "MeetingScheduler": {
        "name": "MeetingScheduler",
        "description": (
            "Schedules a meeting with the user using an online calendar tool "
            "like Calendly."
        ),
        "parameters": {
            "date": "string in YYYY-MM-DD format",
            "time": "string in HH:MM format",
            "timezone": "string (e.g., 'UTC', 'PST', etc.)",
        },
    },
    "OnsiteAppointment": {
        "name": "OnsiteAppointment",
        "description": "Books an onsite appointment for the user.",
        "parameters": {
            "location": "string specifying the appointment location",
            "date": "string in YYYY-MM-DD format",
            "time": "string in HH:MM format",
        },
    },
    "GymAppointmentAvailability": {
        "name": "GymAppointmentAvailability",
        "description": "Checks the availability of gym appointments.",
        "parameters": {
            "date": "string in YYYY-MM-DD format",
            "time_slot": (
                "string indicating preferred time range "
                "(e.g., 'morning', 'afternoon', 'evening')"
            ),
        },
    },
    "PriceInquiry": {
        "name": "PriceInquiry",
        "description": "Fetches the price for a product or service.",
        "parameters": {
            "product_id": "string representing the unique identifier for the product",
            "currency": "string representing the currency code (e.g., 'USD', 'EUR')",
        },
    },
    "WorkoutPlanGenerator": {
        "name": "WorkoutPlanGenerator",
        "description": "Generates a customized workout plan for the user.",
        "parameters": {
            "goal": "string (e.g., 'weight loss', 'muscle gain')",
            "fitness_level": "string (e.g., 'beginner', 'intermediate', 'advanced')",
            "preferences": (
                "string describing exercise preferences "
                "(e.g., 'bodyweight', 'short workouts')"
            ),
        },
    },
    "NutritionAdvisor": {
        "name": "NutritionAdvisor",
        "description": (
            "Provides dietary advice or meal plans based on user preferences."
        ),
        "parameters": {
            "goal": "string (e.g., 'weight loss', 'muscle gain')",
            "diet_type": "string (e.g., 'vegetarian', 'keto', 'balanced')",
        },
    },
}


def onsite_appointment():
    return "Onsite appointment booked successfully."


def fetch_product_price(membership_type):
    # Set up the endpoint and headers
    url = "https://addisuhaile.com/fetchMembership"
    headers = {"Content-Type": "application/json"}

    #  Prepare the data payload with the membership type
    data = {"membership_type": membership_type}

    # Send a POST request to the API
    response = requests.post(url, headers=headers, json=data)

    # Check if the response is successful
    if response.status_code == 200:
        price_info = response.json()
        return f"The price for {membership_type} is {price_info.get('price')}."
    else:
        return "Failed to fetch price information."


def calendly_meeting():
    return "Calendly meeting scheduled successfully."


def appointment_availability():
    return "Gym appointment available on the specified date and time."
