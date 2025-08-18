from domain.entity.userentity import UserPrivate
from typing import Optional

class AuthRepository:
    def __init__(self):
        # Здесь должна быть интеграция с БД
        self._users = {}  # временное хранилище: nickname -> UserPrivate

    def get_user_by_nickname(self, nickname: str) -> Optional[UserPrivate]:
        # Здесь должен быть запрос к БД
        return self._users.get(nickname)

    def save_token(self, nickname: str, token: str):
        user = self._users.get(nickname)
        if user:
            user.jwt_token = token
            # Здесь должна быть запись в БД

    def save_user(self, user: UserPrivate):
        self._users[user.nickname] = user
        # Здесь должна быть запись в БД