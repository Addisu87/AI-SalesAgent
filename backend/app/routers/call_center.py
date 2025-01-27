import json
import logging
import os
import uuid

import redis
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status, Query
from fastapi.responses import FileResponse, JSONResponse
from twilio.rest import Client
from twilio.twiml.voice_response import Gather, VoiceResponse
from werkzeug.utils import secure_filename

from app.core.config import config
from app.helpers.ai_helpers import (
    clean_response,
    delayed_delete,
    initiate_inbound_message,
    process_inbound_message,
    process_message,
)
from app.helpers.audio_helpers import save_audio_file, text_to_speech
from app.models.call import StartCall
from app.prompts.conversation_stages import determine_stage

router = APIRouter()


logger = logging.getLogger(__name__)
redis_client = redis.Redis(
    host="localhost",
    port=6379,
    db=0,
    decode_responses=True,
)


app_public_url = config.APP_PUBLIC_URL
account_sid = config.TWILIO_ACCOUNT_SID
auth_token = config.TWILIO_AUTH_TOKEN
client = Client(account_sid, auth_token)


# Routes
@router.get("/audio/{filename}")
async def serve_audio(filename: str, background_tasks: BackgroundTasks):
    """Serve audio file from directory."""
    directory = "audio_files"
    full_path = os.path.join(directory, filename)
    if os.path.exists(full_path):
        # Schedule the file deletion in the background
        background_tasks.add_task(delayed_delete, full_path)
        return FileResponse(full_path)
    else:
        logger.error(f"Audio file not found: {filename}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Audio file not found"
        )


def get_audio_url(request: Request, filename: str) -> str:
    audio_url = router.url_path_for("serve_audio", filename=secure_filename(filename))
    return str(str(request.base_url).rstrip("/") + audio_url)


@router.post("/start-call")
async def start_call(request: StartCall, request_context: Request):
    """Endpoint to initiate a call."""
    logger.info("Request received")
    unique_id = str(uuid.uuid4())
    message_history = []

    # Extract fields directly from the StartCall model
    customer_name = request.customer_name
    customer_phone_number = request.customer_phoneNumber
    customer_business_details = request.customer_businessDetails

    # Start with the first inbound conversation stage
    current_stage = 1

    # Generate the initial AI response
    ai_message = await process_inbound_message(
        customer_name, customer_business_details, current_stage
    )

    # Clean the response (ensure it's a string)
    initial_message = clean_response(ai_message)

    # Convert AI message to speech
    audio_data = text_to_speech(initial_message)
    audio_file_path = save_audio_file(audio_data)
    audio_filename = os.path.basename(audio_file_path)

    # Update message history with the first conversation interaction
    initial_transcript = (
        f"Customer Name: {customer_name}. "
        f"Customer's business details: {customer_business_details}"
    )
    message_history.extend(
        [
            {"role": "user", "content": initial_transcript},
            {"role": "assistant", "content": initial_message},
        ]
    )

    # Store the message history in Redis
    redis_client.set(unique_id, json.dumps(message_history))

    # Generate audio URL
    audio_url = get_audio_url(request_context, audio_filename)

    # Log for debugging
    logger.debug(f"Audio URL generated: {audio_url}")

    # Twilio response
    response = VoiceResponse()
    response.play(audio_url)

    # Redirect to gather input for the next stage of the conversation
    redirect_url = f"{app_public_url}/gather?CallSid={unique_id}"
    response.redirect(redirect_url)

    # Initiate the call using Twilio API
    call = client.calls.create(
        twiml=str(response),
        to=customer_phone_number,
        from_=config.TWILIO_PHONE_NUMBER,
        method="GET",
        status_callback=app_public_url + "/event",
        status_callback_method="POST",
    )

    return JSONResponse({"message": "Call initiated", "call_sid": call.sid})


@router.post("/gather", name="gather_input")
async def gather_input(call_sid: str = Query(..., alias="CallSid")):
    """Endpoint to gather customer speech input."""
    resp = VoiceResponse()
    process_speech_url = router.url_path_for("process_speech", CallSid=call_sid)
    gather = Gather(
        input="speech",
        action=process_speech_url,
        speechTimeout="auto",
        method="POST",
    )
    resp.append(gather)

    gather_url = router.url_path_for("gather_input", CallSid=call_sid)
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

    resp.play(get_audio_url(request, audio_filename))
    message_history.append({"role": "assistant", "content": agent_response})
    redis_client.set(unique_id, json.dumps(message_history))
    resp.redirect(request.url_for("gather_input", CallSid=call_sid))
    return str(resp)


@router.post("/process-speech")
async def process_speech(request: Request):
    """Process customer's speech input and generates a response."""
    try:
        # Extract speech input and CallSid
        form = await request.form()
        speech_result = form.get("SpeechResult", "").strip()  # type: ignore
        call_sid = str(form.get("CallSid", "default_sid"))

        # Retrieve message history from Redis
        message_history_json = await redis_client.get(call_sid)
        message_history = (
            json.loads(message_history_json) if message_history_json else []
        )

        # Get current stage and determine stage type(inbound/outbound)
        current_stage = (
            message_history[-1].get("conversation_stage", 1) if message_history else 1
        )
        stage_type = "inbound" if "inbound" in call_sid.lower() else "outbound"

        # Update the stage based on user input
        updated_stage = determine_stage(stage_type, current_stage, speech_result)
        message_history.append(
            {
                "role": "user",
                "content": speech_result,
                "conversation_stage": updated_stage,
            }
        )

        # Generate AI response based on message history
        ai_response_text = await process_message(
            message_history, speech_result, current_stage, stage_type
        )
        response_text = clean_response(ai_response_text)

        # Convert AI response to audio and save the audio file
        audio_data = text_to_speech(response_text)
        audio_file_path = save_audio_file(audio_data)
        audio_filename = os.path.basename(audio_file_path)

        # Prepare Twillo VoiceResponse
        resp = VoiceResponse()
        resp.play(get_audio_url(request, audio_filename))

        # End the call if the conversation has ended
        if isinstance(ai_response_text, str) and "<END_OF_CALL>" in ai_response_text:
            logger.info("The conversation has ended.")
            resp.hangup()

        resp.redirect(request.url_for("gather_input", CallSid=call_sid))
        message_history.append({"role": "user", "content": speech_result})
        message_history.append(
            {"role": "assistant", "content": response_text, "stage": updated_stage}
        )
        redis_client.set(call_sid, json.dumps(message_history))
        return str(resp)

    except Exception as e:
        logger.error(f"Error processing speech: {e}")
        raise HTTPException(
            status_code=500, detail="An error occurred while processing speech."
        )


@router.post("/event")
async def event(request: Request):
    """Handle status callback from Twilio calls."""
    call_status = request.values.get("CallStatus", "")
    if call_status in ["completed", "busy", "failed"]:
        logger.info(f"Call completed with status: {call_status}")
    return JSONResponse(content={}, status_code=status.HTTP_204_NO_CONTENT)
