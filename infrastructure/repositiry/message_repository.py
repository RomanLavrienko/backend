from infrastructure.repositiry.db_models import MessageORM
from sqlalchemy import select

class MessageRepository:
    def __init__(self, session):
        self.session = session

    async def get_by_chat(self, chat_id):
        result = await self.session.execute(select(MessageORM).where(MessageORM.chat_id == chat_id).order_by(MessageORM.created_at))
        return result.scalars().all()

    async def create_message(self, chat_id, sender_id, text, type=None, order_id=None, offer_price=None):
        message = MessageORM(chat_id=chat_id, sender_id=sender_id, text=text)
        if hasattr(message, 'type') and type:
            message.type = type
        if hasattr(message, 'order_id') and order_id is not None:
            message.order_id = order_id
        if hasattr(message, 'offer_price') and offer_price is not None:
            message.offer_price = offer_price
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        return message 