from pydantic import BaseModel


class AIOutput(BaseModel):
    ai_output: str


class InitialMessage(BaseModel):
    customer_name: str
    customer_problem: str
