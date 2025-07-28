from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext  # FSMContext остается, но для очистки state, если нужно
from aiogram.fsm.state import State, StatesGroup  # StatesGroup может быть удален, если нет других состояний

from app.keyboards.kbreply import main_menu_keyboard
from app.keyboards.kbinline import create_services_list_keyboard, single_service_details_keyboard, calendar_keyboard
from app.database import requests as db_requests
from config import BOOKINGS_PER_PAGE
from app.handlers.user.handler_appointment import BookingState

services_router = Router()



@services_router.message(F.text == "ℹ️ Подробнее об услугах")
async def handler_more_about_services(message: Message, state: FSMContext, session_maker: callable):
    # Очищаем состояние на всякий случай, если пользователь пришел из другого потока
    await state.clear()

    async with session_maker() as session:
        services = await db_requests.get_services(session)

    if not services:
        await message.answer("Извините, пока нет доступных услуг.", reply_markup=main_menu_keyboard)
        return

    await message.answer(
        "Наши услуги:\n\n"
        "Выберите услугу для просмотра деталей:",
        reply_markup=create_services_list_keyboard(services, 0, BOOKINGS_PER_PAGE)
    )


@services_router.callback_query(F.data.startswith("servicesPage_"))
async def handler_paginate_services(callback: CallbackQuery, session_maker: callable):
    # page передается прямо в callback_data
    page = int(callback.data.split("_")[1])

    async with session_maker() as session:
        services = await db_requests.get_services(session)

    # Обновляем сообщение с новой клавиатурой для пагинации
    await callback.message.edit_reply_markup(
        reply_markup=create_services_list_keyboard(services, page, BOOKINGS_PER_PAGE))
    await callback.answer()


@services_router.callback_query(F.data.startswith("viewService_"))
async def handler_view_single_service(callback: CallbackQuery, state: FSMContext, session_maker: callable):
    # service_id передается прямо в callback_data
    service_id = int(callback.data.split("_")[1])

    async with session_maker() as session:
        service = await db_requests.get_service_by_id(session, service_id)

    if not service:
        await callback.answer("Услуга не найдена.", show_alert=True)
        # Если услуга не найдена, возвращаем к списку услуг
        all_services = await db_requests.get_services(session)
        # Здесь нет state для current_services_page, поэтому просто возвращаем на первую страницу
        await callback.message.edit_text("Услуга не найдена. Пожалуйста, выберите другую.",
                                         reply_markup=create_services_list_keyboard(all_services, 0, BOOKINGS_PER_PAGE))
        return

    service_info_text = (
        f"<b>{service.name}</b>\n\n"
        f"Описание: {service.description}\n"
        f"Цена: {service.price} руб.\n"
    )

    # Отправляем детали услуги с клавиатурой для деталей
    await callback.message.edit_text(service_info_text, reply_markup=single_service_details_keyboard(service.id))
    await callback.answer()


@services_router.callback_query(F.data == "backToServicesList")
async def handler_back_to_services_list(callback: CallbackQuery, session_maker: callable):
    async with session_maker() as session:
        services = await db_requests.get_services(session)

    # Возвращаемся к первой странице списка услуг, так как состояние не сохранялось
    await callback.message.edit_text(
        "Наши услуги:\n\n"
        "Выберите услугу для просмотра деталей:",
        reply_markup=create_services_list_keyboard(services, 0, BOOKINGS_PER_PAGE)
    )
    await callback.answer()


@services_router.callback_query(F.data.startswith("bookService_"))
async def handler_book_service_from_details(callback: CallbackQuery, state: FSMContext, session_maker: callable):
    service_id = int(callback.data.split("_")[1])

    async with session_maker() as session:
        service = await db_requests.get_service_by_id(session, service_id)
        if not service:
            await callback.answer("Услуга не найдена. Пожалуйста, попробуйте снова.", show_alert=True)
            # Возвращаем к списку услуг
            all_services = await db_requests.get_services(session)
            await callback.message.edit_text("Услуга не найдена. Пожалуйста, выберите другую.",
                                             reply_markup=create_services_list_keyboard(all_services, 0,
                                                                                        BOOKINGS_PER_PAGE))
            return

    # Сохраняем выбранную услугу в FSMContext для процесса записи
    await state.update_data(chosen_service_id=service_id, chosen_service_name=service.name)

    # Переходим в состояние выбора даты из handler_appointment
    await callback.message.edit_text("Выберите дату для записи:", reply_markup=calendar_keyboard())
    await state.set_state(BookingState.choosingDate)  # Используем состояние из BookingState
    await callback.answer("Начинаем запись на выбранную услугу.")