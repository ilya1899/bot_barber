from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from .models import Base

engine = None
async_session_maker = None

async def init_db(database_url: str):
    global engine, async_session_maker
    if engine is None:
        engine = create_async_engine(database_url, echo=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async_session_maker = sessionmaker(
            engine, expire_on_commit=False, class_=AsyncSession
        )

