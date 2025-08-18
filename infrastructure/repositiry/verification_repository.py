from sqlalchemy import select, update
from sqlalchemy.exc import NoResultFound
from infrastructure.repositiry.db_models import UserORM
from datetime import datetime, timedelta
import secrets
import logging



class VerificationRepository:
    def __init__(self, session):
        self.session = session

    async def verify_by_phone(self, user_id: int) -> bool:
        user = await self.session.execute(
            select(UserORM).where(UserORM.id == user_id)
        )
        user = user.scalar_one_or_none()

        if not user:
            return False

        # Обновляем данные пользователя
        await self.session.execute(
            update(UserORM)
            .where(UserORM.id == user_id)
            .values(
                phone_verified=True
            )
        )
        await self.session.commit()
        return True

    async def verify_by_admin(self, user_id: int) -> bool:
        user = await self.session.execute(
            select(UserORM).where(UserORM.id == user_id)
        )
        user = user.scalar_one_or_none()

        if not user:
            return False

        await self.session.execute(
            update(UserORM)
            .where(UserORM.id == user_id)
            .values(
                admin_verified=True,
            )
        )
        await self.session.commit()
        return True

    async def get_verification_status(self, user_id: int) -> dict:
        """
        Получает статус верификации пользователя
        :param user_id: ID пользователя
        :return: Словарь с статусами верификации
        """
        user = await self.session.execute(
            select(
                UserORM.phone_verified,
                UserORM.admin_verified,
                UserORM.email_verified
            ).where(UserORM.id == user_id)
        )
        user = user.first()

        if not user:
            raise NoResultFound("User not found")

        return {
            "phone_verified": user.phone_verified,
            "admin_verified": user.admin_verified
        }

    async def get_unverified_users(self) -> list:
        result = await self.session.execute(
            select(UserORM).where(
                (UserORM.phone_verified == False) |
                (UserORM.admin_verified == False)
            )
        )
        return result.scalars().all()
