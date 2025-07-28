from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import date, datetime, timedelta
import calendar

from app.keyboards.kbreply import main_menu_keyboard
from app.keyboards.kbinline import services_keyboard, calendar_keyboard, time_slots_keyboard, get_final_booking_card_content, barbers_keyboard
from app.database import requests as db_requests
from app.database.models import Service, Booking, Barber
from config import AVAILABLE_TIME_SLOTS

appointment_router = Router()

class BookingState(StatesGroup):
    """Состояния для многошагового процесса записи на услугу."""
    choosingService = State()
    choosingDate = State()
    choosingTime = State()
    choosingBarber = State()
    confirmingBooking = State()


@appointment_router.message(F.text == "💈 Записаться")
async def handler_book_appointment(message: Message, state: FSMContext, session_maker: callable):
    """
    Начинает процесс записи на услугу.
    Проверяет регистрацию пользователя и предлагает выбрать услугу.
    """
    async with session_maker() as session:
        user = await db_requests.get_user(session, message.from_user.id)
        if not user or not user.first_name or not user.phone_number:
            await message.answer(
                "Для записи на стрижку необходимо пройти регистрацию. "
                "Пожалуйста, используйте команду /start для начала регистрации.",
                reply_markup=main_menu_keyboard
            )
            await state.clear()
            return

        services = await db_requests.get_services(session)
        if not services:
            await message.answer("Извините, пока нет доступных услуг. Пожалуйста, попробуйте позже.",
                                 reply_markup=main_menu_keyboard)
            await state.clear()
            return

        await message.answer("Выберите услугу:", reply_markup=services_keyboard(services))
        await state.set_state(BookingState.choosingService)


@appointment_router.callback_query(BookingState.choosingService, F.data.startswith("chooseService_"))
async def handler_choose_service(callback: CallbackQuery, state: FSMContext, session_maker: callable):
    """
    Обрабатывает выбор услуги.
    Сохраняет выбранную услугу и предлагает выбрать дату.
    """
    service_id = int(callback.data.split("_")[1])

    async with session_maker() as session:
        service = await db_requests.get_service_by_id(session, service_id)
        if not service:
            all_services = await db_requests.get_services(session)
            await callback.message.edit_text("Услуга не найдена. Пожалуйста, выберите другую.",
                                             reply_markup=services_keyboard(all_services))
            await callback.answer("Ошибка: услуга не найдена.", show_alert=True)
            return

    await state.update_data(chosen_service_id=service_id, chosen_service_name=service.name)
    await callback.message.edit_text("Выберите дату:", reply_markup=calendar_keyboard())
    await state.set_state(BookingState.choosingDate)
    await callback.answer()


@appointment_router.callback_query(BookingState.choosingDate, F.data.startswith("navigateMonth_"))
async def handler_navigate_month(callback: CallbackQuery, state: FSMContext):
    """
    Обрабатывает навигацию по месяцам в календаре.
    """
    new_month_str = callback.data.split("_")[1]
    new_date = datetime.strptime(new_month_str, "%Y-%m").date()
    await callback.message.edit_reply_markup(reply_markup=calendar_keyboard(new_date))
    await callback.answer()


@appointment_router.callback_query(BookingState.choosingDate, F.data.startswith("navigateYear_"))
async def handler_navigate_year(callback: CallbackQuery, state: FSMContext):
    """
    Обрабатывает навигацию по годам в календаре.
    """
    new_year = int(callback.data.split("_")[1])
    current_state_data = await state.get_data()
    current_calendar_date = current_state_data.get('calendar_display_date', date.today())
    new_date = current_calendar_date.replace(year=new_year)
    await state.update_data(calendar_display_date=new_date)
    await callback.message.edit_reply_markup(reply_markup=calendar_keyboard(new_date))
    await callback.answer()


@appointment_router.callback_query(BookingState.choosingDate, F.data.startswith("chooseDate_"))
async def handler_choose_date(callback: CallbackQuery, state: FSMContext, session_maker: callable):
    """
    Обрабатывает выбор даты.
    Сохраняет выбранную дату и предлагает выбрать время.
    """
    chosen_date_str = callback.data.split("_")[1]
    chosen_date = datetime.strptime(chosen_date_str, "%Y-%m-%d").date()

    if chosen_date < date.today():
        await callback.answer("Нельзя выбрать прошедшую дату. Пожалуйста, выберите другую дату.", show_alert=True)
        return

    await state.update_data(chosen_date=chosen_date)

    await callback.message.edit_text(
        f"Вы выбрали {chosen_date.strftime('%d.%m.%Y')}.\nВыберите время:",
        reply_markup=time_slots_keyboard(AVAILABLE_TIME_SLOTS)
    )
    await state.set_state(BookingState.choosingTime)
    await callback.answer()


@appointment_router.callback_query(BookingState.choosingTime, F.data.startswith("chooseTime_"))
async def handler_choose_time(callback: CallbackQuery, state: FSMContext, session_maker: callable):
    """
    Обрабатывает выбор времени.
    Сохраняет выбранное время и предлагает выбрать мастера.
    """
    chosen_time_str = callback.data.split("_")[1]
    user_data = await state.get_data()
    chosen_date: date = user_data.get('chosen_date')
    chosen_service_id: int = user_data.get('chosen_service_id')
    chosen_service_name: str = user_data.get('chosen_service_name')

    if not chosen_date or not chosen_service_id:
        await callback.message.edit_text("Произошла ошибка. Пожалуйста, начните запись заново.",
                                         reply_markup=main_menu_keyboard)
        await state.clear()
        await callback.answer("Ошибка: неполные данные.", show_alert=True)
        return

    booking_datetime = datetime.combine(chosen_date, datetime.strptime(chosen_time_str, "%H:%M").time())

    await state.update_data(
        chosen_time=chosen_time_str,
        booking_datetime=booking_datetime
    )

    async with session_maker() as session:
        barbers = await db_requests.get_barbers(session)
        if not barbers:
            # Если нет доступных мастеров, сразу к подтверждению с "Любым мастером"
            await state.update_data(barber_id=None, barber_name="Любой мастер")
            final_card_text, final_card_keyboard = get_final_booking_card_content(
                service_name=chosen_service_name,
                chosen_date=chosen_date,
                chosen_time=chosen_time_str,
                barber_name="Любой мастер"
            )
            await callback.message.edit_text(final_card_text, reply_markup=final_card_keyboard)
            await state.set_state(BookingState.confirmingBooking)
        else:
            await callback.message.edit_text(
                "Выберите мастера:",
                reply_markup=barbers_keyboard(barbers)
            )
            await state.set_state(BookingState.choosingBarber)
    await callback.answer()

@appointment_router.callback_query(BookingState.choosingBarber, F.data.startswith("chooseBarber_"))
async def handler_choose_barber(callback: CallbackQuery, state: FSMContext, session_maker: callable):
    """
    Обрабатывает выбор мастера.
    Сохраняет выбранного мастера и переходит к подтверждению записи.
    """
    barber_id_str = callback.data.split("_")[1]
    barber_id = int(barber_id_str) if barber_id_str != "any" else None

    user_data = await state.get_data()
    chosen_service_name: str = user_data.get('chosen_service_name')
    chosen_date: date = user_data.get('chosen_date')
    chosen_time_str: str = user_data.get('chosen_time')
    booking_datetime: datetime = user_data.get('booking_datetime')

    barber_name = "Любой мастер"
    if barber_id:
        async with session_maker() as session:
            barber = await db_requests.get_barber_by_id(session, barber_id)
            if barber:
                barber_name = barber.name

    await state.update_data(barber_id=barber_id, barber_name=barber_name)

    final_card_text, final_card_keyboard = get_final_booking_card_content(
        service_name=chosen_service_name,
        chosen_date=chosen_date,
        chosen_time=chosen_time_str,
        barber_name=barber_name
    )

    await callback.message.edit_text(final_card_text, reply_markup=final_card_keyboard)
    await state.set_state(BookingState.confirmingBooking)
    await callback.answer()


@appointment_router.callback_query(BookingState.confirmingBooking, F.data == "confirmBooking")
async def handler_confirm_final_booking(callback: CallbackQuery, state: FSMContext, session_maker: callable):
    """
    Подтверждает и создает финальную запись в БД.
    """
    user_data = await state.get_data()
    user_id = callback.from_user.id
    service_id = user_data.get('chosen_service_id')
    booking_datetime = user_data.get('booking_datetime')
    barber_id = user_data.get('barber_id')
    chosen_service_name = user_data.get('chosen_service_name')
    barber_name = user_data.get('barber_name')

    if not service_id or not booking_datetime:
        await callback.message.edit_text("Ошибка при подтверждении записи. Пожалуйста, попробуйте снова.",
                                         reply_markup=main_menu_keyboard)
        await state.clear()
        await callback.answer("Ошибка: неполные данные для записи.", show_alert=True)
        return

    async with session_maker() as session:
        try:
            new_booking = await db_requests.create_booking(
                session,
                user_id=user_id,
                service_id=service_id,
                booking_date=booking_datetime,
                barber_id=barber_id
            )
            await callback.message.edit_text(
                f"🎉 Вы успешно записались!\n"
                f"Я отправлю Вам напоминание за два часа до стрижки.\n\n"
                f"Услуга: <b>{chosen_service_name}</b>\n"
                f"Дата: <b>{new_booking.booking_date.strftime('%d.%m.%Y')}</b>\n"
                f"Время: <b>{new_booking.booking_date.strftime('%H:%M')}</b>\n"
                f"Мастер: <b>{barber_name}</b>\n\n"
                f"Остаются фото и данные записи."
            )
            await callback.message.answer("Вы вернулись в главное меню.", reply_markup=main_menu_keyboard)
        except Exception as e:
            print(f"Ошибка при создании записи: {e}")
            await callback.message.edit_text("Произошла ошибка при создании записи. Пожалуйста, попробуйте позже.",
                                             reply_markup=main_menu_keyboard)
            await callback.answer("Ошибка записи.", show_alert=True)
        finally:
            await state.clear()


@appointment_router.callback_query(BookingState.confirmingBooking, F.data == "deleteBooking")
async def handler_delete_final_booking(callback: CallbackQuery, state: FSMContext):
    """
    Обрабатывает отмену финального подтверждения записи.
    """
    await callback.message.edit_text("Вы удалили запись.")
    await callback.message.answer("Вы вернулись в главное меню.", reply_markup=main_menu_keyboard)
    await state.clear()
    await callback.answer("Запись удалена.")


@appointment_router.callback_query(F.data == "cancelForm")
async def handler_cancel_form(callback: CallbackQuery, state: FSMContext):
    """
    Общий хэндлер для отмены заполнения любой формы.
    """
    await state.clear()
    await callback.message.edit_text("Заполнение отменено.", reply_markup=main_menu_keyboard)
    await callback.answer("Отменено.")


@appointment_router.callback_query(F.data == "mainMenu")
async def handler_main_menu_inline(callback: CallbackQuery, state: FSMContext):
    """
    Обрабатывает возврат в главное меню из Inline-клавиатуры.
    """
    await state.clear()
    await callback.message.edit_text("Вы вернулись в главное меню.", reply_markup=main_menu_keyboard)
    await callback.answer("Главное меню.")


@appointment_router.callback_query(F.data == "ignore")
async def handler_ignore_callback(callback: CallbackQuery):
    """
    Хэндлер для "пустых" кнопок, которые ничего не делают.
    """
    await callback.answer()


@appointment_router.callback_query(BookingState.choosingDate, F.data == "skipDate")
async def handler_skip_date(callback: CallbackQuery, state: FSMContext):
    """
    Обрабатывает пропуск выбора даты.
    """
    await state.clear()
    await callback.message.edit_text("Вы пропустили выбор даты. Возвращаемся в главное меню.",
                                     reply_markup=main_menu_keyboard)
    await callback.answer()


@appointment_router.callback_query(F.data == "backToMainMenu")
async def handler_back_to_main_menu(callback: CallbackQuery, state: FSMContext):
    """
    Обрабатывает возврат в главное меню.
    """
    await state.clear()
    await callback.message.edit_text("Вы вернулись в главное меню.", reply_markup=main_menu_keyboard)
    await callback.answer()


@appointment_router.callback_query(F.data == "backToServices")
async def handler_back_to_services(callback: CallbackQuery, state: FSMContext, session_maker: callable):
    """
    Обрабатывает возврат к выбору услуги.
    """
    async with session_maker() as session:
        services = await db_requests.get_services(session)
        await callback.message.edit_text("Выберите услугу:", reply_markup=services_keyboard(services))
        await state.set_state(BookingState.choosingService)
        await callback.answer()


@appointment_router.callback_query(F.data == "backToDateSelection")
async def handler_back_to_date_selection(callback: CallbackQuery, state: FSMContext):
    """
    Обрабатывает возврат к выбору даты.
    """
    current_state_data = await state.get_data()
    display_date = current_state_data.get('calendar_display_date', date.today())
    await callback.message.edit_text("Выберите дату:", reply_markup=calendar_keyboard(display_date))
    await state.set_state(BookingState.choosingDate)
    await callback.answer()

@appointment_router.callback_query(F.data == "backToTimeSelection")
async def handler_back_to_time_selection(callback: CallbackQuery, state: FSMContext):
    """
    Обрабатывает возврат к выбору времени.
    """
    await callback.message.edit_text(
        "Выберите время:",
        reply_markup=time_slots_keyboard(AVAILABLE_TIME_SLOTS)
    )
    await state.set_state(BookingState.choosingTime)
    await callback.answer()