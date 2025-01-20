from langchain_core.prompts import PromptTemplate

# Instantiation using from_template (recommended)
STAGE_TOOL_ANALYZER_PROMPT = PromptTemplate.from_template(
    """You are a sales assistant helping your sales agent to determine the next stage of conversation to move to when taking to a user and decide if a sales agent company has following Products:{company_products_services}.
    ===
    {conversation_history}
    Customer Says: {user_input}
    ===
    End of conversation history.
    
    
    Current Conversation stage is: {conversation_stage_id}
    Based on the latest user input and the conversation history, determine the next conversation stage.
    If the user input indicates interest in a product or service, move to the 'Product Discussion' stage.
    If the user input indicates a need for more information, move to the 'Information Gathering' stage.
    If the user input indicates readiness to purchase, move to the 'Purchase' stage.
    If the user input indicates no interest, move to the 'End Conversation' stage.
    Provide a brief explanation for the stage transition.
    """
)

STAGE_TOOL_ANALYZER_PROMPT.format(
    company_products_services=company_products_services,
    conversation_history=conversation_history,
    user_input=user_input,
    conversation_stage_id=conversation_stage_id,
)

# Instantiation using initializer
prompt = PromptTemplate(template="Say {foo}")
