import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

# MariaDB async URI: 'mysql+aiomysql://user:password@host:port/dbname'
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+aiomysql://myuser:mypassword@localhost:3306/mydb")

engine = create_async_engine(DATABASE_URL, echo=True, future=True)
AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
Base = declarative_base()

class BaseRepository:
    def __init__(self):
        self._session = None

    async def get_session(self):
        if self._session is None:
            self._session = AsyncSessionLocal()
        return self._session

    async def close(self):
        if self._session:
            await self._session.close()
            self._session = None 