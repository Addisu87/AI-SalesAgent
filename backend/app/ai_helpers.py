import json
import os

from core.config import Config
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from groq import Groq
from tools import tools_info

from app.utils.prompts import (
    AGENT_PROMPT_INBOUND_TEMPLATE,
    AGENT_STARTING_PROMPT_TEMPLATE,
)
from app.utils.stages import OUTBOUND_CONVERSATION_STAGES, STAGE_TOOL_ANAYLZING_PROMPT

router = APIRouter()

client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)


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
    response = client.chat.completions.create(
        model="gpt-4o-mini", messages=prompt, temperature=0.5, max_token=100
    )
    return response.choices[0].message.content


def is_tool_required(ai_output):
    try:
        data = json.loads(ai_output)
        return data.get("tool_required") == "yes"
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON format in AI output.")


def get_conversation_stage(ai_output):
    try:
        data = json.loads(ai_output)
        return int(data.get("conversation_stage_id"))
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON format in AI output.")


async def get_tool_details(ai_output):
    if not is_tool_required(ai_output):
        return None, None

    try:
        data = json.loads(ai_output)
        tool_name = data.get("tool_name")
        tool_parameters = data.get("tool_parameters")
        return tool_name, tool_parameters
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON format in AI output.")


@router.post("/process_initial_message")
async def process_initial_message(
    customer_name: str, customer_problem: str, config: dict = Depends(get_config)
):
    initial_prompt = AGENT_STARTING_PROMPT_TEMPLATE.format(
        salesperson_name=config["salesperson_name"],
        company_name=config["company_name"],
        company_business=config["company_business"],
        conversation_purpose=config["conversation_purpose"],
        conversation_stages=config["conversation_stages"],
    )

    message_to_send_to_ai = [{"role": "system", "content": initial_prompt}]
    initial_transcript = f"Customer Name: {customer_name}. Customer filled up details in the website: {customer_problem}"
    message_to_send_to_ai.append({"role": "user", "content": initial_transcript})

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

    intent_tool_prompt = STAGE_TOOL_ANAYLZING_PROMPT.format(
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
