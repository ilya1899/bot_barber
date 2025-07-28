from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, date

from app.keyboards.kbreply import main_menu_keyboard
from app.keyboards.kbinline import menu_inline_button, calendar_keyboard, create_bookings_list_keyboard, \
    single_booking_details_keyboard
from app.database import requests as db_requests
from app.database.models import Booking
from app.handlers.user.handler_appointment import BookingState

my_bookings_router = Router()


class MyBookingsState(StatesGroup):
    viewingBookingsList = State()
    viewingSingleBooking = State()


@my_bookings_router.message(F.text == "🗓 Мои записи")
async def handler_my_bookings_list(message: Message, session_maker: callable, state: FSMContext):
    user_id = message.from_user.id
    async with session_maker() as session:
        bookings = await db_requests.get_user_bookings(session, user_id)

    if not bookings:
        await message.answer("У вас пока нет активных записей.", reply_markup=main_menu_keyboard)
        await state.clear()
        return

    future_bookings = sorted([b for b in bookings if b.booking_date >= datetime.now()], key=lambda x: x.booking_date)
    past_bookings = sorted([b for b in bookings if b.booking_date < datetime.now()], key=lambda x: x.booking_date,
                           reverse=True)

    sorted_bookings = future_bookings + past_bookings

    await state.update_data(all_user_bookings_ids=[b.id for b in sorted_bookings], current_bookings_page=0)

    await message.answer(
        "Ваши записи (сортировка по дате):\n\n"
        "Выберите запись для просмотра деталей:",
        reply_markup=create_bookings_list_keyboard(sorted_bookings, 0)
    )
    await state.set_state(MyBookingsState.viewingBookingsList)


@my_bookings_router.callback_query(MyBookingsState.viewingBookingsList, F.data.startswith("bookingsPage_"))
async def handler_paginate_bookings(callback: CallbackQuery, state: FSMContext, session_maker: callable):
    page = int(callback.data.split("_")[1])
    user_id = callback.from_user.id

    async with session_maker() as session:
        bookings = await db_requests.get_user_bookings(session, user_id)

    future_bookings = sorted([b for b in bookings if b.booking_date >= datetime.now()], key=lambda x: x.booking_date)
    past_bookings = sorted([b for b in bookings if b.booking_date < datetime.now()], key=lambda x: x.booking_date,
                           reverse=True)
    sorted_bookings = future_bookings + past_bookings

    await state.update_data(current_bookings_page=page)
    await callback.message.edit_reply_markup(reply_markup=create_bookings_list_keyboard(sorted_bookings, page))
    await callback.answer()


@my_bookings_router.callback_query(MyBookingsState.viewingBookingsList, F.data.startswith("viewBooking_"))
async def handler_view_single_booking(callback: CallbackQuery, state: FSMContext, session_maker: callable):
    booking_id = int(callback.data.split("_")[1])

    async with session_maker() as session:
        booking = await db_requests.get_booking_by_id(session, booking_id)

    if not booking or booking.user_id != callback.from_user.id:
        await callback.answer("Запись не найдена или у вас нет доступа.", show_alert=True)
        await callback.message.edit_text("Произошла ошибка. Возвращаемся в главное меню.",
                                         reply_markup=main_menu_keyboard)
        await state.clear()
        return

    service_name = booking.service.name if booking.service else "Неизвестная услуга"
    barber_name = booking.barber.name if booking.barber else "Любой мастер"
    booking_time_str = booking.booking_date.strftime('%d.%m.%Y %H:%M')

    booking_info_text = (
        f"<b>Информация о записи:</b>\n\n"
        f"Услуга: <b>{service_name}</b>\n"
        f"Мастер: <b>{barber_name}</b>\n"
        f"Дата и время: <b>{booking_time_str}</b>\n"
        f"Статус: <b>{booking.status}</b>\n"
    )

    await state.update_data(current_viewed_booking_id=booking_id)
    await callback.message.edit_text(booking_info_text, reply_markup=single_booking_details_keyboard(booking))
    await state.set_state(MyBookingsState.viewingSingleBooking)
    await callback.answer()


@my_bookings_router.callback_query(MyBookingsState.viewingSingleBooking, F.data.startswith("cancelSingleBooking_"))
async def handler_cancel_single_booking(callback: CallbackQuery, state: FSMContext, session_maker: callable):
    booking_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id

    async with session_maker() as session:
        booking = await db_requests.get_booking_by_id(session, booking_id)
        if not booking or booking.user_id != user_id:
            await callback.answer("Ошибка: запись не найдена или у вас нет доступа.", show_alert=True)
            await callback.message.edit_text("Произошла ошибка. Возвращаемся в главное меню.",
                                             reply_markup=main_menu_keyboard)
            await state.clear()
            return

        if booking.booking_date < datetime.now():
            await callback.answer("Нельзя отменить прошедшую запись.", show_alert=True)
            return

        success = await db_requests.cancel_booking(session, booking_id)

    if success:
        await callback.message.edit_text("✅ Запись отменена.")
    else:
        await callback.message.edit_text("Произошла ошибка при отмене записи. Пожалуйста, попробуйте позже.")

    await callback.message.answer("Вы вернулись в главное меню.", reply_markup=main_menu_keyboard)
    await state.clear()
    await callback.answer()


@my_bookings_router.callback_query(MyBookingsState.viewingSingleBooking, F.data.startswith("repeatBooking_"))
async def handler_repeat_booking(callback: CallbackQuery, state: FSMContext, session_maker: callable):
    booking_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id

    async with session_maker() as session:
        original_booking = await db_requests.get_booking_by_id(session, booking_id)
        if not original_booking or original_booking.user_id != user_id:
            await callback.answer("Ошибка: запись не найдена или у вас нет доступа.", show_alert=True)
            await callback.message.edit_text("Произошла ошибка. Возвращаемся в главное меню.",
                                             reply_markup=main_menu_keyboard)
            await state.clear()
            return

        await state.update_data(
            chosen_service_id=original_booking.service_id,
            chosen_service_name=original_booking.service.name,
            chosen_barber_id=original_booking.barber_id,
            chosen_barber_name=original_booking.barber.name if original_booking.barber else "Любой мастер"
        )

    await callback.message.edit_text("Выберите новую дату для повторной записи:", reply_markup=calendar_keyboard())
    await state.set_state(BookingState.choosingDate)
    await callback.answer("Начинаем повторную запись.")


@my_bookings_router.callback_query(MyBookingsState.viewingSingleBooking, F.data == "backToBookingsList")
async def handler_back_to_bookings_list(callback: CallbackQuery, state: FSMContext, session_maker: callable):
    user_id = callback.from_user.id
    async with session_maker() as session:
        bookings = await db_requests.get_user_bookings(session, user_id)

    current_page = (await state.get_data()).get('current_bookings_page', 0)

    await callback.message.edit_text(
        "Ваши записи (сортировка по дате):\n\n"
        "Выберите запись для просмотра деталей:",
        reply_markup=create_bookings_list_keyboard(bookings, current_page)
    )
    await state.set_state(MyBookingsState.viewingBookingsList)
    await callback.answer()