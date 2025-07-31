from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup # StatesGroup может быть удален, если нет других состояний

from app.keyboards.kbreply import main_menu_keyboard
from app.keyboards.kbinline import create_services_list_keyboard, single_service_details_keyboard, calendar_keyboard
from app.database import requests as db_requests
from config import BOOKINGS_PER_PAGE
from app.handlers.user.handler_appointment import BookingState # Импортируем BookingState для установки состояния

services_router = Router()

# --- Хэндлер для кнопки "ℹ️ Подробнее об услугах" ---
@services_router.message(F.text == "ℹ️ Подробнее об услугах")
async def handlerMoreAboutServices(message: Message, state: FSMContext):
    """
    Обрабатывает нажатие на кнопку "Подробнее об услугах".
    Отображает список всех доступных услуг.
    """
    # Очищаем состояние на всякий случай, если пользователь пришел из другого потока
    await state.clear()

    services = await db_requests.getServices()

    if not services:
        await message.answer("Извините, пока нет доступных услуг.", reply_markup=main_menu_keyboard)
        return

    await message.answer(
        "Наши услуги:\n\n"
        "Выберите услугу для просмотра деталей:",
        reply_markup=create_services_list_keyboard(services, 0, BOOKINGS_PER_PAGE)
    )

# --- Хэндлер для пагинации списка услуг ---
@services_router.callback_query(F.data.startswith("servicesPage_"))
async def handlerPaginateServices(callback: CallbackQuery):
    """
    Обрабатывает навигацию по страницам списка услуг.
    """
    page = int(callback.data.split("_")[1])

    services = await db_requests.getServices()

    # Обновляем сообщение с новой клавиатурой для пагинации
    await callback.message.edit_reply_markup(
        reply_markup=create_services_list_keyboard(services, page, BOOKINGS_PER_PAGE))
    await callback.answer()

# --- Хэндлер для просмотра деталей одной услуги ---
@services_router.callback_query(F.data.startswith("viewService_"))
async def handlerViewSingleService(callback: CallbackQuery, state: FSMContext):
    """
    Отображает подробную информацию о выбранной услуге.
    """
    service_id = int(callback.data.split("_")[1])

    service = await db_requests.getServiceById(service_id)

    if not service:
        await callback.answer("Услуга не найдена.", show_alert=True)
        # Если услуга не найдена, возвращаем к списку услуг
        all_services = await db_requests.getServices()
        # Здесь нет state для current_services_page, поэтому просто возвращаем на первую страницу
        await callback.message.edit_text("Услуга не найдена. Пожалуйста, выберите другую.",
                                         reply_markup=create_services_list_keyboard(all_services, 0, BOOKINGS_PER_PAGE))
        return

    service_info_text = (
        f"<b>{service.name}</b>\n\n"
        f"Описание: {service.description}\n"
        f"Цена: {service.price} руб.\n"
        f"Длительность: {service.duration_hours} час{'а' if 1 < service.duration_hours < 5 else ('ов' if service.duration_hours >= 5 else '')}\n"
    )

    # Отправляем детали услуги с клавиатурой для деталей
    await callback.message.edit_text(service_info_text, reply_markup=single_service_details_keyboard(service.id))
    await callback.answer()

# --- Хэндлер для возврата к списку услуг ---
@services_router.callback_query(F.data == "backToServicesList")
async def handlerBackToServicesList(callback: CallbackQuery):
    """
    Возвращает пользователя к списку услуг.
    """
    services = await db_requests.getServices()

    # Возвращаемся к первой странице списка услуг, так как состояние не сохранялось
    await callback.message.edit_text(
        "Наши услуги:\n\n"
        "Выберите услугу для просмотра деталей:",
        reply_markup=create_services_list_keyboard(services, 0, BOOKINGS_PER_PAGE)
    )
    await callback.answer()

# --- Хэндлер для записи на услугу из деталей услуги ---
@services_router.callback_query(F.data.startswith("bookService_"))
async def handlerBookServiceFromDetails(callback: CallbackQuery, state: FSMContext):
    """
    Обрабатывает нажатие кнопки "Записаться" из деталей услуги.
    Перенаправляет пользователя в процесс записи.
    """
    service_id = int(callback.data.split("_")[1])

    service = await db_requests.getServiceById(service_id)
    if not service:
        await callback.answer("Услуга не найдена. Пожалуйста, попробуйте снова.", show_alert=True)
        # Возвращаем к списку услуг
        all_services = await db_requests.getServices()
        await callback.message.edit_text("Услуга не найдена. Пожалуйста, выберите другую.",
                                         reply_markup=create_services_list_keyboard(all_services, 0,
                                                                                    BOOKINGS_PER_PAGE))
        return

    # Сохраняем выбранную услугу в FSMContext для процесса записи
    await state.update_data(chosenServiceId=service_id, chosenServiceName=service.name)

    # Переходим в состояние выбора даты из handler_appointment
    await callback.message.edit_text("Выберите дату для записи:", reply_markup=calendar_keyboard())
    await state.set_state(BookingState.choosingDate)  # Используем состояние из BookingState
    await callback.answer("Начинаем запись на выбранную услугу.")