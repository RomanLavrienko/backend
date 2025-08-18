from abc import ABC, abstractmethod
from domain.entity.orderentity import Order, Priority
from domain.entity.userentity import UserExecutor
from datetime import datetime
from typing import Optional


class IOrderRepository(ABC):
    @abstractmethod
    def create(self, order: Order) -> tuple[bool, int, str]:  # (success, id, message)
        pass

    @abstractmethod
    def delete(self, order_id: int) -> tuple[bool, int, str]:
        pass

    @abstractmethod
    def get_by_id(self, order_id: int) -> Optional[Order]:
        pass

    @abstractmethod
    def start(self, order_id: int, executor: UserExecutor) -> tuple[bool, datetime, int, str]:
        pass

    @abstractmethod
    def close(self, order_id: int) -> tuple[bool, datetime, int, str]:
        pass

    @abstractmethod
    def cansel(self, order_id: int) -> tuple[bool, int, str]:  # отмена; (success, order_id, message)
        """проверяем есть ли вообще исполнитель"""
        pass

    @abstractmethod
    def set_priority(self, order_id: int, priority: Priority) -> tuple[bool, int, str]:
        pass
