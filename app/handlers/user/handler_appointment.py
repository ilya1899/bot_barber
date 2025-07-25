from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import date, datetime, timedelta
import calendar

from app.keyboards.kbreply import main_menu_keyboard
from app.keyboards.kbinline import services_keyboard, calendar_keyboard, time_slots_keyboard, menu_inline_button, \
    get_final_booking_card_content
from app.database import requests as db_requests
from app.database.models import Service, Booking, Barber

appointment_router = Router()


class BookingState(StatesGroup):
    choosing_service = State()
    choosing_date = State()
    choosing_time = State()
    confirming_booking = State()
    choosing_barber = State()


@appointment_router.message(F.text == "💈 Записаться")
async def handler_book_appointment(message: Message, state: FSMContext, session_maker: callable):
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
        await state.set_state(BookingState.choosing_service)


@appointment_router.callback_query(BookingState.choosing_service, F.data.startswith("service_"))
async def handler_choose_service(callback: CallbackQuery, state: FSMContext, session_maker: callable):
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
    await state.set_state(BookingState.choosing_date)
    await callback.answer()


@appointment_router.callback_query(BookingState.choosing_date, F.data.startswith("calendar_month_"))
async def handler_navigate_month(callback: CallbackQuery, state: FSMContext):
    new_month_str = callback.data.split("_")[2]
    new_date = datetime.strptime(new_month_str, "%Y-%m").date()
    await callback.message.edit_reply_markup(reply_markup=calendar_keyboard(new_date))
    await callback.answer()


@appointment_router.callback_query(BookingState.choosing_date, F.data.startswith("calendar_year_"))
async def handler_navigate_year(callback: CallbackQuery, state: FSMContext):
    new_year = int(callback.data.split("_")[2])
    current_state_data = await state.get_data()
    current_calendar_date = current_state_data.get('calendar_display_date', date.today())
    new_date = current_calendar_date.replace(year=new_year)
    await state.update_data(calendar_display_date=new_date)
    await callback.message.edit_reply_markup(reply_markup=calendar_keyboard(new_date))
    await callback.answer()


@appointment_router.callback_query(BookingState.choosing_date, F.data.startswith("calendar_date_"))
async def handler_choose_date(callback: CallbackQuery, state: FSMContext, session_maker: callable):
    chosen_date_str = callback.data.split("_")[2]
    chosen_date = datetime.strptime(chosen_date_str, "%Y-%m-%d").date()

    if chosen_date < date.today():
        await callback.answer("Нельзя выбрать прошедшую дату. Пожалуйста, выберите другую дату.", show_alert=True)
        return

    await state.update_data(chosen_date=chosen_date)

    available_times = ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00"]

    await callback.message.edit_text(
        f"Вы выбрали {chosen_date.strftime('%d.%m.%Y')}.\nВыберите время:",
        reply_markup=time_slots_keyboard(available_times)
    )
    await state.set_state(BookingState.choosing_time)
    await callback.answer()


@appointment_router.callback_query(BookingState.choosing_time, F.data.startswith("time_select_"))
async def handler_choose_time(callback: CallbackQuery, state: FSMContext, session_maker: callable):
    chosen_time_str = callback.data.split("_")[2]
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

    barber_id = None
    barber_name = "Любой мастер"

    await state.update_data(
        chosen_time=chosen_time_str,
        booking_datetime=booking_datetime,
        barber_id=barber_id,
        barber_name=barber_name
    )

    final_card_text, final_card_keyboard = get_final_booking_card_content(
        service_name=chosen_service_name,
        chosen_date=chosen_date,
        chosen_time=chosen_time_str,
        barber_name=barber_name
    )

    await callback.message.edit_text(final_card_text, reply_markup=final_card_keyboard)
    await state.set_state(BookingState.confirming_booking)
    await callback.answer()


@appointment_router.callback_query(BookingState.confirming_booking, F.data == "confirm_final_booking")
async def handler_confirm_final_booking(callback: CallbackQuery, state: FSMContext, session_maker: callable):
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


@appointment_router.callback_query(BookingState.confirming_booking, F.data == "delete_final_booking")
async def handler_delete_final_booking(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Вы удалили запись.")
    await callback.message.answer("Вы вернулись в главное меню.", reply_markup=main_menu_keyboard)
    await state.clear()
    await callback.answer("Запись удалена.")


@appointment_router.callback_query(F.data == "cancel_form")
async def handler_cancel_form(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Заполнение отменено.", reply_markup=main_menu_keyboard)
    await callback.answer("Отменено.")


@appointment_router.callback_query(F.data == "main_menu")
async def handler_main_menu_inline(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Вы вернулись в главное меню.", reply_markup=main_menu_keyboard)
    await callback.answer("Главное меню.")


@appointment_router.callback_query(F.data == "ignore")
async def handler_ignore_callback(callback: CallbackQuery):
    await callback.answer()


@appointment_router.callback_query(BookingState.choosing_date, F.data == "skip_date")
async def handler_skip_date(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Вы пропустили выбор даты. Возвращаемся в главное меню.",
                                     reply_markup=main_menu_keyboard)
    await callback.answer()


@appointment_router.callback_query(F.data == "back_to_main_menu")
async def handler_back_to_main_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Вы вернулись в главное меню.", reply_markup=main_menu_keyboard)
    await callback.answer()


@appointment_router.callback_query(F.data == "back_to_services")
async def handler_back_to_services(callback: CallbackQuery, state: FSMContext, session_maker: callable):
    async with session_maker() as session:
        services = await db_requests.get_services(session)
        await callback.message.edit_text("Выберите услугу:", reply_markup=services_keyboard(services))
        await state.set_state(BookingState.choosing_service)
        await callback.answer()


@appointment_router.callback_query(F.data == "back_to_date_selection")
async def handler_back_to_date_selection(callback: CallbackQuery, state: FSMContext):
    current_state_data = await state.get_data()
    display_date = current_state_data.get('calendar_display_date', date.today())
    await callback.message.edit_text("Выберите дату:", reply_markup=calendar_keyboard(display_date))
    await state.set_state(BookingState.choosing_date)
    await callback.answer()