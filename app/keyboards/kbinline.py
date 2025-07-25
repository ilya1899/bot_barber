# app/keyboards/kbInline.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import date, timedelta, datetime
from typing import List, Tuple
import calendar
from app.database.models import Service, Booking

BOOKINGS_PER_PAGE = 5


def services_keyboard(services: List[Service]):
    builder = InlineKeyboardBuilder()
    for service in services:
        builder.add(InlineKeyboardButton(text=service.name, callback_data=f"service_{service.id}"))
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main_menu"))
    return builder.as_markup()


def calendar_keyboard(current_date: date = None):
    if current_date is None:
        current_date = date.today()

    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text=f"« {current_date.year - 1}", callback_data=f"calendar_year_{current_date.year - 1}"),
        InlineKeyboardButton(text=f"{current_date.year}", callback_data="ignore"),
        InlineKeyboardButton(text=f"{current_date.year + 1} »", callback_data=f"calendar_year_{current_date.year + 1}")
    )
    builder.row(
        InlineKeyboardButton(text="« Предыдущий",
                             callback_data=f"calendar_month_{current_date.replace(day=1) - timedelta(days=1):%Y-%m}"),
        InlineKeyboardButton(text=f"{current_date.strftime('%B')}", callback_data="ignore"),
        InlineKeyboardButton(text="Следующий »",
                             callback_data=f"calendar_month_{current_date.replace(day=28) + timedelta(days=4):%Y-%m}")
    )

    weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    builder.row(*[InlineKeyboardButton(text=day, callback_data="ignore") for day in weekdays])

    first_day_of_month = current_date.replace(day=1)
    start_day_of_week = first_day_of_month.weekday()

    for _ in range(start_day_of_week):
        builder.add(InlineKeyboardButton(text=" ", callback_data="ignore"))

    num_days_in_month = (current_date.replace(month=current_date.month % 12 + 1, day=1) - timedelta(days=1)).day
    for day_num in range(1, num_days_in_month + 1):
        day = current_date.replace(day=day_num)
        callback_data = f"calendar_date_{day:%Y-%m-%d}"
        builder.add(InlineKeyboardButton(text=str(day_num), callback_data=callback_data))

    builder.adjust(7)

    builder.row(InlineKeyboardButton(text="❌ Пропустить...", callback_data="skip_date"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_services"))
    builder.row(InlineKeyboardButton(text="❌ Отменить заполнение", callback_data="cancel_form"))

    return builder.as_markup()


def time_slots_keyboard(available_times: list[str]):
    builder = InlineKeyboardBuilder()
    for time_slot in available_times:
        builder.add(InlineKeyboardButton(text=time_slot, callback_data=f"time_select_{time_slot}"))
    builder.adjust(4)
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_date_selection"))
    builder.row(InlineKeyboardButton(text="❌ Отменить заполнение", callback_data="cancel_form"))
    return builder.as_markup()


menu_inline_button = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="☰ Меню", callback_data="main_menu")]
    ]
)

continue_registration_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Продолжить", callback_data="continue_registration")]
    ]
)


def final_booking_card_keyboard():
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="✅ Записаться", callback_data="confirm_final_booking"))
    builder.add(InlineKeyboardButton(text="🗑️ Удалить", callback_data="delete_final_booking"))
    builder.adjust(2)
    return builder.as_markup()


def create_bookings_list_keyboard(bookings: List[Booking], page: int = 0):
    builder = InlineKeyboardBuilder()
    start_index = page * BOOKINGS_PER_PAGE
    end_index = start_index + BOOKINGS_PER_PAGE

    current_page_bookings = bookings[start_index:end_index]

    if not current_page_bookings and page > 0 and len(bookings) > 0:
        page = (len(bookings) - 1) // BOOKINGS_PER_PAGE
        start_index = page * BOOKINGS_PER_PAGE
        end_index = start_index + BOOKINGS_PER_PAGE
        current_page_bookings = bookings[start_index:end_index]

    for booking in current_page_bookings:
        service_name = booking.service.name if booking.service else "Услуга"
        barber_name = booking.barber.name if booking.barber else "Мастер"
        booking_time_str = booking.booking_date.strftime('%d.%m.%Y %H:%M')

        emoji = "✅" if booking.booking_date < datetime.now() else "🗓"

        button_text = f"{emoji} {service_name} ({booking_time_str})"
        builder.add(InlineKeyboardButton(text=button_text, callback_data=f"view_booking_{booking.id}"))

    builder.adjust(1)

    total_pages = (len(bookings) + BOOKINGS_PER_PAGE - 1) // BOOKINGS_PER_PAGE
    if total_pages > 1:
        pagination_row = []
        if page > 0:
            pagination_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"bookings_page_{page - 1}"))

        pagination_row.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="ignore"))

        if page < total_pages - 1:
            pagination_row.append(InlineKeyboardButton(text="➡️", callback_data=f"bookings_page_{page + 1}"))

        builder.row(*pagination_row)

    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main_menu"))
    return builder.as_markup()


def single_booking_details_keyboard(booking: Booking):
    builder = InlineKeyboardBuilder()
    if booking.booking_date >= datetime.now():
        builder.add(InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel_single_booking_{booking.id}"))
    else:
        builder.add(InlineKeyboardButton(text="🔄 Повторить запись", callback_data=f"repeat_booking_{booking.id}"))

    builder.row(InlineKeyboardButton(text="🔙 Назад к списку", callback_data="back_to_bookings_list"))
    builder.adjust(1)
    return builder.as_markup()


def get_final_booking_card_content(service_name: str, chosen_date: date, chosen_time: str, barber_name: str) -> Tuple[
    str, InlineKeyboardMarkup]:
    final_card_text = (
        f"<b>Итоговая карточка записи:</b>\n\n"
        f"Услуга: <b>{service_name}</b>\n"
        f"Дата: <b>{chosen_date.strftime('%d.%m.%Y')}</b>\n"
        f"Время: <b>{chosen_time}</b>\n"
        f"Мастер: <b>{barber_name}</b>\n\n"
        f"Проверьте, все ли верно?"
    )

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="✅ Записаться", callback_data="confirm_final_booking"))
    builder.add(InlineKeyboardButton(text="🗑️ Удалить", callback_data="delete_final_booking"))
    builder.adjust(2)

    return final_card_text, builder.as_markup()


def support_inline_keyboard(manager_username: str) -> InlineKeyboardMarkup:
    """
    Создает Inline-клавиатуру с кнопкой для связи с менеджером поддержки.
    :param manager_username: Юзернейм менеджера Telegram (без '@').
    """
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="💬 Написать менеджеру", url=f"https://t.me/{manager_username}"))
    builder.adjust(1)
    return builder.as_markup()