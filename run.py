import asyncio
import os
import logging
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

# Импорты для базы данных
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from app.database.models import Base  # Для создания таблиц
from app.database import requests as db_requests  # Импортируем наш модуль с запросами к БД
from app.database import _async_session_factory
# Импорты для APScheduler
from apscheduler.schedulers.asyncio import AsyncIOScheduler  # Новый импорт
from app.scheduler import jobs  # Новый импорт: модуль с запланированными задачами

# Импорты роутеров
from app.handlers.user import handler_start, handler_appointment, handler_my_bookings, handler_more_services, \
    handler_registration, handler_support
from app.handlers.admin import handler_services, handler_masters, handler_statistics, handler_calendar


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    load_dotenv()
    TOKEN = os.getenv('BOT_TOKEN')
    DATABASE_URL = os.getenv('DATABASE_URL')
    # ADMIN_CHAT_ID больше не нужен для напоминаний пользователям, но может быть нужен для других админских уведомлений
    # Если он вам больше нигде не нужен, можете удалить строку ниже
    ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')

    if not TOKEN:
        logger.critical("BOT_TOKEN не найден в файле .env. Выход.")
        return
    if not DATABASE_URL:
        logger.critical("DATABASE_URL не найден в файле .env. Выход.")
        return
    # Если ADMIN_CHAT_ID не нужен для других целей, этот блок можно удалить
    # if not ADMIN_CHAT_ID:
    #     logger.warning("ADMIN_CHAT_ID не найден в файле .env. Это может повлиять на некоторые админские уведомления, если они используются.")

    # --- Инициализация базы данных ---
    engine = None
    try:
        engine = create_async_engine(DATABASE_URL, echo=False)

        async_session_factory = async_sessionmaker(
            bind=engine,
            expire_on_commit=False,
            class_=AsyncSession
        )

        # Передаем созданную фабрику сессий в модуль с запросами
        db_requests.initialize_db_requests(async_session_factory)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Таблицы базы данных проверены/созданы.")

    except SQLAlchemyError as e:
        logger.critical(f"Ошибка подключения или инициализации базы данных SQLAlchemy: {e}. Выход.")
        if engine:
            await engine.dispose()
        return
    except Exception as e:
        logger.critical(f"Неизвестная ошибка при настройке базы данных: {e}. Выход.")
        if engine:
            await engine.dispose()
        return
    # --- Конец инициализации базы данных ---

    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
    dp = Dispatcher(storage=MemoryStorage())

    # --- Регистрация роутеров ---
    dp.include_router(handler_start.start_router)
    dp.include_router(handler_registration.registration_router)
    dp.include_router(handler_appointment.appointment_router)
    dp.include_router(handler_support.support_router)
    dp.include_router(handler_my_bookings.my_bookings_router)
    dp.include_router(handler_more_services.services_router)
    dp.include_router(handler_services.admin_router)
    dp.include_router(handler_masters.admin_masters_router)
    dp.include_router(handler_statistics.admin_statistics_router)
    dp.include_router(handler_calendar.admin_calendar_router)

    logger.info("Все роутеры зарегистрированы.")
    # --- Конец регистрации роутеров ---

    # --- Инициализация и запуск планировщика ---
    # Указываем часовой пояс, чтобы напоминания отправлялись в 8:00 по МСК
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

    # Передаем bot и db_requests в модуль jobs.
    # ADMIN_CHAT_ID можно передать, если он нужен для других админских уведомлений в jobs.py,
    # но для напоминаний пользователям он не используется.
    jobs.initialize_scheduler_dependencies(bot, db_requests, ADMIN_CHAT_ID)

    # Добавляем задачу: отправлять напоминания каждое утро в 8:00
    scheduler.add_job(jobs.sendDailyReminders, 'cron', hour=8, minute=0)
    logger.info("Запланирована ежедневная отправка напоминаний в 08:00 МСК.")
    scheduler.start()
    logger.info("Планировщик APScheduler запущен.")
    # --- Конец инициализации планировщика ---

    logger.info("Бот запускается...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logger.critical(f"Ошибка при запуске опроса бота: {e}")
    finally:
        logger.info("Бот остановлен. Закрываем соединения.")
        scheduler.shutdown()  # Остановка планировщика при завершении работы бота
        await bot.session.close()  # Закрываем сессию бота
        if engine:  # Закрываем движок SQLAlchemy
            await engine.dispose()
        logger.info("Соединения закрыты.")


if __name__ == '__main__':
    asyncio.run(main())

