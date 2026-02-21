# bot/db/database.py
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
import os

# MUHIM: database URL ni main.py bilan bir xil qilish uchun
# data.py dan DATABASE_URL ni import qilamiz
from bot.data import DATABASE_URL

engine = create_async_engine(
    DATABASE_URL, 
    echo=False,  # SQL loglarini kamaytirish uchun False qiling
    future=True,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if 'sqlite' in DATABASE_URL else {}
)

AsyncSessionLocal = async_sessionmaker(
    engine, 
    expire_on_commit=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

__all__ = ['engine', 'AsyncSessionLocal', 'get_db']