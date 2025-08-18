from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel
from datetime import datetime
from domain.entity.userentity import User


class UserRegistrationDto(BaseModel):
    name: str
    nickname: str
    email: str
    password: str


class UserLoginDto(BaseModel):
    nickname: str
    password: str


class IUserRepository(ABC):
    @abstractmethod
    def register_user(self, user_data: UserRegistrationDto) -> User:
        """
        Регистрирует нового пользователя.

        Args:
            user_data: Данные для регистрации

        Returns:
            Зарегистрированный пользователь

        Raises:
            UserAlreadyExistsError: Если пользователь с таким nickname/email уже существует
        """
        pass

    @abstractmethod
    def login_user(self, user_data: UserLoginDto) -> tuple[bool, Optional[User]]:
        """
                Аутентифицирует пользователя и возвращает Bool для СЕРВИСА АУЕНТИФИКАЦИИ.

                Args:
                    user_data: Данные для входа (логин и пароль)

                Returns:
                    Tuple[success: bool, user: Optional[User]]

                Raises:
                    UserNotFoundError: Если пользователь не найден
                    InvalidPasswordError: Если пароль неверный
                    AccountLockedError: Если аккаунт заблокирован
                """
        pass


