from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from enum import Enum

if TYPE_CHECKING:
    from userentity import UserExecutor, UserCustomer

class Priority(str, Enum):
    BASE = 'BASE'
    PREMIUM = 'PREMIUM'
    EXPRESS = 'EXPRESS'
    NEW = 'NEW'

class Status(str, Enum):
    OPEN = 'OPEN'
    CLOSE = 'CLOSE'
class Order(BaseModel):
    id: int
    name: str = Field(default="", max_length=30, min_length=1)
    description: str = Field(default="", max_length=250, min_length=1)
    price: int = Field(ge=400, le=400000)
    customer: UserCustomer
    responses: int   # отклики
    term: int = Field(ge=1, le=30)   # срок
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    executor: Optional[UserExecutor] = None
    category: list[str]
    priority: Priority = Priority.BASE
    status: Status = Status.OPEN

class CommissionSettingsEntity(BaseModel):
    id: int = 1
    commission_withdraw: float = 3.0
    commission_customer: float = 10.0
    commission_executor: float = 5.0
    commission_post_order: int = 200
    commission_response_threshold: int = 5000
    commission_response_percent: float = 1.0
