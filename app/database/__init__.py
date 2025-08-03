from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from .models import Base

engine = None
_async_session_factory = None  # глобальная переменная с нужным именем

async def init_db(database_url: str):
    global engine, _async_session_factory
    if engine is None:
        engine = create_async_engine(database_url, echo=False)

        # Создание таблиц
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Инициализация фабрики сессий
        _async_session_factory = async_sessionmaker(
            bind=engine,
            expire_on_commit=False
        )