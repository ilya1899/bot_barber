from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from .models import Base

engine = None
async_session_maker = None

async def init_db(database_url: str):
    global engine, async_session_maker
    if engine is None:
        engine = create_async_engine(database_url, echo=False)

        # Создание таблиц
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # ВАЖНО: использовать async_sessionmaker, а не sessionmaker
        async_session_maker = async_sessionmaker(
            bind=engine,
            expire_on_commit=False
        )
