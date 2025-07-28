from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import date, timedelta, datetime
import calendar
from typing import List, Tuple
from app.database.models import Service, Booking, Barber
from config import BOOKINGS_PER_PAGE


def services_keyboard(services: List[Service]) -> InlineKeyboardMarkup:
    """Создает Inline-клавиатуру со списком услуг."""
    builder = InlineKeyboardBuilder()
    for service in services:
        builder.add(InlineKeyboardButton(text=service.name, callback_data=f"chooseService_{service.id}"))
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="backToMainMenu"))
    return builder.as_markup()


def calendar_keyboard(current_date: date = None) -> InlineKeyboardMarkup:
    """Создает Inline-клавиатуру календаря для выбора даты."""
    if current_date is None:
        current_date = date.today()

    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text=f"« {current_date.year - 1}", callback_data=f"navigateYear_{current_date.year - 1}"),
        InlineKeyboardButton(text=f"{current_date.year}", callback_data="ignore"),
        InlineKeyboardButton(text=f"{current_date.year + 1} »", callback_data=f"navigateYear_{current_date.year + 1}")
    )
    builder.row(
        InlineKeyboardButton(text="« Предыдущий",
                             callback_data=f"navigateMonth_{current_date.replace(day=1) - timedelta(days=1):%Y-%m}"),
        InlineKeyboardButton(text=f"{current_date.strftime('%B')}", callback_data="ignore"),
        InlineKeyboardButton(text="Следующий »",
                             callback_data=f"navigateMonth_{current_date.replace(day=28) + timedelta(days=4):%Y-%m}")
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
        callback_data = f"chooseDate_{day:%Y-%m-%d}"
        builder.add(InlineKeyboardButton(text=str(day_num), callback_data=callback_data))

    builder.adjust(7)

    builder.row(InlineKeyboardButton(text="❌ Пропустить...", callback_data="skipDate"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="backToServices"))
    builder.row(InlineKeyboardButton(text="❌ Отменить заполнение", callback_data="cancelForm"))

    return builder.as_markup()


def time_slots_keyboard(available_times: list[str]) -> InlineKeyboardMarkup:
    """Создает Inline-клавиатуру с доступными временными слотами."""
    builder = InlineKeyboardBuilder()
    for time_slot in available_times:
        builder.add(InlineKeyboardButton(text=time_slot, callback_data=f"chooseTime_{time_slot}"))
    builder.adjust(4)
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="backToDateSelection"))
    builder.row(InlineKeyboardButton(text="❌ Отменить заполнение", callback_data="cancelForm"))
    return builder.as_markup()


def barbers_keyboard(barbers: List[Barber]) -> InlineKeyboardMarkup:
    """Создает Inline-клавиатуру со списком мастеров."""
    builder = InlineKeyboardBuilder()
    for barber in barbers:
        builder.add(InlineKeyboardButton(text=barber.name, callback_data=f"chooseBarber_{barber.id}"))
    builder.add(InlineKeyboardButton(text="Любой мастер", callback_data="chooseBarber_any"))
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="backToTimeSelection"))
    builder.row(InlineKeyboardButton(text="❌ Отменить заполнение", callback_data="cancelForm"))
    return builder.as_markup()


menu_inline_button = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="☰ Меню", callback_data="mainMenu")]
    ]
)

continue_registration_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Продолжить", callback_data="continueRegistration")]
    ]
)


def final_booking_card_keyboard() -> InlineKeyboardMarkup:
    """Создает Inline-клавиатуру для подтверждения или отмены записи."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="✅ Записаться", callback_data="confirmBooking"))
    builder.add(InlineKeyboardButton(text="🗑️ Удалить", callback_data="deleteBooking"))
    builder.adjust(2)
    return builder.as_markup()


def get_final_booking_card_content(service_name: str, chosen_date: date, chosen_time: str, barber_name: str) -> Tuple[
    str, InlineKeyboardMarkup]:
    """Формирует текст и клавиатуру для итоговой карточки записи."""
    final_card_text = (
        f"<b>Итоговая карточка записи:</b>\n\n"
        f"Услуга: <b>{service_name}</b>\n"
        f"Дата: <b>{chosen_date.strftime('%d.%m.%Y')}</b>\n"
        f"Время: <b>{chosen_time}</b>\n"
        f"Мастер: <b>{barber_name}</b>\n\n"
        f"Проверьте, все ли верно?"
    )

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="✅ Записаться", callback_data="confirmBooking"))
    builder.add(InlineKeyboardButton(text="🗑️ Удалить", callback_data="deleteBooking"))
    builder.adjust(2)

    return final_card_text, builder.as_markup()


def create_bookings_list_keyboard(bookings: List[Booking], page: int = 0) -> InlineKeyboardMarkup:
    """Создает Inline-клавиатуру со списком записей пользователя с пагинацией."""
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

        emoji = "✅" if booking.booking_date < datetime.now() else "🗓"  # Эмодзи для прошедших/будущих записей

        button_text = f"{emoji} {service_name} ({booking_time_str})"
        builder.add(InlineKeyboardButton(text=button_text, callback_data=f"viewBooking_{booking.id}"))

    builder.adjust(1)

    total_pages = (len(bookings) + BOOKINGS_PER_PAGE - 1) // BOOKINGS_PER_PAGE
    if total_pages > 1:
        pagination_row = []
        if page > 0:
            pagination_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"bookingsPage_{page - 1}"))

        pagination_row.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="ignore"))

        if page < total_pages - 1:
            pagination_row.append(InlineKeyboardButton(text="➡️", callback_data=f"bookingsPage_{page + 1}"))

        builder.row(*pagination_row)

    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="backToMainMenu"))
    return builder.as_markup()


def single_booking_details_keyboard(booking: Booking) -> InlineKeyboardMarkup:
    """Создает Inline-клавиатуру для просмотра деталей одной записи."""
    builder = InlineKeyboardBuilder()
    if booking.booking_date >= datetime.now():
        builder.add(InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancelSingleBooking_{booking.id}"))
    else:
        builder.add(InlineKeyboardButton(text="🔄 Повторить запись", callback_data=f"repeatBooking_{booking.id}"))

    builder.row(InlineKeyboardButton(text="🔙 Назад к списку", callback_data="backToBookingsList"))
    builder.adjust(1)
    return builder.as_markup()


def create_services_list_keyboard(services: List[Service], current_page: int = 0,
                                  services_per_page: int = BOOKINGS_PER_PAGE) -> InlineKeyboardMarkup:
    """Создает Inline-клавиатуру со списком услуг для просмотра (пользовательская часть)."""
    builder = InlineKeyboardBuilder()

    start_index = current_page * services_per_page
    end_index = start_index + services_per_page

    services_on_page = services[start_index:end_index]

    for service in services_on_page:
        builder.button(text=service.name, callback_data=f"viewService_{service.id}")

    total_pages = (len(services) + services_per_page - 1) // services_per_page
    nav_buttons = []
    if current_page > 0:
        nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"servicesPage_{current_page - 1}"))
    else:
        nav_buttons.append(InlineKeyboardButton(text=" ", callback_data="ignore"))

    nav_buttons.append(InlineKeyboardButton(text=f"{current_page + 1}/{total_pages}", callback_data="ignore"))

    if current_page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"servicesPage_{current_page + 1}"))
    else:
        nav_buttons.append(InlineKeyboardButton(text=" ", callback_data="ignore"))

    builder.row(*nav_buttons)

    builder.row(
        InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="mainMenu")
    )

    return builder.as_markup()


def single_service_details_keyboard(service_id: int) -> InlineKeyboardMarkup:
    """Создает Inline-клавиатуру для просмотра деталей одной услуги (пользовательская часть)."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💈 Записаться на эту услугу", callback_data=f"bookService_{service_id}")
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад к услугам", callback_data="backToServicesList"),
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="mainMenu")
    )
    return builder.as_markup()


def support_inline_keyboard(manager_username: str) -> InlineKeyboardMarkup:
    """Создает Inline-клавиатуру для связи с менеджером поддержки."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="💬 Написать менеджеру", url=f"https://t.me/{manager_username}"))
    builder.adjust(1)
    return builder.as_markup()


# --- Admin Keyboards ---
def admin_services_menu_keyboard() -> InlineKeyboardMarkup:
    """Создает Inline-клавиатуру для меню управления услугами в админ-панели."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➕ Добавить услугу", callback_data="adminAddService"))
    builder.row(InlineKeyboardButton(text="👁️ Просмотреть услуги", callback_data="adminViewServices"))
    builder.row(InlineKeyboardButton(text="🗑️ Удалить услугу", callback_data="adminDeleteService"))
    builder.row(InlineKeyboardButton(text="🔙 Назад в админ-панель", callback_data="adminBackToAdminMenu"))
    return builder.as_markup()


def admin_add_service_confirm_keyboard() -> InlineKeyboardMarkup:
    """Создает Inline-клавиатуру для подтверждения добавления услуги."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="✅ Добавить", callback_data="adminConfirmAddService"))
    builder.add(InlineKeyboardButton(text="❌ Отменить", callback_data="adminCancelAddService"))
    builder.adjust(2)
    return builder.as_markup()


def admin_services_list_action_keyboard(services: List[Service], action_prefix: str, current_page: int = 0,
                                        services_per_page: int = BOOKINGS_PER_PAGE) -> InlineKeyboardMarkup:
    """
    Создает Inline-клавиатуру со списком услуг для различных админ-действий (просмотр, удаление).
    `action_prefix` определяет, какое действие будет выполняться при выборе услуги.
    """
    builder = InlineKeyboardBuilder()

    start_index = current_page * services_per_page
    end_index = start_index + services_per_page

    services_on_page = services[start_index:end_index]

    for service in services_on_page:
        builder.button(text=service.name, callback_data=f"{action_prefix}_{service.id}")

    total_pages = (len(services) + services_per_page - 1) // services_per_page
    nav_buttons = []
    if current_page > 0:
        nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"{action_prefix}Page_{current_page - 1}"))
    else:
        nav_buttons.append(InlineKeyboardButton(text=" ", callback_data="ignore"))

    nav_buttons.append(InlineKeyboardButton(text=f"{current_page + 1}/{total_pages}", callback_data="ignore"))

    if current_page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"{action_prefix}Page_{current_page + 1}"))
    else:
        nav_buttons.append(InlineKeyboardButton(text=" ", callback_data="ignore"))

    builder.row(*nav_buttons)

    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="adminBackToServiceMenu")
    )

    return builder.as_markup()


def admin_single_service_view_keyboard(service_id: int) -> InlineKeyboardMarkup:
    """Создает Inline-клавиатуру для просмотра деталей одной услуги в админ-панели."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"adminDeleteServiceConfirm_{service_id}"))
    builder.row(
        InlineKeyboardButton(text="🔙 Назад к списку", callback_data="adminViewServices"))  # Возврат к списку услуг
    return builder.as_markup()


def admin_confirm_delete_service_keyboard(service_id: int) -> InlineKeyboardMarkup:
    """Создает Inline-клавиатуру для подтверждения удаления услуги."""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="✅ Подтвердить удаление", callback_data=f"adminExecuteDeleteService_{service_id}"))
    builder.add(InlineKeyboardButton(text="❌ Отменить", callback_data="adminViewServices"))  # Возврат к списку услуг
    builder.adjust(2)
    return builder.as_markup()