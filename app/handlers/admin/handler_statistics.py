# app/handlers/admin/handler_statistics.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import StateFilter  # <-- НОВЫЙ ИМПОРТ: StateFilter
from datetime import date, datetime, timedelta
from typing import List, Tuple, Optional

from app.keyboards.kbreply import admin_menu_keyboard
from app.keyboards.kbinline import (
    adminStatisticsCategoryKeyboard, adminStatisticsTimePeriodKeyboard,
    adminStatisticsCalendarKeyboard
)
from app.database import requests as db_requests

admin_statistics_router = Router()


# --- Состояния для статистики ---
class AdminStatisticsState(StatesGroup):
    """Состояния FSM для сбора параметров статистики."""
    waitingForCategory = State()
    waitingForTimePeriod = State()
    waitingForCustomStartDate = State()
    waitingForCustomEndDate = State()


# --- Главное меню статистики ---
@admin_statistics_router.message(F.text == "Статистика")
async def handlerAdminStatisticsMenu(message: Message, state: FSMContext):
    """
    Отображает главное меню для статистики, предлагая выбрать категорию.
    """
    if not await db_requests.isUserAdmin(message.from_user.id):
        await message.answer("У вас нет прав для выполнения этого действия.")
        return

    await state.clear()  # Очищаем любое предыдущее состояние
    await message.answer(
        """Выберите категорию статистики:""",
        reply_markup=adminStatisticsCategoryKeyboard()
    )
    await state.set_state(AdminStatisticsState.waitingForCategory)


@admin_statistics_router.callback_query(F.data == "adminBackToAdminMenuFromStatistics")
async def handlerAdminBackToAdminMenuFromStatistics(callback: CallbackQuery, state: FSMContext):
    """
    Возвращает администратора в главное меню админ-панели из раздела статистики.
    """
    if not await db_requests.isUserAdmin(callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        return

    await state.clear()
    await callback.message.edit_text("Вы вернулись в главное меню админ-панели.")
    await callback.message.answer("Добро пожаловать в админ-панель!", reply_markup=admin_menu_keyboard)
    await callback.answer()


# --- Выбор категории статистики ---
@admin_statistics_router.callback_query(AdminStatisticsState.waitingForCategory,
                                        F.data.startswith("adminSelectStatCategory_"))
async def handlerAdminSelectStatCategory(callback: CallbackQuery, state: FSMContext):
    """
    Обрабатывает выбор категории статистики и предлагает выбрать период.
    """
    if not await db_requests.isUserAdmin(callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        return

    category = callback.data.split("_")[1]  # users, services, masters
    await state.update_data(statCategory=category)

    await callback.message.edit_text(
        """Выберите период для статистики:""",
        reply_markup=adminStatisticsTimePeriodKeyboard()
    )
    await state.set_state(AdminStatisticsState.waitingForTimePeriod)
    await callback.answer()


@admin_statistics_router.callback_query(F.data == "adminBackToStatCategorySelection")
async def handlerAdminBackToStatCategorySelection(callback: CallbackQuery, state: FSMContext):
    """
    Возвращает администратора к выбору категории статистики.
    """
    if not await db_requests.isUserAdmin(callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        return

    await state.clear()  # Очищаем состояние выбора времени, если было
    await callback.message.edit_text(
        """Выберите категорию статистики:""",
        reply_markup=adminStatisticsCategoryKeyboard()
    )
    await state.set_state(AdminStatisticsState.waitingForCategory)
    await callback.answer()


# --- Выбор периода времени для статистики ---
@admin_statistics_router.callback_query(AdminStatisticsState.waitingForTimePeriod,
                                        F.data.startswith("adminSelectTimePeriod_"))
async def handlerAdminSelectTimePeriod(callback: CallbackQuery, state: FSMContext):
    """
    Обрабатывает выбор периода времени для статистики.
    """
    if not await db_requests.isUserAdmin(callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        return

    period_type = callback.data.split("_")[1]

    end_date = date.today()  # Конечная дата для большинства периодов - сегодня

    start_date: Optional[date] = None
    if period_type == "day":
        start_date = end_date
    elif period_type == "week":
        start_date = end_date - timedelta(days=end_date.weekday())  # Начало текущей недели (понедельник)
    elif period_type == "month":
        start_date = end_date.replace(day=1)  # Начало текущего месяца
    elif period_type == "year":
        start_date = end_date.replace(month=1, day=1)  # Начало текущего года
    elif period_type == "all_time":
        start_date = None  # Будет обработано в функции db_requests как "с начала"
    elif period_type == "custom":
        # Переходим к выбору произвольного периода
        await state.update_data(calendar_display_date=date.today())  # Для отображения календаря
        await callback.message.edit_text(
            """Выберите дату начала периода:""",
            reply_markup=adminStatisticsCalendarKeyboard(date.today(), max_date=date.today())
            # Нельзя выбрать дату в будущем
        )
        await state.set_state(AdminStatisticsState.waitingForCustomStartDate)
        await callback.answer()
        return  # Выходим, чтобы не выводить статистику сейчас

    # Сохраняем выбранные даты для дальнейшего использования
    await state.update_data(statStartDate=start_date, statEndDate=end_date)
    await displayStatistics(callback.message, state)
    await callback.answer()


# --- Календарь для произвольного периода (Выбор даты начала/конца) ---
@admin_statistics_router.callback_query(
    StateFilter(AdminStatisticsState.waitingForCustomStartDate, AdminStatisticsState.waitingForCustomEndDate),
    # ИСПРАВЛЕНО
    F.data.startswith("adminStatCalYear_") | F.data.startswith("adminStatCalMonth_") | F.data.startswith(
        "adminStatCalDate_")
)
async def handlerAdminStatisticsCalendarNavigationOrSelection(callback: CallbackQuery, state: FSMContext):
    """
    Единый хэндлер для навигации по календарю и выбора даты для произвольного диапазона статистики.
    """
    if not await db_requests.isUserAdmin(callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        return

    user_data = await state.get_data()
    current_calendar_display_date: date = user_data.get('calendar_display_date', date.today())
    current_state = await state.get_state()

    # Даты, которые уже были выбраны
    custom_start_date: Optional[date] = user_data.get('statStartDate')

    action_data = callback.data.split("_")
    action_type = action_data[0]
    value = action_data[1]

    new_calendar_display_date = current_calendar_display_date  # По умолчанию текущая отображаемая дата

    if action_type == "adminStatCalYear":
        new_year = int(value)
        new_calendar_display_date = current_calendar_display_date.replace(year=new_year)
    elif action_type == "adminStatCalMonth":
        new_calendar_display_date = datetime.strptime(value, "%Y-%m").date()
    elif action_type == "adminStatCalDate":
        chosen_date = datetime.strptime(value, "%Y-%m-%d").date()

        if current_state == AdminStatisticsState.waitingForCustomStartDate:
            if chosen_date > date.today():  # Нельзя выбрать будущую дату
                await callback.answer("Нельзя выбрать будущую дату для начала периода.", show_alert=True)
                return
            await state.update_data(statStartDate=chosen_date)
            await state.update_data(calendar_display_date=chosen_date)  # Сбрасываем календарь на выбранный месяц

            await callback.message.edit_text(
                f"""Дата начала: <b>{chosen_date.strftime('%d.%m.%Y')}</b>.
Выберите дату окончания периода:""",
                reply_markup=adminStatisticsCalendarKeyboard(chosen_date, min_date=chosen_date, max_date=date.today())
                # Мин. дата - выбранная дата начала, макс. - сегодня
            )
            await state.set_state(AdminStatisticsState.waitingForCustomEndDate)
            await callback.answer()
            return  # Выходим, так как состояние изменилось

        elif current_state == AdminStatisticsState.waitingForCustomEndDate:
            if not custom_start_date or chosen_date < custom_start_date:
                await callback.answer("Дата окончания не может быть раньше даты начала.", show_alert=True)
                return
            if chosen_date > date.today():  # Нельзя выбрать будущую дату
                await callback.answer("Нельзя выбрать будущую дату для окончания периода.", show_alert=True)
                return
            await state.update_data(statEndDate=chosen_date)
            await displayStatistics(callback.message, state)
            await callback.answer()
            return  # Выходим, так как состояние изменилось

    await state.update_data(calendar_display_date=new_calendar_display_date)

    # Обновляем клавиатуру календаря с учетом новой отображаемой даты и min/max date
    if current_state == AdminStatisticsState.waitingForCustomStartDate:
        keyboard_markup = adminStatisticsCalendarKeyboard(new_calendar_display_date, max_date=date.today())
    elif current_state == AdminStatisticsState.waitingForCustomEndDate:
        keyboard_markup = adminStatisticsCalendarKeyboard(new_calendar_display_date, min_date=custom_start_date,
                                                          max_date=date.today())

    await callback.message.edit_reply_markup(reply_markup=keyboard_markup)
    await callback.answer()


@admin_statistics_router.callback_query(
    StateFilter(AdminStatisticsState.waitingForCustomStartDate, AdminStatisticsState.waitingForCustomEndDate),
    # ИСПРАВЛЕНО
    F.data == "adminBackToTimePeriodSelection"
)
async def handlerAdminBackToTimePeriodSelectionFromCalendar(callback: CallbackQuery, state: FSMContext):
    """
    Возвращает администратора к выбору периода времени из календаря.
    """
    if not await db_requests.isUserAdmin(callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        return

    await state.update_data(statStartDate=None, statEndDate=None, calendar_display_date=None)  # Сброс данных календаря
    await callback.message.edit_text(
        """Выберите период для статистики:""",
        reply_markup=adminStatisticsTimePeriodKeyboard()
    )
    await state.set_state(AdminStatisticsState.waitingForTimePeriod)
    await callback.answer()


# --- Вспомогательная функция для отображения статистики ---
async def displayStatistics(message: Message, state: FSMContext):
    """
    Формирует и отображает запрошенную статистику.
    """
    user_data = await state.get_data()
    category = user_data.get('statCategory')
    start_date = user_data.get('statStartDate')
    end_date = user_data.get('statEndDate')

    stat_text = """<b>📊 Статистика</b>

"""
    period_str = ""

    if start_date and end_date:
        if start_date == end_date:
            period_str = f"за {start_date.strftime('%d.%m.%Y')}"
        else:
            period_str = f"с {start_date.strftime('%d.%m.%Y')} по {end_date.strftime('%d.%m.%Y')}"
    elif start_date is None:  # all_time
        period_str = "за всё время"

    if category == "users":
        new_users_count = await db_requests.getNewUsersCount(start_date, end_date)
        stat_text += f"""Новые пользователи {period_str}: <b>{new_users_count}</b>
"""
    elif category == "services":
        service_stats = await db_requests.getServiceBookingStatistics(start_date, end_date)
        stat_text += f"""Записи по услугам {period_str}:
"""
        if service_stats:
            for service_name, count in service_stats:
                stat_text += f"""  - {service_name}: <b>{count}</b>
"""
        else:
            stat_text += """Нет записей по услугам за выбранный период.
"""
    elif category == "masters":
        master_stats = await db_requests.getMasterBookingStatistics(start_date, end_date)
        stat_text += f"""Записи по мастерам {period_str}:
"""
        if master_stats:
            for master_name, count in master_stats:
                stat_text += f"""  - {master_name}: <b>{count}</b>
"""
        else:
            stat_text += """Нет записей к мастерам за выбранный период.
"""
    else:
        stat_text = """Неизвестная категория статистики."""

    await message.edit_text(stat_text)
    await message.answer("""Выберите категорию статистики:""", reply_markup=adminStatisticsCategoryKeyboard())
    await state.set_state(AdminStatisticsState.waitingForCategory)
    await state.update_data(statCategory=None, statStartDate=None, statEndDate=None,
                            calendar_display_date=None)  # Очищаем данные статистики