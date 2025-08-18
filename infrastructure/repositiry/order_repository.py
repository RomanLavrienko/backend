from infrastructure.repositiry.db_models import OrderORM, FavoriteOrderORM
from sqlalchemy import select

class OrderRepository:
    def __init__(self, session):
        self.session = session

    async def get_by_id(self, order_id):
        result = await self.session.execute(select(OrderORM).where(OrderORM.id == order_id))
        return result.scalar_one_or_none()

    async def get_user_orders(self, user_id):
        result = await self.session.execute(select(OrderORM).where(OrderORM.customer_id == user_id))
        return result.scalars().all()

    async def increment_responses(self, order):
        order.responses = (order.responses or 0) + 1
        await self.session.commit()

    async def add_favorite(self, user_id, order_id):
        fav = await self.session.execute(select(FavoriteOrderORM).where(FavoriteOrderORM.user_id == user_id, FavoriteOrderORM.order_id == order_id))
        if fav.scalar_one_or_none():
            return  # уже в избранном
        favorite = FavoriteOrderORM(user_id=user_id, order_id=order_id)
        self.session.add(favorite)
        await self.session.commit()
        await self.session.refresh(favorite)
        return favorite

    async def remove_favorite(self, user_id, order_id):
        fav = await self.session.execute(select(FavoriteOrderORM).where(FavoriteOrderORM.user_id == user_id, FavoriteOrderORM.order_id == order_id))
        favorite = fav.scalar_one_or_none()
        if favorite:
            await self.session.delete(favorite)
            await self.session.commit()

    async def get_favorites(self, user_id):
        result = await self.session.execute(select(FavoriteOrderORM).where(FavoriteOrderORM.user_id == user_id))
        return result.scalars().all()

    async def is_favorite(self, user_id, order_id):
        fav = await self.session.execute(select(FavoriteOrderORM).where(FavoriteOrderORM.user_id == user_id, FavoriteOrderORM.order_id == order_id))
        return fav.scalar_one_or_none() is not None 