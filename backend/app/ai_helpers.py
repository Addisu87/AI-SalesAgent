import json
import logging
import os
import threading
import time

from core.config import Config
from fastapi import APIRouter, HTTPException  # type: ignore
from groq import Groq

from app.utils.stages import OUTBOUND_CONVERSATION_STAGES

router = APIRouter()

logger = logging.getLogger(__name__)

client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)


# Utility Functions
def get_config():
    return {
        "openai_api_key": Config.OPENAI_API_KEY,
        "salesperson_name": Config.AISALESAGENT_NAME,
        "company_name": Config.COMPANY_NAME,
        "company_business": Config.COMPANY_BUSINESS,
        "conversation_purpose": Config.CONVERSATION_PURPOSE,
        "company_products_services": Config.COMPANY_PRODUCTS_SERVICES,
        "conversation_stages": OUTBOUND_CONVERSATION_STAGES,
    }


def gen_ai_output(prompt):
    """Generate AI response based on the provided prompt."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini", messages=prompt, temperature=0.5, max_tokens=100
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error generating AI output: {e}")
        raise HTTPException(status_code=500, detail="AI generation error")

    # Utility Functions


def clean_response(unfiltered_response_text):
    """Remove specific substrings from the response text."""
    return unfiltered_response_text.replace("<END_OF_TURN>", "").replace(
        "<END_OF_CALL>", ""
    )


def delayed_delete(filename, delay=5):
    """Delete the file after a specified delay in seconds."""

    def attempt_delete():
        time.sleep(delay)
        try:
            os.remove(filename)
            logger.info(f"Successfully deleted temporary audio file: {filename}")
        except Exception as error:
            logger.error(f"Error deleting temporary audio file: {filename} - {error}")

    thread = threading.Thread(target=attempt_delete)
    thread.start()


def is_tool_required(ai_output):
    """Check if a tool is required based on AI output."""
    try:
        data = json.loads(ai_output)
        return data.get("tool_required") == "yes"
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON format in AI output.")


def get_conversation_stage(ai_output):
    """Extract conversation stage from AI output."""
    try:
        data = json.loads(ai_output)
        return int(data.get("conversation_stage_id"))
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON format in AI output.")


async def get_tool_details(ai_output):
    """Extract tool details from AI output."""
    if not is_tool_required(ai_output):
        return None, None

    try:
        data = json.loads(ai_output)
        tool_name = data.get("tool_name")
        tool_parameters = data.get("tool_parameters")
        return tool_name, tool_parameters
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON format in AI output.")
