from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from infrastructure.repositiry.db_models import UserORM
from infrastructure.repositiry.base_repository import AsyncSessionLocal
from domain.entity.userentity import UserPrivate

class UserRepository:
    def __init__(self, session):
        self.session = session

    async def get_by_id(self, user_id):
        result = await self.session.execute(select(UserORM).where(UserORM.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_nickname(self, nickname):
        result = await self.session.execute(select(UserORM).where(UserORM.nickname == nickname))
        return result.scalar_one_or_none()

    async def get_by_email(self, email):
        result = await self.session.execute(select(UserORM).where(UserORM.email == email))
        return result.scalar_one_or_none()

    async def get_all(self):
        result = await self.session.execute(select(UserORM))
        return result.scalars().all()

    async def create(self, user: UserPrivate):
        from infrastructure.repositiry.db_models import UserORM
        user_orm = UserORM.from_entity(user)
        self.session.add(user_orm)
        await self.session.commit()
        await self.session.refresh(user_orm)
        return user_orm

    async def exists(self, nickname=None, email=None):
        if nickname:
            return await self.get_by_nickname(nickname) is not None
        if email:
            return await self.get_by_email(email) is not None
        return False 