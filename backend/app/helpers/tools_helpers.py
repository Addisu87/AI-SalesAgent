import logging

import httpx

# Logger Setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

tools_info = {
    "MeetingScheduler": {
        "name": "MeetingScheduler",
        "description": "Schedules a meeting using tools like Calendly.",
        "parameters": {
            "date": "YYYY-MM-DD",
            "time": "HH:MM",
            "timezone": "e.g., 'UTC'",
        },
    },
    "OnsiteAppointment": {
        "name": "OnsiteAppointment",
        "description": "Books an onsite appointment for the user.",
        "parameters": {"location": "string", "date": "YYYY-MM-DD", "time": "HH:MM"},
    },
    "GymAppointmentAvailability": {
        "name": "GymAppointmentAvailability",
        "description": "Checks gym appointment availability.",
        "parameters": {"date": "YYYY-MM-DD", "time_slot": "morning/afternoon/evening"},
    },
    "PriceInquiry": {
        "name": "PriceInquiry",
        "description": "Fetches the price for a specific membership type.",
        "parameters": {
            "membership_type": "Silver/Gold/Platinum",
            "currency": "USD/EUR",
        },
    },
}


async def onsite_appointment():
    return "Onsite appointment booked successfully."


async def calendly_meeting():
    return "Calendly meeting scheduled successfully."


async def appointment_availability():
    return "Gym appointment available on the specified date and time."


# Function to fetch product price from an API
async def fetch_product_price(membership_type):
    """Fetch price for a gym membership type using httpx."""
    if not membership_type:
        return "Error: Membership type is required."

    # Set up the endpoint and payload
    url = "https://addisuhaile.com/fetchMembership"
    payload = {
        "membership_type": membership_type,
        "currency": "USD",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()  # Will raise for non-2xx responses

            # Parse the JSON response to get the price
            price_info = response.json()
            price = price_info.get("price")

            # Return the price if available
            if price:
                return f"The price for {membership_type} is {price} USD."
            else:
                return f"Price information for {membership_type} is unavailable."
    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        logger.error(f"Error fetching price for {membership_type}: {e}")
        return "An error occurred while fetching membership price."
