from infrastructure.repositiry.order_repository import OrderRepository
from infrastructure.repositiry.db_models import CommissionSettingsORM

class OrderService:
    def __init__(self, session):
        self.session = session
        self.order_repo = OrderRepository(session)

    async def get_order(self, order_id):
        return await self.order_repo.get_by_id(order_id)

    async def get_user_orders(self, user_id):
        return await self.order_repo.get_user_orders(user_id)

    async def increment_responses(self, order):
        await self.order_repo.increment_responses(order)

    async def add_favorite(self, user_id, order_id):
        return await self.order_repo.add_favorite(user_id, order_id)

    async def remove_favorite(self, user_id, order_id):
        return await self.order_repo.remove_favorite(user_id, order_id)

    async def get_favorites(self, user_id):
        return await self.order_repo.get_favorites(user_id)

    async def is_favorite(self, user_id, order_id):
        return await self.order_repo.is_favorite(user_id, order_id)

    async def get_commission_settings(self, session):
        settings = (await session.execute(
            CommissionSettingsORM.__table__.select().limit(1)
        )).first()
        if settings and hasattr(settings, '_mapping'):
            return settings._mapping
        return None

    async def set_commission_settings(self, session, **kwargs):
        settings = (await session.execute(
            CommissionSettingsORM.__table__.select().limit(1)
        )).first()
        if settings and hasattr(settings, '_mapping'):
            settings_id = settings._mapping['id']
            await session.execute(
                CommissionSettingsORM.__table__.update().where(CommissionSettingsORM.id == settings_id).values(**kwargs)
            )
        else:
            await session.execute(
                CommissionSettingsORM.__table__.insert().values(**kwargs)
            )
        await session.commit() 