import json
import logging
import os
import uuid

import redis
from core.config import Config
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, url_for
from fastapi.responses import FileResponse, JSONResponse
from twilio.rest import Client
from twilio.twiml.voice_response import Gather, VoiceResponse

from app.ai_helpers import (
    clean_response,
    delayed_delete,
    gen_ai_output,
    get_config,
    get_conversation_stage,
    get_tool_details,
    is_tool_required,
)
from app.audio_helpers import save_audio_file, text_to_speech
from app.utils.prompts import (
    AGENT_PROMPT_INBOUND_TEMPLATE,
    AGENT_STARTING_PROMPT_TEMPLATE,
    STAGE_TOOL_ANALYZER_PROMPT,
)
from app.utils.tools import tools_info

router = APIRouter()
logger = logging.getLogger(__name__)
redis_client = redis.Redis(host="redis", port=6379, db=0, decode_responses=True)
client = Client(Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN)


# Routes
@router.get("/audio/{filename}")
async def serve_audio(filename: str, background_tasks: BackgroundTasks):
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
    customer_phone_number = data.get("customer_phoneNumber", "")
    customer_business_details = data.get(
        "customer_businessDetails", "No details provided."
    )

    # Call AI to generate the initial response.
    ai_message = await process_initial_message(customer_name, customer_business_details)
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
    audio_url = url_for("serve_audio", filename=audio_filename, _external=True)
    response.play(audio_url)

    gather_url = url_for("gather_input", _external=True, CallSid=unique_id)
    response.redirect(gather_url)

    call = client.calls.create(
        twiml=str(response),
        to=customer_phone_number,
        from_=Config.TWILIO_PHONE_NUMBER,
        method="GET",
        status_callback=Config.APP_PUBLIC_EVENT_URL,
        status_callback_method="POST",
    )
    return JSONResponse({"message": "Call initiated", "call_sid": call.sid})


@router.post("/gather")
async def gather_input(request: Request):
    """Endpoint to gather customer speech input."""
    call_sid = request.query_params.get("CallSid", "default_sid")
    resp = VoiceResponse()
    process_speech_url = url_for("process_speech", _external=True, CallSid=call_sid)
    gather = Gather(
        input="speech",
        action=process_speech_url,
        speechTimeout="auto",
        method="POST",
    )
    resp.append(gather)

    gather_url = url_for("gather_input", _external=True, CallSid=call_sid)
    resp.redirect(gather_url)
    return str(resp)


@router.post("/process_initial_message")
async def process_initial_message(
    customer_name: str,
    customer_problem: str,
    config: dict = Depends(lambda: get_config()),
):
    """Process the initial message for the customer."""
    initial_prompt = AGENT_STARTING_PROMPT_TEMPLATE.format(
        salesperson_name=config["salesperson_name"],
        company_name=config["company_name"],
        company_business=config["company_business"],
        conversation_purpose=config["conversation_purpose"],
        conversation_stages=config["conversation_stages"],
    )

    message_to_send_to_ai = [
        {"role": "system", "content": initial_prompt},
        {
            "role": "user",
            "content": f"Customer Name: {customer_name}. Problem: {customer_problem}",
        },
    ]

    response = gen_ai_output(message_to_send_to_ai)
    return JSONResponse(content={"response": response})


@router.post("/invoke_stage_tool_analysis")
async def invoke_stage_tool_analysis(
    message_history: list, user_input: str, config: dict = Depends(get_config)
):
    tools_description = "\n".join(
        [
            f"{tool['name']}: {tool['description']}"
            + (
                f" (Parameters: {', '.join([f'{k} - possible values: {v}' if isinstance(v, list) else f'{k} format' for k, v in tool.get('parameters', {}).items()])})"
                if tool.get("parameters")
                else ""
            )
            for tool in tools_info.values()
        ]
    )

    intent_tool_prompt = STAGE_TOOL_ANALYZER_PROMPT.format(
        salesperson_name=config["salesperson_name"],
        company_name=config["company_name"],
        company_business=config["company_business"],
        conversation_purpose=config["conversation_purpose"],
        conversation_stages=config["conversation_stages"],
        conversation_history=message_history,
        company_products_services=config["company_products_services"],
        user_input=user_input,
        tools=tools_description,
    )
    message_to_send_to_ai = [{"role": "system", "content": intent_tool_prompt}]
    message_to_send_to_ai.append(
        {
            "role": "user",
            "content": "You must respond in the json format specified in system prompt",
        }
    )
    ai_output = gen_ai_output(message_to_send_to_ai)
    return JSONResponse(content={"ai_output": ai_output})


@router.post("/process_message")
async def process_message(
    message_history: list, user_input: str, config: dict = Depends(get_config)
):
    stage_tool_output = await invoke_stage_tool_analysis(
        message_history, user_input, config
    )
    stage = get_conversation_stage(stage_tool_output)
    tool_output = ""

    try:
        if is_tool_required(stage_tool_output):
            tool_name, params = await get_tool_details(stage_tool_output)
            match tool_name:
                case "MeetingScheduler":
                    tool_output = calendly_meeting()
                case "OnsiteAppointment":
                    tool_output = onsite_appointment()
                case "GymAppointmentAvailablitiy":
                    tool_output = appointment_availablitiy()
                case "PriceInquity":
                    tool_output = fetch_product_price(params)
                case _:
                    return JSONResponse(content={"response": ""})
            message_history.append({"role": "api_response", "content": tool_output})
    except ValueError:
        tool_output = "Some Error occurred in calling the tools. Ask user if it's okay that you callback the user later with answer of the query"

    inbound_prompt = AGENT_PROMPT_INBOUND_TEMPLATE.format(
        salesperson_name=config["salesperson_name"],
        company_name=config["company_name"],
        company_business=config["company_business"],
        conversation_purpose=config["conversation_purpose"],
        conversation_stage_id=stage,
        company_products_services=config["company_products_services"],
        conversation_stages=json.dumps(config["conversation_stages"], indent=2),
        conversation_history=json.dumps(message_history, indent=2),
        tools_response=tool_output,
    )
    message_to_send_to_ai_final = [{"role": "system", "content": inbound_prompt}]
    message_to_send_to_ai_final.append({"role": "user", "content": user_input})
    talkback_response = gen_ai_output(message_to_send_to_ai_final)
    return JSONResponse(content={"response": talkback_response})
