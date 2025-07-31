# app/scheduler/jobs.py
from datetime import date, datetime, timedelta
from typing import List, Tuple, Optional

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError  # Для обработки ошибок отправки

from app.database import requests as db_requests # Не импортируем напрямую, а получаем через initialize_scheduler_dependencies

# Переменные для хранения зависимостей, которые будут инициализированы из run.py
_bot: Optional[Bot] = None
_db_requests = None  # Типизация будет сложной, так как это модуль, оставим None


# _admin_chat_id: Optional[str] = None # Больше не используется для этой функции, но может быть передан

def initialize_scheduler_dependencies(bot_instance: Bot, db_requests_module, admin_chat_id: Optional[str] = None):
    """
    Инициализирует зависимости (объект бота, модуль БД).
    admin_chat_id передается опционально, если нужен для других задач,
    но не используется в sendDailyReminders.
    Вызывается один раз при запуске приложения.
    """
    global _bot, _db_requests  # _admin_chat_id не делает глобальным здесь
    _bot = bot_instance
    _db_requests = db_requests_module
    # Если admin_chat_id понадобится для других админских уведомлений в этом модуле,
    # можно добавить: global _admin_chat_id; _admin_chat_id = admin_chat_id


async def sendDailyReminders():
    """
    Ежедневная запланированная задача для отправки индивидуальных напоминаний
    пользователям о их записях на текущий день.
    """
    # Проверяем, инициализированы ли все необходимые зависимости
    if _bot is None or _db_requests is None:
        print("Ошибка: Зависимости планировщика не инициализированы. Ежедневное напоминание не может быть отправлено.")
        return

    today = date.today()

    # Получаем все активные записи на текущий день
    # Эта функция уже загружает связанные объекты User, Service и Barber
    bookings_for_day = await db_requests.getBookingsForDate(today)

    if not bookings_for_day:
        print(f"На {today.strftime('%d.%m.%Y')} нет записей для отправки напоминаний.")
        # Опционально: можно отправить уведомление админу, что записей нет.
        # if _admin_chat_id: # Если _admin_chat_id был сохранен глобально
        #     try:
        #         await _bot.send_message(chat_id=_admin_chat_id, text=f"На {today.strftime('%d.%m.%Y')} нет записей.")
        #     except Exception as e:
        #         print(f"Ошибка при отправке уведомления админу об отсутствии записей: {e}")
        return

    print(
        f"Найдено {len(bookings_for_day)} записей на {today.strftime('%d.%m.%Y')}. Отправляем индивидуальные напоминания...")

    # Отправляем индивидуальные напоминания каждому пользователю
    for booking in bookings_for_day:
        # Получаем ID пользователя напрямую из объекта записи
        # Это работает, потому что booking.user - это объект User, связанный с данной записью
        user_id = booking.user.user_id
        service_name = booking.service.name if booking.service else "Услуга не указана"
        barber_name = booking.barber.name if booking.barber else "Любой мастер"
        booking_time = booking.booking_date.strftime('%H:%M')
        booking_date_str = booking.booking_date.strftime('%d.%m.%Y')

        reminder_text = f"""<b>🗓️ Напоминание о записи!</b>

Ваша запись на <b>{service_name}</b>
К мастеру: <b>{barber_name}</b>
На дату: <b>{booking_date_str}</b>
На время: <b>{booking_time}</b>

Мы ждем вас!"""

        try:
            await _bot.send_message(chat_id=user_id, text=reminder_text, parse_mode='HTML')
            print(f"Напоминание отправлено пользователю {user_id} о записи на {booking_date_str} {booking_time}")
        except TelegramForbiddenError:
            # Пользователь заблокировал бота
            print(f"Не удалось отправить напоминание пользователю {user_id}: бот заблокирован пользователем.")
            # Здесь можно добавить логику для пометки пользователя как неактивного
            # или удаления его из базы данных, чтобы избежать повторных ошибок.
        except TelegramBadRequest as e:
            # Другие ошибки Telegram API, например, неверный chat_id (очень редко для user_id из БД)
            print(f"Ошибка Telegram API при отправке напоминания пользователю {user_id}: {e}")
        except Exception as e:
            # Любые другие неожиданные ошибки
            print(f"Неизвестная ошибка при отправке напоминания пользователю {user_id}: {e}")

