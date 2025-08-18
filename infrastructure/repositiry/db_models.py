from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Enum as SAEnum, func
from sqlalchemy.orm import Mapped
from infrastructure.repositiry.base_repository import Base
from domain.entity.userentity import UserPrivate
from datetime import datetime
from enum import Enum

class UserORM(Base):
    __tablename__ = "users"

    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = Column(String(15), nullable=False)
    nickname: Mapped[str] = Column(String(10), unique=True, nullable=False)
    email: Mapped[str] = Column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = Column(String(100), nullable=False)
    specification: Mapped[str] = Column(String(100), default="")
    description: Mapped[str] = Column(String(500), default=None)
    created_at: Mapped[datetime] = Column(DateTime, default=datetime.utcnow)
    jwt_token: Mapped[str] = Column(String(500), default=None)
    email_verified: Mapped[bool] = Column(Boolean, default=False)
    last_login: Mapped[datetime] = Column(DateTime, default=None)
    customer_rating: Mapped[float] = Column(Float, default=0.0)
    executor_rating: Mapped[float] = Column(Float, default=0.0)
    done_count: Mapped[int] = Column(Integer, default=0)
    taken_count: Mapped[int] = Column(Integer, default=0)
    photo: Mapped[str] = Column(String(255), nullable=True)
    balance: Mapped[float] = Column(Float, default=0.0)
    is_support: Mapped[bool] = Column(Boolean, default=False)

    @classmethod
    def from_entity(cls, user: UserPrivate) -> "UserORM":
        return cls(
            id=user.id,
            name=user.name,
            nickname=user.nickname,
            email=getattr(user, "email", None),
            password_hash=user.password_hash,
            specification=user.specification,
            description=user.description,
            created_at=user.created_at,
            jwt_token=user.jwt_token,
            email_verified=user.email_verified,
            last_login=user.last_login,
            customer_rating=getattr(user, "customer_rating", 0.0),
            executor_rating=getattr(user, "executor_rating", 0.0),
            done_count=getattr(user, "done_count", 0),
            taken_count=getattr(user, "taken_count", 0),
            photo=getattr(user, "photo", None),
            balance=getattr(user, "balance", 0.0),
            is_support=getattr(user, "is_support", False),
        )

    def to_entity(self) -> UserPrivate:
        return UserPrivate(
            id=self.id,
            name=self.name,
            nickname=self.nickname,
            email=self.email,
            specification=self.specification,
            description=self.description,
            created_at=self.created_at,
            password_hash=self.password_hash,
            jwt_token=self.jwt_token,
            email_verified=self.email_verified,
            last_login=self.last_login,
            customer_rating=self.customer_rating,
            executor_rating=self.executor_rating,
            done_count=self.done_count,
            taken_count=self.taken_count,
            photo=self.photo,
            balance=self.balance,
            is_support=self.is_support,
        )

class ChatORM(Base):
    __tablename__ = "chats"
    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    executor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Priority(str, Enum):
    BASE = 'BASE'
    PREMIUM = 'PREMIUM'
    EXPRESS = 'EXPRESS'
    NEW = 'NEW'

class Status(str, Enum):
    OPEN = 'OPEN'
    WORK = 'WORK'
    REVIEW = 'REVIEW'
    CLOSE = 'CLOSE'

class OrderORM(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(30), nullable=False)
    description = Column(String(250), nullable=False)
    price = Column(Integer, nullable=False)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    responses = Column(Integer, default=0)
    term = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, default=None)
    closed_at = Column(DateTime, default=None)
    executor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    priority = Column(SAEnum(Priority), default=Priority.BASE)
    status = Column(String(20), default='OPEN')
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False) 

class CategoryORM(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False) 

class MessageORM(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, ForeignKey("chats.id"))
    sender_id = Column(Integer, ForeignKey("users.id"))
    text = Column(String(1000))
    type = Column(String(20), default=None)  # тип сообщения: обычное, offer и т.д.
    created_at = Column(DateTime, default=func.now()) 
    order_id = Column(Integer, nullable=True)  # id заказа, если это offer
    offer_price = Column(Integer, nullable=True)  # цена оффера

class FavoriteOrderORM(Base):
    __tablename__ = "favorite_orders"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow) 

class ReviewORM(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(20), nullable=False)  # executor/customer
    rate = Column(Integer, nullable=False)
    text = Column(String(150), nullable=False)
    response = Column(String(100), nullable=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    recipient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow) 

class CommissionSettingsORM(Base):
    __tablename__ = "commission_settings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    commission_withdraw = Column(Float, default=3.0)  # %
    commission_customer = Column(Float, default=10.0)  # %
    commission_executor = Column(Float, default=5.0)  # %
    commission_post_order = Column(Integer, default=200)  # руб
    commission_response_threshold = Column(Integer, default=5000)  # руб
    commission_response_percent = Column(Float, default=1.0)  # %

    def to_entity(self):
        from domain.entity.orderentity import CommissionSettingsEntity
        return CommissionSettingsEntity(
            id=self.id,
            commission_withdraw=self.commission_withdraw,
            commission_customer=self.commission_customer,
            commission_executor=self.commission_executor,
            commission_post_order=self.commission_post_order,
            commission_response_threshold=self.commission_response_threshold,
            commission_response_percent=self.commission_response_percent
        )

    @classmethod
    def from_entity(cls, entity):
        return cls(
            id=entity.id,
            commission_withdraw=entity.commission_withdraw,
            commission_customer=entity.commission_customer,
            commission_executor=entity.commission_executor,
            commission_post_order=entity.commission_post_order,
            commission_response_threshold=entity.commission_response_threshold,
            commission_response_percent=entity.commission_response_percent
        ) 

class ContactRequestORM(Base):
    __tablename__ = "contact_requests"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)
    message = Column(String(1000), nullable=False)
    status = Column(String(20), default="pending")  # pending/answered
    created_at = Column(DateTime, default=datetime.utcnow)
    answered_at = Column(DateTime, nullable=True) 