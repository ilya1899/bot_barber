from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import date, timedelta, datetime
import calendar
from typing import List, Tuple, Optional  # ИСПРАВЛЕНО: Добавлен Optional

from app.database.models import Service, Booking, Barber  # Убедитесь, что импортированы модели
from config import BOOKINGS_PER_PAGE, AVAILABLE_TIME_SLOTS


def services_keyboard(services: List[Service]) -> InlineKeyboardMarkup:
    """Создает Inline-клавиатуру со списком услуг."""
    builder = InlineKeyboardBuilder()
    for service in services:
        builder.add(InlineKeyboardButton(text=service.name, callback_data=f"chooseService_{service.id}"))
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="backToMainMenu"))
    return builder.as_markup()


def time_slots_keyboard(chosen_date_str: str, service_id: int):
    """
    Создает клавиатуру с доступными временными слотами.
    :param chosen_date_str: Выбранная дата в строковом формате 'YYYY-MM-DD'.
    :param service_id: ID выбранной услуги.
    :return: InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()

    # Список доступных временных слотов
    # Здесь можно добавить логику, чтобы получать слоты динамически
    # Например, из базы данных с учетом занятости мастеров

    # Генерация кнопок времени
    for time_slot in AVAILABLE_TIME_SLOTS:
        # ИСПРАВЛЕНО: Формируем callback_data в правильном формате
        callback_data = f"chooseTime_{time_slot}_{chosen_date_str}_{service_id}"
        builder.add(InlineKeyboardButton(text=time_slot, callback_data=callback_data))

    builder.adjust(4)

    # Добавление кнопок "Назад" и "Отмена"
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data=f"backToCalendar_{service_id}"),
        InlineKeyboardButton(text="❌ Отменить", callback_data="cancelForm")
    )

    return builder.as_markup()


def barbers_keyboard(barbers: list, chosen_date_str: str, chosen_time_str: str, service_id: int):
    """
    Создает клавиатуру с доступными мастерами.
    :param barbers: Список объектов Barber.
    :param chosen_date_str: Выбранная дата в формате 'YYYY-MM-DD'.
    :param chosen_time_str: Выбранное время в формате 'HH:MM'.
    :param service_id: ID выбранной услуги.
    :return: InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()

    for barber in barbers:
        # ИСПРАВЛЕНО: Формируем callback_data в правильном формате
        callback_data = f"chooseBarber_{barber.id}_{chosen_date_str}_{chosen_time_str}_{service_id}"
        builder.add(InlineKeyboardButton(text=barber.name, callback_data=callback_data))

    # Добавляем кнопку "Любой мастер"
    builder.add(InlineKeyboardButton(
        text="Любой мастер",
        callback_data=f"chooseBarber_any_{chosen_date_str}_{chosen_time_str}_{service_id}"
    ))

    builder.adjust(2)

    # Добавляем кнопку "Назад"
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data=f"backToTime_{chosen_date_str}_{service_id}"),
        InlineKeyboardButton(text="❌ Отменить", callback_data="cancelForm")
    )

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


def admin_services_list_action_keyboard(
        services: List,  # Тип должен быть List[Service], если используете модели
        base_callback_data: str,
        current_page: int,
        items_per_page: int
) -> InlineKeyboardMarkup:
    """
    Генерирует Inline-клавиатуру для списка услуг в админ-панели с пагинацией.
    :param services: Список объектов услуг.
    :param base_callback_data: Базовый префикс для callback_data кнопок услуг (например, "adminViewService").
    :param current_page: Текущая страница (начиная с 0).
    :param items_per_page: Количество услуг на одной странице.
    """
    keyboard = []

    total_services = len(services)
    total_pages = (total_services + items_per_page - 1) // items_per_page  # Правильный расчет общего количества страниц

    start_index = current_page * items_per_page
    end_index = start_index + items_per_page

    services_on_page = services[start_index:end_index]

    # Создаем кнопки для каждой услуги на текущей странице
    for service in services_on_page:
        # Callback data для просмотра деталей услуги будет выглядеть так: "adminViewService_123"
        keyboard.append([InlineKeyboardButton(text=service.name, callback_data=f"{base_callback_data}_{service.id}")])

    # Добавляем кнопки для навигации (Назад/Вперед) и индикатор страницы
    pagination_row = []
    if current_page > 0:
        # Callback data для перехода на предыдущую страницу: "adminViewServicePage_0"
        pagination_row.append(
            InlineKeyboardButton(text="⬅️ Назад", callback_data=f"adminViewServicePage_{current_page - 1}"))

    # Индикатор текущей страницы / общего количества страниц
    pagination_row.append(
        InlineKeyboardButton(text=f"{current_page + 1}/{total_pages}", callback_data="page_indicator"))

    if current_page < total_pages - 1:
        # Callback data для перехода на следующую страницу: "adminViewServicePage_2"
        pagination_row.append(
            InlineKeyboardButton(text="➡️ Вперед", callback_data=f"adminViewServicePage_{current_page + 1}"))

    if pagination_row:  # Добавляем ряд с пагинацией, только если в нем есть кнопки
        keyboard.append(pagination_row)

    # Кнопка для возврата в главное меню услуг
    keyboard.append([InlineKeyboardButton(text="↩️ Назад в меню услуг", callback_data="admin_back_to_services_menu")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


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

MASTERS_PER_PAGE = 5


def getMasterSelectKeyboard(barbers: list, callback_prefix: str, page: int) -> InlineKeyboardMarkup:
    """
    Создает инлайн-клавиатуру с пагинацией для списка мастеров.

    :param barbers: Список всех мастеров.
    :param callback_prefix: Префикс для callback_data (например, 'adminSelectDeleteMaster').
    :param page: Текущая страница (начиная с 0).
    :return: Объект InlineKeyboardMarkup.
    """
    keyboard_buttons = []

    total_pages = (len(barbers) + MASTERS_PER_PAGE - 1) // MASTERS_PER_PAGE
    start_index = page * MASTERS_PER_PAGE
    end_index = start_index + MASTERS_PER_PAGE

    # Добавляем кнопки для мастеров на текущей странице
    for i in range(start_index, min(end_index, len(barbers))):
        barber = barbers[i]
        keyboard_buttons.append([
            InlineKeyboardButton(text=barber.name, callback_data=f"{callback_prefix}_{barber.id}")
        ])

    # Добавляем кнопки пагинации (стрелки и номер страницы)
    pagination_buttons = []
    if page > 0:
        pagination_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"{callback_prefix}Page_{page - 1}"))

    pagination_buttons.append(
        InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="pagination_current_page"))

    if page < total_pages - 1:
        pagination_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"{callback_prefix}Page_{page + 1}"))

    if pagination_buttons:
        keyboard_buttons.append(pagination_buttons)

    # Кнопка "Назад"
    keyboard_buttons.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="adminMastersBack")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


def adminConfirmDeleteMasterKeyboard(master_id: int) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для подтверждения удаления мастера.
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Да, удалить", callback_data=f"adminExecuteDeleteMaster_{master_id}")],
        [InlineKeyboardButton(text="⬅️ Отмена", callback_data="cancelDeleteMaster")]
    ])

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


MONTHS_RU = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь",
             "Декабрь"]


def adminMasterVacationCalendarKeyboard(currentDate: date = None, minDate: date = None) -> InlineKeyboardMarkup:
    """
    Создает инлайн-клавиатуру календаря для выбора дат отпуска для мастера.
    Показывает только текущие и будущие даты.
    `minDate` может быть использована для предотвращения выбора дат до определенного момента.
    """
    if currentDate is None:
        currentDate = date.today()
    if minDate is None:
        minDate = date.today()

    builder = InlineKeyboardBuilder()

    # Ряд 1: Кнопки навигации по году
    builder.row(
        InlineKeyboardButton(text=f"« {currentDate.year - 1}",
                             callback_data=f"adminVacationNavigateYear_{currentDate.year - 1}"),
        InlineKeyboardButton(text=f"{currentDate.year}", callback_data="ignore"),
        InlineKeyboardButton(text=f"{currentDate.year + 1} »",
                             callback_data=f"adminVacationNavigateYear_{currentDate.year + 1}")
    )

    # Ряд 2: Кнопки навигации по месяцу
    builder.row(
        InlineKeyboardButton(text="«",
                             callback_data=f"adminVacationNavigateMonth_{(currentDate.replace(day=1) - timedelta(days=1)):%Y-%m}"),
        InlineKeyboardButton(text=f"{MONTHS_RU[currentDate.month - 1]}", callback_data="ignore"),
        InlineKeyboardButton(text="»",
                             callback_data=f"adminVacationNavigateMonth_{(currentDate.replace(day=28) + timedelta(days=4)):%Y-%m}")
    )

    # Ряд 3: Заголовки дней недели
    builder.row(*[InlineKeyboardButton(text=day, callback_data="ignore") for day in WEEKDAYS_RU])

    # Дни месяца
    firstDayOfMonth = currentDate.replace(day=1)
    startDayOfWeek = firstDayOfMonth.weekday()

    # Добавляем пустые кнопки для начала недели
    for _ in range(startDayOfWeek):
        builder.add(InlineKeyboardButton(text=" ", callback_data="ignore"))

    numDaysInMonth = (currentDate.replace(month=currentDate.month % 12 + 1, day=1) - timedelta(days=1)).day
    for dayNum in range(1, numDaysInMonth + 1):
        day = currentDate.replace(day=dayNum)

        # Отключаем прошедшие даты
        if day < minDate:
            builder.add(InlineKeyboardButton(text=" ", callback_data="ignore"))
        else:
            callback_data = f"adminVacationDate_{day:%Y-%m-%d}"
            builder.add(InlineKeyboardButton(text=str(dayNum), callback_data=callback_data))

    # Выравниваем кнопки дней по 7 столбцам
    builder.adjust(3, 3, 7, *([7] * 6), 1)

    # Последний ряд: Кнопка Отмены
    builder.row(InlineKeyboardButton(text="❌ Отменить", callback_data="adminCancelOperation"))

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


from datetime import date, timedelta
import calendar
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton



def adminCalendarKeyboard(current_date: date = None) -> InlineKeyboardMarkup:
    """
    Календарь для админ-панели с русскими месяцами и датами:
    « 2024 | • 2025 • | 2026 »
    « Июль | • Август • | Сентябрь »
    """
    if current_date is None:
        current_date = date.today()

    year = current_date.year
    month = current_date.month
    today = date.today()

    keyboard = []

    # --- 1. Навигация по годам ---
    keyboard.append([
        InlineKeyboardButton(text=f"{year-1}", callback_data=f"adminCalYear_{year-1}_{month}"),
        InlineKeyboardButton(text=f"• {year} •", callback_data="ignore"),
        InlineKeyboardButton(text=f"{year+1}", callback_data=f"adminCalYear_{year+1}_{month}")
    ])

    # --- 2. Навигация по месяцам ---
    prev_month = (month - 2) % 12 + 1
    next_month = month % 12 + 1

    keyboard.append([
        InlineKeyboardButton(text=MONTHS_RU[prev_month-1],
                             callback_data=f"adminCalMonth_{year}-{prev_month:02d}"),
        InlineKeyboardButton(text=f"• {MONTHS_RU[month-1]} •", callback_data="ignore"),
        InlineKeyboardButton(text=MONTHS_RU[next_month-1],
                             callback_data=f"adminCalMonth_{year}-{next_month:02d}")
    ])

    # --- 3. Дни недели ---
    keyboard.append([InlineKeyboardButton(text=day, callback_data="ignore") for day in WEEKDAYS_RU])

    # --- 4. Сетка дней месяца ---
    cal = calendar.Calendar(firstweekday=calendar.MONDAY)
    for week in cal.monthdayscalendar(year, month):
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data="ignore"))
            else:
                day_date = date(year, month, day)
                if day_date < today:
                    row.append(InlineKeyboardButton(text=" ", callback_data="ignore"))
                else:
                    btn_text = f"[{day}]" if day_date == today else str(day)
                    row.append(
                        InlineKeyboardButton(
                            text=btn_text,
                            callback_data=f"adminCalDate_{day_date.strftime('%Y-%m-%d')}"
                        )
                    )
        keyboard.append(row)

    # --- 5. Кнопка назад ---
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="adminBackToAdminMenuFromCalendar")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)



def adminDayBookingsKeyboard() -> InlineKeyboardMarkup:
    """
    Создает Inline-клавиатуру для просмотра записей за день с кнопкой "Назад к календарю".
    """
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Назад к календарю", callback_data="adminBackToCalendarSelection"))
    return builder.as_markup()



# Русские дни недели
WEEKDAYS_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def calendar_keyboard(current_date: date = None, service_id: int = None) -> InlineKeyboardMarkup:
    """
    Календарь с навигацией в формате:
    « 2024 | • 2025 • | 2026 »
    « Июль | • Август • | Сентябрь »
    """
    if current_date is None:
        current_date = date.today()

    year = current_date.year
    month = current_date.month
    today = date.today()

    builder = InlineKeyboardBuilder()

    # --- 1. Навигация по годам ---
    builder.row(
        InlineKeyboardButton(text=f"{year-1}", callback_data=f"navigateYear_{year-1}_{month}_{service_id}"),
        InlineKeyboardButton(text=f"• {year} •", callback_data="ignore"),
        InlineKeyboardButton(text=f"{year+1}", callback_data=f"navigateYear_{year+1}_{month}_{service_id}")
    )

    # --- 2. Навигация по месяцам ---
    prev_month = (month - 2) % 12 + 1  # предыдущий месяц
    next_month = month % 12 + 1        # следующий месяц

    builder.row(
        InlineKeyboardButton(
            text=f"{MONTHS_RU[prev_month-1]}",
            callback_data=f"navigateMonth_{year}-{prev_month:02d}_{service_id}"
        ),
        InlineKeyboardButton(
            text=f"• {MONTHS_RU[month-1]} •",
            callback_data="ignore"
        ),
        InlineKeyboardButton(
            text=f"{MONTHS_RU[next_month-1]}",
            callback_data=f"navigateMonth_{year}-{next_month:02d}_{service_id}"
        )
    )

    # --- 3. Дни недели ---
    weekday_buttons = [InlineKeyboardButton(text=day, callback_data="ignore") for day in WEEKDAYS_RU]
    builder.row(*weekday_buttons)

    # --- 4. Сетка дней месяца ---
    cal = calendar.Calendar(firstweekday=calendar.MONDAY)
    for week in cal.monthdayscalendar(year, month):
        day_buttons = []
        for day in week:
            if day == 0:
                day_buttons.append(InlineKeyboardButton(text=" ", callback_data="ignore"))
            else:
                day_date = date(year, month, day)
                # Блокируем прошлые даты
                if day_date < today:
                    day_buttons.append(InlineKeyboardButton(text=f"~{day}~", callback_data="ignore"))
                else:
                    day_buttons.append(
                        InlineKeyboardButton(
                            text=str(day),
                            callback_data=f"chooseDate_{day_date.strftime('%Y-%m-%d')}_{service_id}"
                        )
                    )
        builder.row(*day_buttons)

    # --- 5. Кнопка выхода ---
    builder.row(
        InlineKeyboardButton(text="🔙 Выход из календаря", callback_data="backToMainMenu")
    )

    return builder.as_markup()


def single_service_details_keyboard_with_nav(
        service_id: int,
        prev_service_id: int = None,
        next_service_id: int = None
) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для просмотра одной услуги с кнопками навигации.

    Args:
        service_id (int): ID текущей услуги.
        prev_service_id (int): ID предыдущей услуги. Если None, кнопка не отображается.
        next_service_id (int): ID следующей услуги. Если None, кнопка не отображается.

    Returns:
        InlineKeyboardMarkup: Объект клавиатуры.
    """
    builder = InlineKeyboardBuilder()

    # Кнопки навигации между услугами
    if prev_service_id is not None:
        builder.button(text="<", callback_data=f"showService_{prev_service_id}")

    # Кнопка для записи на текущую услугу
    builder.button(text="✍️ Записаться", callback_data=f"bookService_{service_id}")

    if next_service_id is not None:
        builder.button(text=">", callback_data=f"showService_{next_service_id}")

    builder.adjust(3)

    # Дополнительные кнопки
    builder.row(InlineKeyboardButton(text="❌ Назад", callback_data="cancelForm"))

    return builder.as_markup()


def get_final_booking_card_content(
        service_name: str,
        chosen_date: datetime.date,
        chosen_time: str,
        barber_name: str,
        service_id: int,
        barber_id: int | None
) -> Tuple[str, InlineKeyboardMarkup]:
    """
    Создает текст и inline-клавиатуру для карточки подтверждения записи.
    """
    card_text = (
        f"📋 **Подтверждение записи**\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"**Услуга:** {service_name}\n"
        f"**Дата:** {chosen_date.strftime('%d.%m.%Y')}\n"
        f"**Время:** {chosen_time}\n"
        f"**Мастер:** {barber_name}\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"Пожалуйста, проверьте данные и подтвердите запись."
    )

    # Формируем уникальную callback_data для кнопки подтверждения
    callback_data = f"confirmBooking_{service_id}_{chosen_date.strftime('%Y-%m-%d')}_{chosen_time}_{barber_id}"

    confirm_button = InlineKeyboardButton(text="✅ Подтвердить", callback_data=callback_data)
    cancel_button = InlineKeyboardButton(text="❌ Отменить", callback_data="cancelBooking")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [confirm_button],
        [cancel_button]
    ])

    return card_text, keyboard


def backToMastersKeyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура с кнопкой Назад к списку мастеров.
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="adminViewMasters")]
    ])