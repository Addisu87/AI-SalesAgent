import json
import logging
import os
import threading
import time

from app.core.config import config
from app.helpers.tools_helpers import (
    appointment_availability,
    calendly_meeting,
    fetch_product_price,
    onsite_appointment,
    tools_info,
)
from app.prompts.agent_prompts import (
    AGENT_PROMPT_INBOUND_TEMPLATE,
    AGENT_PROMPT_OUTBOUND_TEMPLATE,
    STAGE_TOOL_ANALYZER_PROMPT,
)
from app.prompts.conversation_stages import ConversationStages, update_stage
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from groq import Groq

router = APIRouter()

logger = logging.getLogger(__name__)

client = Groq(api_key=config.GROQ_API_KEY)


# Utility Functions
def get_config():
    """Directly return config data as a dictionary."""
    return {
        "groq_api_key": config.GROQ_API_KEY,
        "salesperson_name": config.AISALESAGENT_NAME,
        "company_name": config.COMPANY_NAME,
        "company_business": config.COMPANY_BUSINESS,
        "conversation_purpose": config.CONVERSATION_PURPOSE,
        "company_products_services": config.COMPANY_PRODUCTS_SERVICES,
        "conversation_stages": ConversationStages,
    }


def gen_ai_output(prompt):
    """Generate AI response based on the provided prompt."""
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=prompt,
            temperature=0.5,
            max_tokens=150,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error generating AI output: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI generation error",
        )


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


# Route Handlers


async def initiate_inbound_message():
    config_dict = get_config()
    initial_prompt = AGENT_PROMPT_INBOUND_TEMPLATE.format(
        salesperson_name=config_dict["salesperson_name"],
        company_name=config_dict["company_name"],
    )
    return initial_prompt


async def process_inbound_message(
    customer_name: str,
    customer_problem: str,
):
    """Process the initial message for the customer."""
    config_dict = get_config()
    initial_prompt = AGENT_PROMPT_INBOUND_TEMPLATE.format(
        salesperson_name=config_dict["salesperson_name"],
        company_name=config_dict["company_name"],
        company_business=config_dict["company_business"],
        conversation_purpose=config_dict["conversation_purpose"],
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


async def invoke_stage_tool_analysis(message_history: list, user_input: str):
    config_dict = get_config()
    tools_description = "\n".join(
        [
            f"{tool['name']}: {tool['description']}"
            + (
                f" (Parameters: {', '.join([f'{k} - possible values: {v}' if isinstance(v, list) else f'{k} format' for k, v in tool.get('parameters', {}).items()])})"  # noqa: E501
                if tool.get("parameters")
                else ""
            )
            for tool in tools_info.values()
        ]
    )

    intent_tool_prompt = STAGE_TOOL_ANALYZER_PROMPT.format(
        salesperson_name=config_dict["salesperson_name"],
        company_name=config_dict["company_name"],
        company_business=config_dict["company_business"],
        conversation_purpose=config_dict["conversation_purpose"],
        conversation_stages=json.dumps(ConversationStages.INBOUND, indent=2),
        conversation_history=message_history,
        company_products_services=config_dict["company_products_services"],
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


async def process_message(
    message_history: list,
    user_input: str,
    current_stage: int,
    stage_type: str,
):
    config_dict = get_config()

    # Validate the current stage
    if current_stage < 1 or current_stage > len(ConversationStages.INBOUND):
        raise HTTPException(status_code=400, detail="Invalid current stage.")

    # Update stage based on user input
    new_stage = update_stage(stage_type, current_stage, user_input)

    # Proceed with the rest of the logic based on the updated stage
    stage_tool_output = await invoke_stage_tool_analysis(message_history, user_input)

    tool_output = ""
    try:
        if is_tool_required(stage_tool_output):
            tool_name, params = await get_tool_details(stage_tool_output)
            match tool_name:
                case "MeetingScheduler":
                    tool_output = await calendly_meeting()
                case "OnsiteAppointment":
                    tool_output = await onsite_appointment()
                case "GymAppointmentAvailability":
                    tool_output = await appointment_availability()
                case "PriceInquiry":
                    tool_output = await fetch_product_price(params)
                case _:
                    return JSONResponse(content={"response": ""})

            message_history.append({"role": "api_response", "content": tool_output})
    except ValueError:
        tool_output = (
            "Some Error occurred in calling the tools. "
            "Ask user if it's okay that you callback the user later with "
            "answer of the query"
        )

    inbound_prompt = AGENT_PROMPT_OUTBOUND_TEMPLATE.format(
        salesperson_name=config_dict["salesperson_name"],
        company_name=config_dict["company_name"],
        company_business=config_dict["company_business"],
        conversation_purpose=config_dict["conversation_purpose"],
        conversation_stage_id=new_stage,  # Updated stage
        company_products_services=config_dict["company_products_services"],
        conversation_stages=json.dumps(ConversationStages.OUTBOUND, indent=2),
        conversation_history=json.dumps(message_history, indent=2),
        tools_response=tool_output,
    )
    message_to_send_to_ai_final = [{"role": "system", "content": inbound_prompt}]
    message_to_send_to_ai_final.append({"role": "user", "content": user_input})

    try:
        talkback_response = gen_ai_output(message_to_send_to_ai_final)
        return JSONResponse(content={"response": talkback_response})
    except Exception as e:
        logger.error(f"Error generating AI response: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI generation error",
        )
