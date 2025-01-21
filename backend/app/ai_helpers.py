import json
import logging
import os
import threading
import time

from core.config import Config
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from groq import Groq

from app.utils.prompts import (
    AGENT_PROMPT_INBOUND_TEMPLATE,
    GYM_AGENT_PROMPT,
    STAGE_TOOL_ANALYZER_PROMPT,
)
from app.utils.stages import conversation_stage
from app.utils.tools import (
    appointment_availability,
    calendly_meeting,
    fetch_product_price,
    onsite_appointment,
    tools_info,
)

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
        "conversation_stage": conversation_stage,
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


async def process_initial_message(
    customer_name: str,
    customer_problem: str,
    config: dict = Depends(lambda: get_config()),
):
    """Process the initial message for the customer."""
    initial_prompt = GYM_AGENT_PROMPT.format(
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
                    tool_output = appointment_availability()
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
