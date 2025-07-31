from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import date, timedelta, datetime
import calendar
from typing import List, Tuple, Optional  # ИСПРАВЛЕНО: Добавлен Optional

from app.database.models import Service, Booking, Barber  # Убедитесь, что импортированы модели
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
    """Создает Inline-клавиатуру календаря для выбора даты (для пользователя).
    Показывает только сегодняшние и будущие даты.
    """
    if current_date is None:
        current_date = date.today()

    builder = InlineKeyboardBuilder()
    today = date.today()

    # Навигация по году и месяцу
    month_name = current_date.strftime('%B').capitalize()  # Форматируем название месяца

    builder.row(
        InlineKeyboardButton(text=f"« {current_date.year - 1}", callback_data=f"navigateYear_{current_date.year - 1}"),
        InlineKeyboardButton(text=f"{current_date.year}", callback_data="ignore"),
        InlineKeyboardButton(text=f"{current_date.year + 1} »", callback_data=f"navigateYear_{current_date.year + 1}"),
        width=3  # ИСПРАВЛЕНО: Указываем ширину
    )
    builder.row(
        InlineKeyboardButton(text="«",
                             callback_data=f"navigateMonth_{(current_date.replace(day=1) - timedelta(days=1)):%Y-%m}"),
        # ИСПРАВЛЕНО: Короткий текст
        InlineKeyboardButton(text=f"{month_name} {current_date.year}", callback_data="ignore"),
        # ИСПРАВЛЕНО: Месяц и год
        InlineKeyboardButton(text="»",
                             callback_data=f"navigateMonth_{(current_date.replace(day=28) + timedelta(days=4)):%Y-%m}"),
        # ИСПРАВЛЕНО: Короткий текст
        width=3  # ИСПРАВЛЕНО: Указываем ширину
    )

    # Дни недели
    weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    builder.row(*[InlineKeyboardButton(text=day, callback_data="ignore") for day in weekdays],
                width=7)  # ИСПРАВЛЕНО: Указываем ширину

    # Дни месяца
    first_day_of_month = current_date.replace(day=1)
    start_day_of_week = first_day_of_month.weekday()

    # Добавляем пустые кнопки для начала недели, если месяц начинается не с понедельника
    for _ in range(start_day_of_week):
        builder.add(InlineKeyboardButton(text=" ", callback_data="ignore"))

    num_days_in_month = (current_date.replace(month=current_date.month % 12 + 1, day=1) - timedelta(days=1)).day

    for day_num in range(1, num_days_in_month + 1):
        day = current_date.replace(day=day_num)
        callback_data = f"chooseDate_{day:%Y-%m-%d}"
        button_text = str(day_num)

        # Отключаем кнопки для прошедших дат
        if day < today:
            builder.add(InlineKeyboardButton(text=" ", callback_data="ignore"))  # Неактивная кнопка
        else:
            if day == today:
                button_text = f"[{day_num}]"  # Обозначаем сегодняшний день
            builder.add(InlineKeyboardButton(text=button_text, callback_data=callback_data))

    builder.adjust(7)  # Выравниваем дни по 7 столбцам

    # Нижние кнопки
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


def adminMastersMenuKeyboard() -> InlineKeyboardMarkup:
    """Creates an inline keyboard for the master management menu in the admin panel."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➕ Добавить мастера", callback_data="adminAddMaster"))
    builder.row(InlineKeyboardButton(text="👁️ Просмотреть мастеров", callback_data="adminViewMasters"))
    builder.row(InlineKeyboardButton(text="🗑️ Удалить мастера", callback_data="adminDeleteMaster"))
    builder.row(InlineKeyboardButton(text="🏖️ Отправить в отпуск", callback_data="adminMasterVacation"))  # New button
    builder.row(InlineKeyboardButton(text="🔙 Назад в админ-панель", callback_data="adminBackToAdminMenuFromMasters"))
    return builder.as_markup()


def adminAddMasterConfirmKeyboard() -> InlineKeyboardMarkup:
    """Creates an inline keyboard for confirming adding a master."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="✅ Добавить", callback_data="adminConfirmAddMaster"))
    builder.add(InlineKeyboardButton(text="❌ Отменить", callback_data="adminCancelAddMaster"))
    builder.adjust(2)
    return builder.as_markup()


def adminMastersListActionKeyboard(barbers: List[Barber], action_prefix: str, currentPage: int = 0,
                                   itemsPerPage: int = BOOKINGS_PER_PAGE) -> InlineKeyboardMarkup:
    """
    Creates an inline keyboard with a paginated list of barbers for various admin actions.
    `action_prefix` determines the action when a barber is selected (e.g., "adminViewMaster", "adminSelectDeleteMaster").
    """
    builder = InlineKeyboardBuilder()

    startIndex = currentPage * itemsPerPage
    endIndex = startIndex + itemsPerPage

    barbersOnPage = barbers[startIndex:endIndex]

    for barber in barbersOnPage:
        builder.button(text=barber.name, callback_data=f"{action_prefix}_{barber.id}")

    totalPages = (len(barbers) + itemsPerPage - 1) // itemsPerPage
    navButtons = []
    if currentPage > 0:
        navButtons.append(InlineKeyboardButton(text="◀️", callback_data=f"{action_prefix}Page_{currentPage - 1}"))
    else:
        navButtons.append(InlineKeyboardButton(text=" ", callback_data="ignore"))

    navButtons.append(InlineKeyboardButton(text=f"{currentPage + 1}/{totalPages}", callback_data="ignore"))

    if currentPage < totalPages - 1:
        navButtons.append(InlineKeyboardButton(text="▶️", callback_data=f"{action_prefix}Page_{currentPage + 1}"))
    else:
        navButtons.append(InlineKeyboardButton(text=" ", callback_data="ignore"))

    builder.row(*navButtons)

    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="adminBackToMastersMenu")  # Back to masters menu
    )

    return builder.as_markup()


def adminSingleMasterViewKeyboard(masterId: int) -> InlineKeyboardMarkup:
    """Creates an inline keyboard for viewing details of a single master in the admin panel."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"adminConfirmDeleteMaster_{masterId}"))
    builder.row(InlineKeyboardButton(text="🔙 Назад к списку", callback_data="adminViewMasters"))  # Back to list
    return builder.as_markup()


def adminConfirmDeleteMasterKeyboard(masterId: int) -> InlineKeyboardMarkup:
    """Creates an inline keyboard for confirming the deletion of a master."""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="✅ Подтвердить удаление", callback_data=f"adminExecuteDeleteMaster_{masterId}"))
    builder.add(InlineKeyboardButton(text="❌ Отменить", callback_data="adminViewMasters"))  # Back to list
    builder.adjust(2)
    return builder.as_markup()


def adminMasterServicesSelectionKeyboard(services: List[Service],
                                         selectedServiceIds: List[int]) -> InlineKeyboardMarkup:
    """
    Creates an inline keyboard for selecting services provided by a master.
    Selected services are marked with a checkmark.
    """
    builder = InlineKeyboardBuilder()
    for service in services:
        checkmark = "✅ " if service.id in selectedServiceIds else ""
        builder.add(InlineKeyboardButton(text=f"{checkmark}{service.name}",
                                         callback_data=f"adminToggleMasterService_{service.id}"))
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="✅ Подтвердить выбор услуг", callback_data="adminConfirmMasterServices"))
    builder.row(InlineKeyboardButton(text="❌ Отменить добавление мастера",
                                     callback_data="adminCancelAddMaster"))  # Generic cancel
    return builder.as_markup()


def adminMasterVacationCalendarKeyboard(currentDate: date = None, minDate: date = None) -> InlineKeyboardMarkup:
    """
    Creates an inline calendar keyboard for selecting vacation dates for a master.
    `minDate` can be used to prevent selecting dates before a certain point (e.g., start date).
    """
    if currentDate is None:
        currentDate = date.today()
    if minDate is None:
        minDate = date.today()

    builder = InlineKeyboardBuilder()

    # Navigation buttons for year
    builder.row(
        InlineKeyboardButton(text=f"« {currentDate.year - 1}",
                             callback_data=f"adminVacationNavigateYear_{currentDate.year - 1}"),
        InlineKeyboardButton(text=f"{currentDate.year}", callback_data="ignore"),
        InlineKeyboardButton(text=f"{currentDate.year + 1} »",
                             callback_data=f"adminVacationNavigateYear_{currentDate.year + 1}")
    )
    # Navigation buttons for month
    builder.row(
        InlineKeyboardButton(text="« Предыдущий",
                             callback_data=f"adminVacationNavigateMonth_{currentDate.replace(day=1) - timedelta(days=1):%Y-%m}"),
        InlineKeyboardButton(text=f"{currentDate.strftime('%B')}", callback_data="ignore"),
        InlineKeyboardButton(text="Следующий »",
                             callback_data=f"adminVacationNavigateMonth_{currentDate.replace(day=28) + timedelta(days=4):%Y-%m}")
    )

    # Weekday headers
    weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    builder.row(*[InlineKeyboardButton(text=day, callback_data="ignore") for day in weekdays])

    # Days of the month
    firstDayOfMonth = currentDate.replace(day=1)
    startDayOfWeek = firstDayOfMonth.weekday()

    for _ in range(startDayOfWeek):
        builder.add(InlineKeyboardButton(text=" ", callback_data="ignore"))

    numDaysInMonth = (currentDate.replace(month=currentDate.month % 12 + 1, day=1) - timedelta(days=1)).day
    for dayNum in range(1, numDaysInMonth + 1):
        day = currentDate.replace(day=dayNum)
        # Disable past dates or dates before minDate
        if day < minDate:
            builder.add(InlineKeyboardButton(text=str(dayNum), callback_data="ignore"))
        else:
            callback_data = f"adminVacationDate_{day:%Y-%m-%d}"
            builder.add(InlineKeyboardButton(text=str(dayNum), callback_data=callback_data))

    builder.adjust(7)

    builder.row(InlineKeyboardButton(text="❌ Отменить", callback_data="adminCancelOperation"))  # Generic cancel
    return builder.as_markup()


def adminMasterVacationConfirmKeyboard() -> InlineKeyboardMarkup:
    """Creates an inline keyboard for confirming the master's vacation period."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="✅ Подтвердить", callback_data="adminConfirmVacation"))
    builder.add(InlineKeyboardButton(text="❌ Отменить", callback_data="adminCancelVacation"))
    builder.adjust(2)
    return builder.as_markup()


def adminStatisticsCategoryKeyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура для выбора категории статистики (Пользователи, Услуги, Мастера).
    """
    buttons = [
        [
            InlineKeyboardButton(text="Пользователи", callback_data="adminSelectStatCategory_users"),
            InlineKeyboardButton(text="Услуги", callback_data="adminSelectStatCategory_services")
        ],
        [
            InlineKeyboardButton(text="Мастера", callback_data="adminSelectStatCategory_masters")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="adminBackToAdminMenuFromStatistics")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def adminStatisticsTimePeriodKeyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура для выбора периода статистики (День, Неделя, Месяц, Год, Всё время, Произвольно).
    """
    buttons = [
        [
            InlineKeyboardButton(text="Сегодня", callback_data="adminSelectTimePeriod_day"),
            InlineKeyboardButton(text="Неделя", callback_data="adminSelectTimePeriod_week")
        ],
        [
            InlineKeyboardButton(text="Месяц", callback_data="adminSelectTimePeriod_month"),
            InlineKeyboardButton(text="Год", callback_data="adminSelectTimePeriod_year")
        ],
        [
            InlineKeyboardButton(text="Всё время", callback_data="adminSelectTimePeriod_all_time"),
            InlineKeyboardButton(text="Произвольно", callback_data="adminSelectTimePeriod_custom")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="adminBackToStatCategorySelection")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def adminStatisticsCalendarKeyboard(current_date: date = None, min_date: date = None,
                                    max_date: date = None) -> InlineKeyboardMarkup:
    """
    Генерирует инлайн-клавиатуру календаря для выбора даты в статистике.
    current_date: Дата, которая отображается в текущем месяце календаря.
    min_date: Минимально разрешенная дата для выбора (для диапазона, если нужно).
    max_date: Максимально разрешенная дата для выбора (для диапазона, если нужно).
    """
    if current_date is None:
        current_date = date.today()

    today = date.today()

    keyboard = []

    # Навигация по году
    year_buttons = [
        InlineKeyboardButton(text="< Год", callback_data=f"adminStatCalYear_{current_date.year - 1}"),
        InlineKeyboardButton(text=f"{current_date.year}", callback_data="adminStatCalIgnore"),
        InlineKeyboardButton(text="Год >", callback_data=f"adminStatCalYear_{current_date.year + 1}")
    ]
    keyboard.append(year_buttons)

    # Навигация по месяцу
    month_buttons = [
        InlineKeyboardButton(text="< Месяц",
                             callback_data=f"adminStatCalMonth_{(current_date.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')}"),
        InlineKeyboardButton(text=f"{current_date.strftime('%B %Y')}", callback_data="adminStatCalIgnore"),
        InlineKeyboardButton(text="Месяц >",
                             callback_data=f"adminStatCalMonth_{(current_date.replace(day=28) + timedelta(days=4)).replace(day=1).strftime('%Y-%m')}")
    ]
    keyboard.append(month_buttons)

    # Дни недели
    week_days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    keyboard.append([InlineKeyboardButton(text=day, callback_data="adminStatCalIgnore") for day in week_days])

    # Дни месяца
    first_day_of_month = current_date.replace(day=1)
    # Определяем, какой день недели является первым днем месяца (Пн=0, Вс=6)
    start_offset = (first_day_of_month.weekday()) % 7  # Если Пн=0, то 0. Если Вс=6, то 6.

    # Создаем пустые кнопки для начала недели, если месяц начинается не с понедельника
    current_week = [InlineKeyboardButton(text=" ", callback_data="adminStatCalIgnore")] * start_offset

    for day in range(1, (current_date.replace(month=current_date.month % 12 + 1, day=1) - timedelta(days=1)).day + 1):
        current_day = date(current_date.year, current_date.month, day)
        button_text = str(day)
        callback_data = f"adminStatCalDate_{current_day.strftime('%Y-%m-%d')}"

        # Проверяем, находится ли дата в разрешенном диапазоне
        is_disabled = False
        if min_date and current_day < min_date:
            is_disabled = True
        if max_date and current_day > max_date:  # Здесь обычно max_date не нужен для выбора начала, но для конца да
            is_disabled = True

        # Если кнопка сегодняшняя или выбрана и не отключена
        if current_day == today:
            button_text = f"[{day}]"

        if is_disabled:
            current_week.append(InlineKeyboardButton(text=" ", callback_data="adminStatCalIgnore"))  # Неактивная кнопка
        else:
            current_week.append(InlineKeyboardButton(text=button_text, callback_data=callback_data))

        if len(current_week) == 7:
            keyboard.append(current_week)
            current_week = []

    if current_week:
        # Добавляем пустые кнопки, если последняя неделя неполная
        while len(current_week) < 7:
            current_week.append(InlineKeyboardButton(text=" ", callback_data="adminStatCalIgnore"))
        keyboard.append(current_week)

    keyboard.append(
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="adminBackToTimePeriodSelection")])  # Новая кнопка назад

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def adminCalendarKeyboard(current_date: date = None) -> InlineKeyboardMarkup:
    """
    Генерирует инлайн-клавиатуру календаря для выбора даты в админ-панели.
    Показывает только сегодняшние и будущие даты.
    """
    if current_date is None:
        current_date = date.today()

    today = date.today()

    keyboard = []

    # Навигация по году
    year_buttons = [
        InlineKeyboardButton(text=f"« {current_date.year - 1}", callback_data=f"adminCalYear_{current_date.year - 1}"),
        InlineKeyboardButton(text=f"{current_date.year}", callback_data="ignore"),
        InlineKeyboardButton(text=f"{current_date.year + 1} »", callback_data=f"adminCalYear_{current_date.year + 1}")
    ]
    keyboard.append(year_buttons)

    # Навигация по месяцу
    month_buttons = [
        InlineKeyboardButton(text="« Предыдущий",
                             callback_data=f"adminCalMonth_{(current_date.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')}"),
        InlineKeyboardButton(text=f"{current_date.strftime('%B %Y')}", callback_data="ignore"),
        InlineKeyboardButton(text="Следующий »",
                             callback_data=f"adminCalMonth_{(current_date.replace(day=28) + timedelta(days=4)).replace(day=1).strftime('%Y-%m')}")
    ]
    keyboard.append(month_buttons)

    # Дни недели
    week_days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    keyboard.append([InlineKeyboardButton(text=day, callback_data="ignore") for day in week_days])

    # Дни месяца
    first_day_of_month = current_date.replace(day=1)
    # Определяем, какой день недели является первым днем месяца (Пн=0, Вс=6)
    start_offset = (first_day_of_month.weekday()) % 7

    # Создаем пустые кнопки для начала недели, если месяц начинается не с понедельника
    current_week = [InlineKeyboardButton(text=" ", callback_data="ignore")] * start_offset

    # Количество дней в текущем месяце
    num_days_in_month = (current_date.replace(month=current_date.month % 12 + 1, day=1) - timedelta(days=1)).day

    for day_num in range(1, num_days_in_month + 1):
        current_day = date(current_date.year, current_date.month, day_num)
        button_text = str(day_num)
        callback_data = f"adminCalDate_{current_day.strftime('%Y-%m-%d')}"

        # Отключаем кнопки для прошедших дат
        if current_day < today:
            current_week.append(InlineKeyboardButton(text=" ", callback_data="ignore"))  # Неактивная кнопка
        else:
            if current_day == today:
                button_text = f"[{day_num}]"  # Обозначаем сегодняшний день
            current_week.append(InlineKeyboardButton(text=button_text, callback_data=callback_data))

        if len(current_week) == 7:
            keyboard.append(current_week)
            current_week = []

    if current_week:
        # Добавляем пустые кнопки, если последняя неделя неполная
        while len(current_week) < 7:
            current_week.append(InlineKeyboardButton(text=" ", callback_data="ignore"))
        keyboard.append(current_week)

    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="adminBackToAdminMenuFromCalendar")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def adminDayBookingsKeyboard() -> InlineKeyboardMarkup:
    """
    Создает Inline-клавиатуру для просмотра записей за день с кнопкой "Назад к календарю".
    """
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Назад к календарю", callback_data="adminBackToCalendarSelection"))
    return builder.as_markup()