from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext
from domain.entity.userentity import UserPrivate
from infrastructure.repositiry.user_repository import UserRepository

ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    def __init__(self, secret_key: str, user_repo: UserRepository):
        self.secret_key = secret_key
        self.user_repo = user_repo

    def create_access_token(self, data: dict, expires_delta: timedelta):
        to_encode = data.copy()
        expire = datetime.utcnow() + expires_delta
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, self.secret_key, algorithm=ALGORITHM)

    def decode_token(self, token: str):
        return jwt.decode(token, self.secret_key, algorithms=[ALGORITHM])

    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    async def register(self, name: str, email: str, nickname: str, password: str, specification: str) -> UserPrivate:
        if await self.user_repo.exists(email, nickname):
            raise ValueError("Пользователь с таким email или nickname уже существует")
        password_hash = self.hash_password(password)
        user = UserPrivate(
            name=name,
            nickname=nickname,
            email=email,
            specification=specification,
            description=None,
            created_at=datetime.utcnow(),
            password_hash=password_hash,
            jwt_token=None,
            email_verified=False,
            last_login=None,
            customer_rating=0.0,
            executor_rating=0.0,
            done_count=0,
            taken_count=0,
        )
        return await self.user_repo.create(user)

    async def login(self, email: str, password: str) -> str:
        user = await self.user_repo.get_by_email(email)
        if not user or not self.verify_password(password, user.password_hash):
            raise ValueError("Неверный email или пароль")
        token = self.create_access_token({"sub": user.nickname}, timedelta(days=7))
        return token
