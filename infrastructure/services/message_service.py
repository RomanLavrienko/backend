from infrastructure.repositiry.message_repository import MessageRepository

class MessageService:
    def __init__(self, session):
        self.session = session
        self.message_repo = MessageRepository(session)

    async def get_messages_by_chat(self, chat_id):
        return await self.message_repo.get_by_chat(chat_id)

    async def send_message(self, chat_id, sender_id, text, type=None, order_id=None, offer_price=None):
        return await self.message_repo.create_message(chat_id, sender_id, text, type=type, order_id=order_id, offer_price=offer_price) 