import asyncio
import os
import logging
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

from app import main_router
import app.database

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    load_dotenv()
    TOKEN = os.getenv('BOT_TOKEN')
    DATABASE_URL = os.getenv('DATABASE_URL')

    if not TOKEN:
        logger.error("BOT_TOKEN not found in .env file. Exiting.")
        return
    if not DATABASE_URL:
        logger.error("DATABASE_URL not found in .env file. Exiting.")
        return

    # Инициализация базы данных
    try:
        await app.database.init_db(DATABASE_URL)
        if app.database.async_session_maker is None:
            logger.error("async_session_maker was not initialized by init_db. Exiting.")
            return
    except Exception as e:
        # Это сообщение об ошибке оставлено, так как оно критично для запуска
        logger.error(f"Error initializing database: {e}. Exiting.")
        return

    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(main_router)

    dp['session_maker'] = app.database.async_session_maker

    logger.info("Bot starting...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logger.critical(f"Bot polling failed: {e}")
    finally:
        logger.info("Bot stopped.")

if __name__ == '__main__':
    asyncio.run(main())