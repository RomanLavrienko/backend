from infrastructure.repositiry.db_models import ChatORM, UserORM
from sqlalchemy import select, or_

class ChatRepository:
    def __init__(self, session):
        self.session = session

    async def get_user_chats(self, user_id):
        result = await self.session.execute(
            select(ChatORM).where(or_(ChatORM.customer_id == user_id, ChatORM.executor_id == user_id))
        )
        return result.scalars().all()

    async def get_by_id(self, chat_id):
        result = await self.session.execute(select(ChatORM).where(ChatORM.id == chat_id))
        return result.scalar_one_or_none()

    async def get_or_create_between_users(self, customer_id, executor_id):
        user1, user2 = sorted([customer_id, executor_id])
        result = await self.session.execute(
            select(ChatORM).where(
                ChatORM.customer_id == user1,
                ChatORM.executor_id == user2
            )
        )
        chat = result.scalar_one_or_none()
        if chat:
            return chat
        chat = ChatORM(customer_id=user1, executor_id=user2)
        self.session.add(chat)
        await self.session.commit()
        await self.session.refresh(chat)
        return chat

    async def get_chat_between_users(self, customer_id, executor_id):
        result = await self.session.execute(
            select(ChatORM).where(
                ChatORM.customer_id == customer_id,
                ChatORM.executor_id == executor_id
            )
        )
        return result.scalar_one_or_none() 