from __future__ import annotations
from pydantic import BaseModel, Field, computed_field
from enum import Enum
from typing import Optional, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from orderentity import Order


class ReviewType(str, Enum):
    EXECUTOR = "executor"
    CUSTOMER = "customer"


class Review(BaseModel):
    id: int
    type: ReviewType
    rate: int = Field(ge=1, le=5)
    text: str = Field(default="", max_length=150, min_length=1)
    response: Optional[str] = Field(default=None, max_length=100, min_length=1)
    sender: int  # отправитель
    recipient: int  # получатель
    created_at: datetime = Field(default_factory=datetime.now)


class User(BaseModel):
    id: int
    name: str = Field(..., min_length=2, max_length=15)
    nickname: str = Field(..., pattern='^[a-zA-Z0-9_]+$', min_length=4, max_length=10)
    specification: str = Field(default="", max_length=100, min_length=5)
    description: Optional[str] = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=datetime.now)
    photo: Optional[str] = None
    balance: float = 0.0
    phone_verified: bool = Field(default=False, description="Верификация по номеру телефона")
    admin_verified: bool = Field(default=False, description="Верификация администрацией")
    phone_number: Optional[str] = Field(default=None, pattern='^\+?[1-9]\d{1,14}$', description="Номер телефона в формате E.164")


class UserCustomer(User):  # заказчик
    orders: list[Order] = Field(default_factory=list)
    customer_rating: float = Field(0.0, ge=0.0, le=5.0)


class UserExecutor(User):   # исполнитель
    done_count: int = 0
    taken_count: int = 0
    tags: list[str] = Field(default_factory=list)
    executor_rating: float = Field(0.0, ge=0.0, le=5.0)
    taken_orders: list[Order] = Field(default_factory=list, exclude=True)

    @computed_field
    @property
    def taken(self) -> Optional[list[Order]]:
        """Возвращает список заказов ТОЛЬКО для текущего исполнителя."""
        return None  # По умолчанию скрыто для всех

    def get_own_taken(self) -> list[Order]:
        """
        Метод для явного доступа к своим заказам.
        """
        return self.taken_orders

    @property
    def success_rate(self) -> float:
        if self.done_count == 0:
            return 0.0
        return (self.taken_count / self.done_count) * 100


class UserFull(User):  # полные данные юзера
    executor_data: Optional[UserExecutor] = None
    customer_data: Optional[UserCustomer] = None
    reviews: list[Review] = Field(default_factory=list)
    photo: Optional[str] = None
    balance: float = 0.0


class UserPrivate(BaseModel):
    id: Optional[int] = None
    name: str
    nickname: str
    email: str
    password_hash: Optional[str] = None
    specification: str = ""
    description: Optional[str] = None
    created_at: datetime
    jwt_token: Optional[str] = None
    email_verified: bool = False
    last_login: Optional[datetime] = None
    customer_rating: float = 0.0
    executor_rating: float = 0.0
    done_count: int = 0
    taken_count: int = 0
    photo: Optional[str] = None
    balance: float = 0.0
    phone_number: Optional[str] = None
    phone_verified: bool = False
    admin_verified: bool = False
