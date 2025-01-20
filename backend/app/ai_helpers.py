from fastapi import session

from utils.stages import OUTBOUND_CONVERSATION_STAGES, INBOUND_CONVERSATION_STAGES

from tools import tools_info, onsite_appointment, fetch_product_price, calendly_meeting,  appointment_availablity
from groq import Groq