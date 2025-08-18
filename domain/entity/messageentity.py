from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class Message(BaseModel):
    id: int
    chat_id: int
    sender_id: int
    text: str
    type: Optional[str] = None
    created_at: datetime
    order_id: Optional[int] = None
    offer_price: Optional[int] = None 