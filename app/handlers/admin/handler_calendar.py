# app/handlers/admin/handler_calendar.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import StateFilter  # Для объединения состояний
from datetime import date, datetime, timedelta
from typing import List, Tuple, Optional

from app.keyboards.kbreply import admin_menu_keyboard
from app.keyboards.kbinline import adminCalendarKeyboard, adminDayBookingsKeyboard  # Импортируем новую клавиатуру
from app.database import requests as db_requests

admin_calendar_router = Router()


# --- Состояния для календаря админа ---
class AdminCalendarState(StatesGroup):
    """Состояния FSM для навигации по календарю и просмотра записей."""
    waitingForDateSelection = State()
    viewingBookingsForDate = State()


# --- Главное меню Календаря ---
@admin_calendar_router.message(F.text == "Календарь")
async def handlerAdminCalendarMenu(message: Message, state: FSMContext):
    """
    Отображает календарь для выбора даты просмотра записей.
    """
    if not await db_requests.isUserAdmin(message.from_user.id):
        await message.answer("У вас нет прав для выполнения этого действия.")
        return

    await state.clear()  # Очищаем любое предыдущее состояние
    await message.answer(
        """Выберите дату для просмотра записей:""",
        reply_markup=adminCalendarKeyboard()  # По умолчанию покажет текущий месяц, только будущие даты
    )
    await state.set_state(AdminCalendarState.waitingForDateSelection)


@admin_calendar_router.callback_query(F.data == "adminBackToAdminMenuFromCalendar")
async def handlerAdminBackToAdminMenuFromCalendar(callback: CallbackQuery, state: FSMContext):
    """
    Возвращает администратора в главное меню админ-панели из раздела календаря.
    """
    if not await db_requests.isUserAdmin(callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        return

    await state.clear()
    await callback.message.edit_text("Вы вернулись в главное меню админ-панели.")
    await callback.message.answer("Добро пожаловать в админ-панель!", reply_markup=admin_menu_keyboard)
    await callback.answer()


# --- Навигация и выбор даты в календаре ---
@admin_calendar_router.callback_query(
    AdminCalendarState.waitingForDateSelection,
    F.data.startswith("adminCalYear_") | F.data.startswith("adminCalMonth_") | F.data.startswith("adminCalDate_")
)
async def handlerAdminCalendarNavigationOrSelection(callback: CallbackQuery, state: FSMContext):
    """
    Единый хэндлер для навигации по календарю и выбора даты.
    """
    if not await db_requests.isUserAdmin(callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        return

    user_data = await state.get_data()
    current_calendar_display_date: date = user_data.get('calendar_display_date', date.today())

    action_data = callback.data.split("_")
    action_type = action_data[0]
    value = action_data[1]

    new_calendar_display_date = current_calendar_display_date  # По умолчанию текущая отображаемая дата

    if action_type == "adminCalYear":
        new_year = int(value)
        new_calendar_display_date = current_calendar_display_date.replace(year=new_year)
    elif action_type == "adminCalMonth":
        new_calendar_display_date = datetime.strptime(value, "%Y-%m").date()
    elif action_type == "adminCalDate":
        chosen_date = datetime.strptime(value, "%Y-%m-%d").date()

        if chosen_date < date.today():  # Нельзя выбрать прошедшую дату
            await callback.answer("Нельзя выбрать прошедшую дату. Пожалуйста, выберите сегодняшнюю или будущую дату.",
                                  show_alert=True)
            return

        await state.update_data(chosenCalendarDate=chosen_date)
        await displayDayBookings(callback.message, state)  # Отображаем записи за выбранный день
        await callback.answer()
        return  # Выходим, так как состояние изменилось

    await state.update_data(calendar_display_date=new_calendar_display_date)

    # Обновляем клавиатуру календаря с учетом новой отображаемой даты
    await callback.message.edit_reply_markup(reply_markup=adminCalendarKeyboard(new_calendar_display_date))
    await callback.answer()


@admin_calendar_router.callback_query(
    AdminCalendarState.viewingBookingsForDate,  # Состояние просмотра записей
    F.data == "adminBackToCalendarSelection"
)
async def handlerAdminBackToCalendarSelection(callback: CallbackQuery, state: FSMContext):
    """
    Возвращает администратора к выбору даты в календаре из просмотра записей.
    """
    if not await db_requests.isUserAdmin(callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        return

    user_data = await state.get_data()
    current_calendar_display_date = user_data.get('calendar_display_date', date.today())

    await state.update_data(chosenCalendarDate=None)  # Сбрасываем выбранную дату
    await callback.message.edit_text(
        """Выберите дату для просмотра записей:""",
        reply_markup=adminCalendarKeyboard(current_calendar_display_date)
    )
    await state.set_state(AdminCalendarState.waitingForDateSelection)
    await callback.answer()


# --- Вспомогательная функция для отображения записей за день ---
async def displayDayBookings(message: Message, state: FSMContext):
    """
    Формирует и отображает записи за выбранный день, сгруппированные по мастерам.
    """
    user_data = await state.get_data()
    chosen_date: date = user_data.get('chosenCalendarDate')

    if not chosen_date:
        await message.edit_text("Ошибка: Дата не выбрана. Пожалуйста, попробуйте снова.")
        await message.answer(
            """Выберите дату для просмотра записей:""",
            reply_markup=adminCalendarKeyboard()
        )
        await state.set_state(AdminCalendarState.waitingForDateSelection)
        return

    bookings_for_day = await db_requests.getBookingsForDate(chosen_date)

    if not bookings_for_day:
        bookings_text = f"""🗓️ Записи на <b>{chosen_date.strftime('%d.%m.%Y')}</b>:

Нет записей на эту дату."""
    else:
        bookings_text = f"""🗓️ Записи на <b>{chosen_date.strftime('%d.%m.%Y')}</b>:

"""
        # Группируем записи по мастерам
        bookings_by_barber = {}
        for booking in bookings_for_day:
            barber_name = booking.barber.name if booking.barber else "Без мастера"
            if barber_name not in bookings_by_barber:
                bookings_by_barber[barber_name] = []
            bookings_by_barber[barber_name].append(booking)

        for barber_name, bookings in bookings_by_barber.items():
            bookings_text += f"<b>Мастер: {barber_name}</b>\n"
            for booking in sorted(bookings, key=lambda b: b.booking_date):  # Сортируем по времени
                service_name = booking.service.name if booking.service else "Услуга не указана"
                booking_time = booking.booking_date.strftime('%H:%M')
                bookings_text += f"  - {booking_time} - {service_name} ({booking.service.price} руб.)\n"
            bookings_text += "\n"  # Пустая строка между мастерами

    await message.edit_text(
        bookings_text,
        reply_markup=adminDayBookingsKeyboard()  # Используем функцию клавиатуры
    )
    await state.set_state(AdminCalendarState.viewingBookingsForDate)