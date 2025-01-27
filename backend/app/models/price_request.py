from pydantic import BaseModel


class PriceRequest(BaseModel):
    membership_type: str  # Required field
    currency: str = "USD"  # Defaults to USD
