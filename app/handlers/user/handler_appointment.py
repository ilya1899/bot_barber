from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from datetime import date, datetime
import calendar

from app.keyboards.kbreply import main_menu_keyboard
from app.keyboards.kbinline import (
    services_keyboard,
    calendar_keyboard,
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

    # Отправляем сообщение с календарём и callback_data для состояния choosingDate
    await callback.message.edit_text(
        """Выберите дату для записи:""",
        reply_markup=calendar_keyboard()
    )
    await callback.answer("Начинаем запись на выбранную услугу.")


@appointment_router.callback_query(F.data.startswith("navigateMonth_"))
async def handlerNavigateMonth(callback: CallbackQuery):
    """
    Навигация по месяцам в календаре.
    """
    new_month_str = callback.data.split("_")[1]
    new_date = datetime.strptime(new_month_str, "%Y-%m").date()
    await callback.message.edit_reply_markup(reply_markup=calendar_keyboard(new_date))
    await callback.answer()


@appointment_router.callback_query(F.data.startswith("navigateYear_"))
async def handlerNavigateYear(callback: CallbackQuery):
    """
    Навигация по годам в календаре.
    """
    new_year = int(callback.data.split("_")[1])
    # В callback_data лучше всегда передавать актуальную дату для показа
    # Здесь для простоты используем текущую дату
    current_date = date.today()
    try:
        new_date = current_date.replace(year=new_year)
    except ValueError:
        # На случай 29 февраля
        new_date = current_date.replace(year=new_year, day=28)
    await callback.message.edit_reply_markup(reply_markup=calendar_keyboard(new_date))
    await callback.answer()


@appointment_router.callback_query(F.data.startswith("chooseDate_"))
async def handlerChooseDate(callback: CallbackQuery):
    """
    Обрабатывает выбор даты и предлагает выбрать время.
    """
    chosen_date_str = callback.data.split("_")[1]
    chosen_date = datetime.strptime(chosen_date_str, "%Y-%m-%d").date()

    if chosen_date < date.today():
        await callback.answer(
            """Нельзя выбрать прошедшую дату. Пожалуйста, выберите другую дату.""",
            show_alert=True
        )
        return

    await callback.message.edit_text(
        f"""Вы выбрали {chosen_date.strftime('%d.%m.%Y')}.\nВыберите время:""",
        reply_markup=time_slots_keyboard(AVAILABLE_TIME_SLOTS)
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

    chosen_date = datetime.strptime(chosen_date_str, "%Y-%m-%d").date()

    barbers = await db_requests.getBarbers()
    service = await db_requests.getServiceById(service_id)
    if not service:
        await callback.message.edit_text(
            """Ошибка: выбранная услуга не найдена. Пожалуйста, начните заново.""",
            reply_markup=main_menu_keyboard
        )
        await callback.answer()
        return

    if not barbers:
        # Нет доступных мастеров — сразу к подтверждению с "Любым мастером"
        final_card_text, final_card_keyboard = get_final_booking_card_content(
            service_name=service.name,
            chosen_date=chosen_date,
            chosen_time=chosen_time_str,
            barber_name="Любой мастер"
        )
        await callback.message.edit_text(final_card_text, reply_markup=final_card_keyboard)
    else:
        # Предлагаем выбрать мастера
        await callback.message.edit_text(
            """Выберите мастера:""",
            reply_markup=barbers_keyboard(barbers)
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
        barber_name=barber_name
    )
    await callback.message.edit_text(final_card_text, reply_markup=final_card_keyboard)
    await callback.answer()


@appointment_router.callback_query(F.data == "confirmBooking")
async def handlerConfirmFinalBooking(callback: CallbackQuery):
    """
    Создает запись в БД по подтверждению.
    В callback.message.text содержится информация для подтверждения,
    либо можно передавать дополнительные данные через callback_data или context.
    Здесь пример с передачей данных через callback_data не реализован —
    нужно доработать под твои нужды.
    """
    user_id = callback.from_user.id

    # Здесь нужно получить service_id, booking_datetime, barber_id из контекста.
    # Поскольку мы отказались от FSMContext, для хранения данных можно использовать что-то другое:
    # например, временный кэш в памяти, БД, Redis, или информацию из callback_data.
    # Ниже — заглушка с ошибкой, так как данных нет:
    await callback.answer(
        """Ошибка: нет данных для создания записи. 
Пожалуйста, начните процесс записи заново.""",
        show_alert=True
    )
    await callback.message.edit_text(
        """Произошла ошибка при создании записи. Пожалуйста, попробуйте снова.""",
        reply_markup=main_menu_keyboard
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
