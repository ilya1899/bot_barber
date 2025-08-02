from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from datetime import datetime

from app.keyboards.kbreply import main_menu_keyboard
from app.keyboards.kbinline import (
    calendar_keyboard,
    create_bookings_list_keyboard,
    single_booking_details_keyboard
)
from app.database import requests as db_requests
from app.handlers.user.handler_appointment import BookingState  # для повторной записи

my_bookings_router = Router()


@my_bookings_router.message(F.text == "🗓 Мои записи")
async def handler_my_bookings_list(message: Message):
    """
    Показывает список всех записей пользователя.
    """
    user_id = message.from_user.id
    bookings = await db_requests.getUserBookings(user_id)

    if not bookings:
        await message.answer(
            """У вас пока нет активных записей.""",
            reply_markup=main_menu_keyboard
        )
        return

    # Сортировка: будущие → прошедшие
    future_bookings = sorted(
        [b for b in bookings if b.booking_date >= datetime.now()],
        key=lambda x: x.booking_date
    )
    past_bookings = sorted(
        [b for b in bookings if b.booking_date < datetime.now()],
        key=lambda x: x.booking_date,
        reverse=True
    )
    sorted_bookings = future_bookings + past_bookings

    await message.answer(
        """Ваши записи (сортировка по дате):

Выберите запись для просмотра деталей:""",
        reply_markup=create_bookings_list_keyboard(sorted_bookings, 0)
    )


@my_bookings_router.callback_query(F.data.startswith("bookingsPage_"))
async def handler_paginate_bookings(callback: CallbackQuery):
    """
    Пагинация списка записей.
    """
    page = int(callback.data.split("_")[1])
    user_id = callback.from_user.id

    bookings = await db_requests.getUserBookings(user_id)

    future_bookings = sorted(
        [b for b in bookings if b.booking_date >= datetime.now()],
        key=lambda x: x.booking_date
    )
    past_bookings = sorted(
        [b for b in bookings if b.booking_date < datetime.now()],
        key=lambda x: x.booking_date,
        reverse=True
    )
    sorted_bookings = future_bookings + past_bookings

    await callback.message.edit_reply_markup(
        reply_markup=create_bookings_list_keyboard(sorted_bookings, page)
    )
    await callback.answer()


@my_bookings_router.callback_query(F.data.startswith("viewBooking_"))
async def handler_view_single_booking(callback: CallbackQuery):
    """
    Отображает детали выбранной записи.
    """
    booking_id = int(callback.data.split("_")[1])
    booking = await db_requests.getBookingById(booking_id)

    if not booking or booking.user.user_id != callback.from_user.id:
        await callback.answer("Запись не найдена или у вас нет доступа.", show_alert=True)
        await callback.message.edit_text(
            """Произошла ошибка. Возвращаемся в главное меню.""",
            reply_markup=main_menu_keyboard
        )
        return

    service_name = booking.service.name if booking.service else "Неизвестная услуга"
    barber_name = booking.barber.name if booking.barber else "Любой мастер"
    booking_time_str = booking.booking_date.strftime('%d.%m.%Y %H:%M')

    booking_info_text = f"""
<b>Информация о записи:</b>

Услуга: <b>{service_name}</b>
Мастер: <b>{barber_name}</b>
Дата и время: <b>{booking_time_str}</b>
Статус: <b>{booking.status}</b>
"""

    await callback.message.edit_text(
        booking_info_text,
        reply_markup=single_booking_details_keyboard(booking)
    )
    await callback.answer()


@my_bookings_router.callback_query(F.data.startswith("cancelSingleBooking_"))
async def handler_cancel_single_booking(callback: CallbackQuery):
    """
    Отмена выбранной записи.
    """
    booking_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id

    booking = await db_requests.getBookingById(booking_id)
    if not booking or booking.user.user_id != user_id:
        await callback.answer("Ошибка: запись не найдена или у вас нет доступа.", show_alert=True)
        await callback.message.edit_text(
            """Произошла ошибка. Возвращаемся в главное меню.""",
            reply_markup=main_menu_keyboard
        )
        return

    if booking.booking_date < datetime.now():
        await callback.answer("Нельзя отменить прошедшую запись.", show_alert=True)
        return

    success = await db_requests.cancelBooking(booking_id)
    if success:
        await callback.message.edit_text("""✅ Запись отменена.""")
    else:
        await callback.message.edit_text("""Произошла ошибка при отмене записи. Попробуйте позже.""")

    await callback.message.answer(
        """Вы вернулись в главное меню.""",
        reply_markup=main_menu_keyboard
    )
    await callback.answer()


@my_bookings_router.callback_query(F.data.startswith("repeatBooking_"))
async def handler_repeat_booking(callback: CallbackQuery, state):
    """
    Повторная запись — тут нужно FSM для выбора даты.
    """
    booking_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id

    original_booking = await db_requests.getBookingById(booking_id)
    if not original_booking or original_booking.user.user_id != user_id:
        await callback.answer("Ошибка: запись не найдена или у вас нет доступа.", show_alert=True)
        await callback.message.edit_text(
            """Произошла ошибка. Возвращаемся в главное меню.""",
            reply_markup=main_menu_keyboard
        )
        return

    # Тут вызываем календарь (пример)
    await state.set_state(BookingState.choose_date)
    await callback.message.edit_text(
        """Выберите дату для повторной записи:""",
        reply_markup=calendar_keyboard()
    )
    await callback.answer()
