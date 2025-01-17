import os

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    SECRET_KY = os.getenv("SECRET_KEY")
    API_PUBLIC_URL = os.getenv("API_PUBLIC_URL")

    # Twilio API Credentials
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
    TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

    # OpenAI API Credentials
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    # Eleven Labs API Credentials
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
    VOICE_ID = os.getenv("VOICE_ID")

    # Company Details
    COMPANY_NAME = os.getenv("COMPANY_NAME")
    COMPANY_BUSINESS = os.getenv("COMPANY_BUSINESS")
    CONVERSATION_PURPOSE = os.getenv("CONVERSATION_PURPOSE")
    COMPANY_PRODUCTS_SERVICES = os.getenv("COMPANY_PRODUCTS_SERVICES")
    AISALESAGENT_NAME = os.getenv("AISALESAGENT_NAME")
