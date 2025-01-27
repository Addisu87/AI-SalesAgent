import logging

import httpx
from fastapi import APIRouter, HTTPException

from app.models.price_request import PriceRequest

# Logger Setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


router = APIRouter()


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
@router.post("/fetch-price")
async def fetch_price(request: PriceRequest):
    """Fetch price for a gym membership type."""
    url = "https://addisuhaile.app.n8n.cloud/webhook/membership"
    payload = {
        "membership_type": request.membership_type,
        "currency": request.currency,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()

            price_info = response.json()
            price = price_info.get("price")

            if price:
                return (
                    f"The price for {request.membership_type} membership is ${price}."
                )
            else:
                raise HTTPException(
                    status_code=404, detail="Price information not available."
                )
    except httpx.RequestError as e:
        logger.error(f"Error fetching price: {e}")
        raise HTTPException(
            status_code=500, detail="An error occurred while fetching the price."
        )
