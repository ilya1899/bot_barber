from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, date  # <-- ИСПРАВЛЕННЫЙ ИМПОРТ
from sqlalchemy.ext.asyncio import AsyncSession

import calendar
from typing import Callable

from app.keyboards.kbreply import main_menu_keyboard
from app.keyboards.kbinline import (
    services_keyboard,
    calendar_keyboard,  # Теперь это наша новая функция
    time_slots_keyboard,
    get_final_booking_card_content,
    barbers_keyboard
)
from app.database import requests as db_requests
from app.database.models import Service, Booking, Barber
from config import AVAILABLE_TIME_SLOTS

appointment_router = Router()


class BookingState(StatesGroup):
    """Состояния для типизации и удобства (не используются для реального FSM)."""
    choosingService = State()
    choosingDate = State()
    choosingTime = State()
    choosingBarber = State()
    confirmingBooking = State()


@appointment_router.message(F.text == "💈 Записаться")
async def handlerBookAppointment(message: Message):
    """
    Начинает процесс записи на услугу.
    Проверяет регистрацию пользователя и предлагает выбрать услугу.
    """
    user = await db_requests.getUser(message.from_user.id)
    if not user or not user.first_name or not user.phone_number:
        await message.answer(
            """Для записи на стрижку необходимо пройти регистрацию.
Пожалуйста, используйте команду /start для начала регистрации.""",
            reply_markup=main_menu_keyboard
        )
        return

    services = await db_requests.getServices()
    if not services:
        await message.answer(
            """Извините, пока нет доступных услуг. Пожалуйста, попробуйте позже.""",
            reply_markup=main_menu_keyboard
        )
        return

    await message.answer(
        """Выберите услугу:""",
        reply_markup=services_keyboard(services)
    )


@appointment_router.callback_query(F.data.startswith("chooseService_"))
async def handlerChooseService(callback: CallbackQuery):
    """
    Обрабатывает выбор услуги.
    Предлагает выбрать дату.
    """
    service_id = int(callback.data.split("_")[1])
    service = await db_requests.getServiceById(service_id)
    if not service:
        all_services = await db_requests.getServices()
        await callback.message.edit_text(
            """Услуга не найдена. Пожалуйста, выберите другую.""",
            reply_markup=services_keyboard(all_services)
        )
        await callback.answer("Ошибка: услуга не найдена.", show_alert=True)
        return

    # Отправляем сообщение с календарём, передавая ID услуги
    await callback.message.edit_text(
        """Выберите дату для записи:""",
        reply_markup=calendar_keyboard(service_id=service_id)
    )
    await callback.answer("Начинаем запись на выбранную услугу.")


@appointment_router.callback_query(F.data.startswith("navigateMonth_"))
async def handlerNavigateMonth(callback: CallbackQuery):
    """
    Навигация по месяцам в календаре.
    В callback_data ожидаем формат: "navigateMonth_{YYYY-MM}_{service_id}"
    """
    parts = callback.data.split("_")
    new_month_str = parts[1]
    service_id = int(parts[2])

    new_date = datetime.strptime(new_month_str, "%Y-%m").date()
    await callback.message.edit_reply_markup(reply_markup=calendar_keyboard(new_date, service_id))
    await callback.answer()


@appointment_router.callback_query(F.data.startswith("navigateYear_"))
async def handlerNavigateYear(callback: CallbackQuery):
    """
    Навигация по годам в календаре.
    В callback_data ожидаем формат: "navigateYear_{YYYY}_{MM}_{service_id}"
    """
    parts = callback.data.split("_")
    new_year = int(parts[1])
    month = int(parts[2])
    service_id = int(parts[3])

    current_date = date(new_year, month, 1)

    await callback.message.edit_reply_markup(reply_markup=calendar_keyboard(current_date, service_id))
    await callback.answer()


@appointment_router.callback_query(F.data.startswith("chooseDate_"))
async def handlerChooseDate(callback: CallbackQuery):
    """
    Обрабатывает выбор даты и предлагает выбрать время.
    В callback_data ожидаем формат: "chooseDate_{YYYY-MM-DD}_{service_id}"
    """
    parts = callback.data.split("_")
    chosen_date_str = parts[1]
    service_id = int(parts[2])

    chosen_date = datetime.strptime(chosen_date_str, "%Y-%m-%d").date()

    if chosen_date < date.today():
        await callback.answer(
            """Нельзя выбрать прошедшую дату. Пожалуйста, выберите другую дату.""",
            show_alert=True
        )
        return

    # ИСПРАВЛЕНО: Передаем chosen_date и service_id в time_slots_keyboard
    # чтобы она могла сгенерировать правильную callback_data для кнопок времени.
    await callback.message.edit_text(
        f"""Вы выбрали {chosen_date.strftime('%d.%m.%Y')}.\nВыберите время:""",
        reply_markup=time_slots_keyboard(chosen_date_str, service_id)
    )
    await callback.answer()


@appointment_router.callback_query(F.data.startswith("chooseTime_"))
async def handlerChooseTime(callback: CallbackQuery):
    """
    Обрабатывает выбор времени и предлагает выбрать мастера.
    В callback.data ожидаем данные в формате "chooseTime_{HH:MM}_{YYYY-MM-DD}_{service_id}".
    """
    parts = callback.data.split("_")
    if len(parts) < 4:
        await callback.answer("Некорректные данные.", show_alert=True)
        return

    chosen_time_str = parts[1]
    chosen_date_str = parts[2]
    service_id = int(parts[3])

    try:
        chosen_date = datetime.strptime(chosen_date_str, "%Y-%m-%d").date()
    except ValueError:
        await callback.answer("Некорректная дата.", show_alert=True)
        return

    barbers = await db_requests.getBarbers()
    service = await db_requests.getServiceById(service_id)

    if not service:
        await callback.message.edit_text(
            "Ошибка: выбранная услуга не найдена. Пожалуйста, начните заново.",
            reply_markup=main_menu_keyboard
        )
        await callback.answer()
        return

    # Получаем список занятых мастеров в выбранную дату и время
    busy_barber_ids = await db_requests.get_busy_barbers_by_datetime(chosen_date, chosen_time_str)

    # Фильтруем доступных мастеров
    available_barbers = [barber for barber in barbers if barber.id not in busy_barber_ids]

    if not available_barbers:
        # Если нет свободных мастеров — показываем карточку с "Любым мастером"
        final_card_text, final_card_keyboard = get_final_booking_card_content(
            service_name=service.name,
            chosen_date=chosen_date,
            chosen_time=chosen_time_str,
            barber_name="Любой мастер",
            service_id=service_id,
            barber_id=None
        )
        await callback.message.edit_text(final_card_text, reply_markup=final_card_keyboard)
    else:
        # Показываем доступных мастеров для выбора
        await callback.message.edit_text(
            "Выберите мастера:",
            reply_markup=barbers_keyboard(available_barbers, chosen_date_str, chosen_time_str, service_id)
        )

    await callback.answer()



@appointment_router.callback_query(F.data.startswith("chooseBarber_"))
async def handlerChooseBarber(callback: CallbackQuery):
    """
    Обрабатывает выбор мастера и предлагает подтвердить запись.
    В callback.data ожидаем формат: "chooseBarber_{barber_id}_{YYYY-MM-DD}_{HH:MM}_{service_id}"
    barber_id может быть "any".
    """
    parts = callback.data.split("_")
    if len(parts) < 5:
        await callback.answer("Некорректные данные.", show_alert=True)
        return

    barber_id_str = parts[1]
    chosen_date_str = parts[2]
    chosen_time_str = parts[3]
    service_id = int(parts[4])

    barber_id = None if barber_id_str == "any" else int(barber_id_str)
    chosen_date = datetime.strptime(chosen_date_str, "%Y-%m-%d").date()

    service = await db_requests.getServiceById(service_id)
    if not service:
        await callback.message.edit_text(
            """Ошибка: выбранная услуга не найдена. Пожалуйста, начните заново.""",
            reply_markup=main_menu_keyboard
        )
        await callback.answer()
        return

    barber_name = "Любой мастер"
    if barber_id:
        barber = await db_requests.getBarberById(barber_id)
        if barber:
            barber_name = barber.name

    final_card_text, final_card_keyboard = get_final_booking_card_content(
        service_name=service.name,
        chosen_date=chosen_date,
        chosen_time=chosen_time_str,
        barber_name=barber_name,
        service_id=service_id,
        barber_id=barber_id
    )
    await callback.message.edit_text(final_card_text, reply_markup=final_card_keyboard)
    await callback.answer()



@appointment_router.callback_query(F.data.startswith("confirmBooking_"))
async def handlerConfirmFinalBooking(callback: CallbackQuery):
    await callback.answer()

    parts = callback.data.split("_")
    if len(parts) < 5:
        await callback.message.edit_text("Ошибка: некорректные данные для подтверждения.")
        return

    try:
        service_id = int(parts[1])
        chosen_date = datetime.strptime(parts[2], "%Y-%m-%d").date()
        chosen_time = parts[3]
        barber_id = int(parts[4]) if parts[4] != 'None' else None

        user_id = callback.from_user.id

        # Сохраняем запись в БД
        new_booking = await db_requests.addBooking(
            user_id=user_id,
            service_id=service_id,
            barber_id=barber_id,
            booking_date=chosen_date,
            booking_time=chosen_time
        )

        # Получаем данные для подтверждения
        service = await db_requests.getServiceById(service_id)
        barber_name = "Любой мастер"
        if barber_id:
            barber = await db_requests.getBarberById(barber_id)
            if barber:
                barber_name = barber.name

        # Формируем текст подтверждения с HTML
        confirmation_text = (
            "✅ <b>Подтверждение записи</b>\n"
            "➖➖➖➖➖➖➖➖➖➖\n"
            f"<b>Услуга:</b> {service.name}\n"
            f"<b>Дата:</b> {chosen_date.strftime('%d.%m.%Y')}\n"
            f"<b>Время:</b> {chosen_time}\n"
            f"<b>Мастер:</b> {barber_name}\n"
            "➖➖➖➖➖➖➖➖➖➖\n"
            "Ваша запись успешно создана!"
        )

        # Редактируем сообщение с подтверждением
        await callback.message.edit_text(confirmation_text, parse_mode="HTML")

        # Отправляем главное меню
        await callback.message.answer("Выберите действие из меню:", reply_markup=main_menu_keyboard)

    except (ValueError, IndexError) as e:
        print(f"Ошибка при обработке подтверждения: {e}")
        await callback.message.edit_text(
            "Произошла ошибка при сохранении вашей записи. Пожалуйста, попробуйте еще раз."
        )





@appointment_router.callback_query(F.data == "deleteBooking")
async def handlerDeleteFinalBooking(callback: CallbackQuery):
    """
    Отмена подтвержденной записи.
    """
    await callback.message.edit_text("Вы удалили запись.")
    await callback.message.answer("Вы вернулись в главное меню.", reply_markup=main_menu_keyboard)
    await callback.answer("Запись удалена.")


@appointment_router.callback_query(F.data == "cancelForm")
async def handlerCancelForm(callback: CallbackQuery):
    """
    Общий хэндлер для отмены.
    """
    await callback.message.edit_text("Заполнение отменено.")
    await callback.message.answer("Вы вернулись в главное меню.", reply_markup=main_menu_keyboard)
    await callback.answer("Отменено.")


@appointment_router.callback_query(F.data == "mainMenu")
async def handlerMainMenuInline(callback: CallbackQuery):
    """
    Возврат в главное меню.
    """
    await callback.message.edit_text("Вы вернулись в главное меню.")
    await callback.message.answer("Вы вернулись в главное меню.", reply_markup=main_menu_keyboard)
    await callback.answer("Главное меню.")


@appointment_router.callback_query(F.data == "ignore")
async def handlerIgnoreCallback(callback: CallbackQuery):
    """
    Пустая кнопка.
    """
    await callback.answer()


@appointment_router.callback_query(F.data == "backToMainMenu")
async def handlerBackToMainMenu(callback: CallbackQuery):
    """
    Возврат в главное меню.
    """
    await callback.message.edit_text("Вы вернулись в главное меню.")
    await callback.message.answer("Вы вернулись в главное меню.", reply_markup=main_menu_keyboard)
    await callback.answer("Главное меню.")

@appointment_router.callback_query(F.data.startswith("backToTime_"))
async def handlerBackToTime(callback: CallbackQuery):
    parts = callback.data.split("_")
    chosen_date_str = parts[1]
    service_id = int(parts[2])

    await callback.message.edit_text(
        f"""Вы выбрали {chosen_date_str}.\nВыберите время:""",
        reply_markup=time_slots_keyboard(chosen_date_str, service_id)
    )
    await callback.answer()

@appointment_router.callback_query(F.data == "cancelBooking")
async def handlerCancelBooking(callback: CallbackQuery):
    """
    Обрабатывает нажатие на кнопку 'Отменить' запись.
    """
    await callback.answer("Запись отменена.", show_alert=False)
    await callback.message.edit_text(
        "Вы отменили запись. Выберите следующее действие:",
        reply_markup=main_menu_keyboard
    )
