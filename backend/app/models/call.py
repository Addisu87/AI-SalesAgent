from pydantic import BaseModel


class StartCall(BaseModel):
    customer_name: str = "Valued Customer"
    customer_phoneNumber: str = ""
    customer_businessDetails: str = "No details provided."
