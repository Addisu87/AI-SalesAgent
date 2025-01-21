import json
import logging
import os
import uuid

import redis
from fastapi import (
    APIRouter,
    BackgroundTasks,
    HTTPException,
    Request,
    status,
)
from fastapi.responses import FileResponse, JSONResponse
from twilio.rest import Client
from twilio.twiml.voice_response import Gather, VoiceResponse
from werkzeug.utils import secure_filename

from app.core.config import Config
from app.helpers.ai_helpers import (
    clean_response,
    delayed_delete,
    initiate_inbound_message,
    process_inbound_message,
    process_message,
)
from app.helpers.audio_helpers import (
    save_audio_file,
    text_to_speech,
)

router = APIRouter()


logger = logging.getLogger(__name__)
redis_client = redis.Redis(host="redis", port=6379, db=0, decode_responses=True)

app_public_url = os.environ["APP_PUBLIC_URL"]

account_sid = os.environ["TWILIO_ACCOUNT_SID"]
auth_token = os.environ["TWILIO_AUTH_TOKEN"]
client = Client(account_sid, auth_token)


# Routes
@router.get("/audio/{filename}")
async def serve_audio(
    filename: str, background_tasks: BackgroundTasks, request: Request
):
    """Serve audio file from directory."""
    directory = "audio_files"
    full_path = os.path.join(directory, filename)
    try:
        response = FileResponse(full_path)
        background_tasks.add_task(delayed_delete, full_path)
        return response
    except FileNotFoundError:
        logger.error(f"Audio file not found: {filename}")
        raise HTTPException(status_code=404, detail="Audio file not found")


@router.post("/start-call")
async def start_call(request: Request):
    """Endpoint to initiate a call."""
    logger.info("Request received")
    unique_id = str(uuid.uuid4())
    message_history = []
    data = await request.json()

    customer_name = data.get("customer_name", "Valued Customer")
    customer_phone_number = data.get("customer_phonenumber", "")
    customer_business_details = data.get(
        "customer_businessdetails", "No details provided."
    )

    # Call AI to generate the initial response.
    ai_message = await process_inbound_message(customer_name, customer_business_details)
    initial_message = clean_response(ai_message)
    audio_data = text_to_speech(initial_message)
    audio_file_path = save_audio_file(audio_data)
    audio_filename = os.path.basename(audio_file_path)

    # Update message history
    initial_transcript = f"Customer Name: {customer_name}. Customer's business details: {customer_business_details}"
    message_history.extend(
        [
            {"role": "user", "content": initial_transcript},
            {"role": "assistant", "content": initial_message},
        ]
    )

    redis_client.set(unique_id, json.dumps(message_history))

    response = VoiceResponse()
    audio_url = request.url_for("serve_audio", filename=audio_filename, _external=True)
    response.play(audio_url)

    gather_url = request.url_for("gather_input", _external=True, CallSid=unique_id)
    response.redirect(gather_url)

    call = client.calls.create(
        twiml=str(response),
        to=customer_phone_number,
        from_=Config.TWILIO_PHONE_NUMBER,
        method="GET",
        status_callback=app_public_url + "/event",
        status_callback_method="POST",
    )
    return JSONResponse({"message": "Call initiated", "call_sid": call.sid})


@router.post("/gather")
async def gather_input(request: Request):
    """Endpoint to gather customer speech input."""
    call_sid = request.query_params.get("CallSid", "default_sid")
    resp = VoiceResponse()
    process_speech_url = request.url_for(
        "process_speech", _external=True, CallSid=call_sid
    )
    gather = Gather(
        input="speech",
        action=process_speech_url,
        speechTimeout="auto",
        method="POST",
    )
    resp.append(gather)

    gather_url = request.url_for("gather_input", _external=True, CallSid=call_sid)
    resp.redirect(gather_url)
    return str(resp)


@router.get("/gather-inbound")
async def gather_input_inbound(call_sid: str, request: Request):
    """Gathers customer's speech input for both inbound and outbound calls."""
    resp = VoiceResponse()
    logger.info("Initializing for inbound call...")
    unique_id = str(uuid.uuid4())
    message_history = []
    agent_response = await initiate_inbound_message()
    audio_data = text_to_speech(agent_response)
    audio_file_path = save_audio_file(audio_data)
    audio_filename = os.path.basename(audio_file_path)

    resp.play(
        request.url_for(
            "serve_audio", filename=secure_filename(audio_filename), _external=True
        )
    )
    message_history.append({"role": "assistant", "content": agent_response})
    redis_client.set(unique_id, json.dumps(message_history))
    resp.redirect(request.url_for("gather_input", CallSid=call_sid))
    return str(resp)


@router.post("/process-speech")
async def process_speech(request: Request):
    """Process customer's speech input and generates a response."""
    speech_result = request.form.get("SpeechResult", "").strip()
    call_sid = request.args.get("CallSid", "default_sid")
    message_history_json = redis_client.get(call_sid)
    message_history = json.loads(message_history_json) if message_history_json else []

    ai_response_text = await process_message(message_history, speech_result)
    response_text = clean_response(ai_response_text)
    audio_data = text_to_speech(response_text)
    audio_file_path = save_audio_file(audio_data)
    audio_filename = os.path.basename(audio_file_path)

    resp = VoiceResponse()
    resp.play(
        request.url_for(
            "serve_audio",
            filename=secure_filename(audio_filename),
            CallSid=call_sid,
        )
    )
    if "<END_OF_CALL>" in ai_response_text:
        logger.info("The conversation has ended.")
        resp.hangup()

    resp.redirect(request.url_for("gather_input", CallSid=call_sid))
    message_history.append({"role": "user", "content": speech_result})
    message_history.append({"role": "assistant", "content": response_text})
    redis_client.set(call_sid, json.dumps(message_history))
    return str(resp)


@router.post("/event")
async def event(request: Request):
    """Handle status callback from Twilio calls."""
    call_status = request.form.get("CallStatus", "")
    if call_status in ["completed", "busy", "failed"]:
        logger.info(f"Call completed with status: {call_status}")
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT)
