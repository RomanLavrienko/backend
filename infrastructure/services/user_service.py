from infrastructure.repositiry.user_repository import UserRepository

class UserService:
    def __init__(self, session):
        self.session = session
        self.user_repo = UserRepository(session)

    async def get_user_by_id(self, user_id):
        return await self.user_repo.get_by_id(user_id)

    async def get_user_by_nickname(self, nickname):
        return await self.user_repo.get_by_nickname(nickname)

    async def get_user_by_email(self, email):
        return await self.user_repo.get_by_email(email)

    async def create_user(self, user):
        return await self.user_repo.create(user)

    async def exists(self, nickname=None, email=None):
        return await self.user_repo.exists(nickname=nickname, email=email)

    async def get_all_users(self):
        return await self.user_repo.get_all() 