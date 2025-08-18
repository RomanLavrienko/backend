from infrastructure.repositiry.chat_repository import ChatRepository
from infrastructure.repositiry.user_repository import UserRepository

class ChatService:
    def __init__(self, session):
        self.session = session
        self.chat_repo = ChatRepository(session)
        self.user_repo = UserRepository(self.session)

    async def get_user_chats(self, user_id):
        return await self.chat_repo.get_user_chats(user_id)

    async def get_chat(self, chat_id):
        return await self.chat_repo.get_by_id(chat_id)

    async def get_or_create_chat_between_users(self, customer_id, executor_id):
        return await self.chat_repo.get_or_create_between_users(customer_id, executor_id)

    async def get_chat_between_users(self, customer_id, executor_id):
        return await self.chat_repo.get_chat_between_users(customer_id, executor_id) 