from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup  # StatesGroup может быть удален, если нет других состояний

from app.keyboards.kbreply import main_menu_keyboard
from app.keyboards.kbinline import (
    create_services_list_keyboard,
    single_service_details_keyboard_with_nav,  # ИСПОЛЬЗУЕМ НОВУЮ ФУНКЦИЮ
    calendar_keyboard
)
from app.database import requests as db_requests
from config import BOOKINGS_PER_PAGE
from app.handlers.user.handler_appointment import BookingState  # Импортируем BookingState для установки состояния

services_router = Router()


# --- Хэндлер для кнопки "ℹ️ Подробнее об услугах" ---
@services_router.message(F.text == "ℹ️ Подробнее об услугах")
async def handlerMoreAboutServices(message: Message, state: FSMContext):
    """
    Обрабатывает нажатие на кнопку "Подробнее об услугах".
    Отображает детали первой доступной услуги с навигацией.
    """
    await state.clear()

    services = await db_requests.getServices()
    if not services:
        await message.answer("Извините, пока нет доступных услуг.", reply_markup=main_menu_keyboard)
        return

    # Получаем IDs всех услуг для навигации
    service_ids = [s.id for s in services]

    # Отображаем первую услугу
    first_service = services[0]
    next_service_id = service_ids[1] if len(service_ids) > 1 else None

    await send_service_details(message.answer, first_service, None, next_service_id)


# --- Хэндлер для просмотра деталей одной услуги (с навигацией) ---
@services_router.callback_query(F.data.startswith("showService_"))
async def handlerShowSingleServiceWithNav(callback: CallbackQuery):
    """
    Отображает подробную информацию о выбранной услуге и кнопки навигации.
    """
    service_id = int(callback.data.split("_")[1])
    services = await db_requests.getServices()

    service_ids = [s.id for s in services]
    try:
        current_index = service_ids.index(service_id)
        current_service = services[current_index]
        prev_service_id = service_ids[current_index - 1] if current_index > 0 else None
        next_service_id = service_ids[current_index + 1] if current_index < len(service_ids) - 1 else None

        await send_service_details(callback.message.edit_text, current_service, prev_service_id, next_service_id)
    except ValueError:
        await callback.answer("Услуга не найдена.", show_alert=True)

    await callback.answer()


async def send_service_details(
        send_method,
        service,
        prev_service_id: int,
        next_service_id: int
):
    """Вспомогательная функция для отправки деталей услуги."""
    # Формируем текст без лишних слов
    service_info_text = (
        f"<b>{service.name}</b>\n\n"
        f"{service.description}\n\n"
        f"<i>{service.price} руб.</i>\n"
        f"{service.duration_hours} час{'а' if 1 < service.duration_hours < 5 else ('ов' if service.duration_hours >= 5 else '')}"
    )

    await send_method(
        service_info_text,
        reply_markup=single_service_details_keyboard_with_nav(
            service.id,
            prev_service_id,
            next_service_id
        )
    )


# --- Хэндлер для записи на услугу из деталей услуги ---
@services_router.callback_query(F.data.startswith("bookService_"))
async def handlerBookServiceFromDetails(callback: CallbackQuery):
    """
    Обрабатывает нажатие кнопки "Записаться" из деталей услуги.
    Перенаправляет пользователя в процесс записи.
    """
    service_id = int(callback.data.split("_")[1])

    service = await db_requests.getServiceById(service_id)
    if not service:
        await callback.answer("Услуга не найдена. Пожалуйста, попробуйте снова.", show_alert=True)
        return

    # Переходим к календарю, передавая service_id
    await callback.message.edit_text(
        "Выберите дату для записи:",
        reply_markup=calendar_keyboard(service_id=service_id)
    )
    await callback.answer("Начинаем запись на выбранную услугу.")
