from pydantic import BaseModel


class UserInput(BaseModel):
    message_history: list
    user_input: str
