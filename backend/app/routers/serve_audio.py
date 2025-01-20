import json
import logging
import os
import threading
import time
import uuid

import redis
from core.config import Config
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from twilio.rest import Client
from twilio.twiml.voice_response import Gather, VoiceResponse

router = APIRouter()

logger = logging.getLogger(__name__)

redis_client = redis.Redis(host="redis", port=6379, db=0, decode_responses=True)

client = Client(Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN)


def clean_response(unfiltered_response_text):
    # Remove specific substrings from the response text
    filtered_response_text = unfiltered_response_text.replace(
        "<END_OF_TURN>", ""
    ).replace("<END_OF_CALL>", "")

    return filtered_response_text


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


@router.get("/audio/{filename}")
async def serve_audio(filename: str):
    """Serve audio file from directory."""
    directory = "audio_files"
    full_path = os.path.join(directory, filename)
    try:
        response = FileResponse(full_path)
        delayed_delete(full_path)
        return response
    except FileNotFoundError:
        logger.error(f"Audio file not found: {filename}")
        raise HTTPException(status_code=404, detail="Audio file not found")


@router.post("/start-call")
async def start_call(request: Request):
    logger.info("Request received")
    """End point to initiate call."""
    unique_id = str(uuid.uuid4())
    message_history = []
    data = await request.json()
    customer_name = data.get("customer_name", "Valued Customer")
    customer_phoneNumber = data.get("customer_phoneNumber", "")
    customer_businessDetails = data.get(
        "customer_businessDetails", "No details provided."
    )

    # Call AI_Helpers with customer_name, customer_bussinessDetails to create the initial response and return it.
    ai_message = process_initial_message(customer_name, customer_businessDetails)
    initial_message = clean_response(ai_message)
    audio_data = text_to_speech(initial_message)
    audio_file_path = save_audio_file(audio_data)
    audio_filename = os.path.basename(audio_file_path)

    # Create message history session variable and store the message history [WIP: Enhance this session management]
    initial_transcript = (
        "Customer Name: "
        + customer_name
        + ". Customer's business Details as filled up in the website: "
        + customer_businessDetails
    )

    message_history.append({"role": "user", "content": initial_transcript})
    message_history.append({"role": "assistant", "content": initial_message})

    redis_client.set(unique_id, json.dumps(message_history))
    response = VoiceResponse()
    response.play(f"/audio/{audio_filename}")
    redirect_url = f"{Config.API_PUBLIC_GATHER_URL}?Callsid={unique_id}"
    response.redirect(redirect_url)
    call = client.calls.create(
        twiml=str(response),
        to=customer_phoneNumber,
        from_=Config.TWILIO_PHONE_NUMBER,
        method="GET",
        status_callback=Config.APP_PUBLIC_EVENT_URL,
        status_callback_method="POST",
    )
    return JSONResponse({"message": "Call initiated", "call_sid": call.sid})


@router.post("/gather")
async def gather_input(request: Request):
    """Endpoint to gather customer's speech input."""
    call_sid = request.query_params.get("CallSid", "default_sid")
    resp = VoiceResponse()
    gather = Gather(
        input="speech",
        action=f"/process-speech?CallSid={call_sid}",
        speechTimeout="auto",
        method="POST",
    )
    resp.append(gather)
    resp.redirect(f"/gather?CallSid={call_sid}")
    return str(resp)


@router.get("/gather-inbound")
def gather_input_inbound():
    """Gathers customer's speech input for both inbound and outbound calls."""
    resp = VoiceResponse()
    print("Initializing for inbound call...")
    unique_id = str(uuid.uuid4())
    session["conversation_stage_id"] = 1
    message_history = []
    agent_response = initiate_inbound_message()
    audio_data = text_to_speech(agent_response)
