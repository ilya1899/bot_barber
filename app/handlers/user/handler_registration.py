from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.keyboards.kbreply import request_contact_keyboard, main_menu_keyboard
from app.keyboards.kbinline import continue_registration_keyboard
from app.database import requests as db_requests

registration_router = Router()

class RegistrationState(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()

@registration_router.callback_query(F.data == "continue_registration")
async def handler_continue_registration(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Отлично! Как вас зовут? Напишите ваше имя:")
    await state.set_state(RegistrationState.waiting_for_name)
    await callback.answer()

@registration_router.message(RegistrationState.waiting_for_name)
async def handler_get_name(message: Message, state: FSMContext):
    user_name = message.text.strip()
    if not user_name:
        await message.answer("Пожалуйста, введите ваше имя.")
        return

    await state.update_data(registration_name=user_name)
    await message.answer(
        f"Приятно познакомиться, {user_name}!\n"
        "Теперь, пожалуйста, поделитесь своим номером телефона, чтобы мы могли с вами связаться.",
        reply_markup=request_contact_keyboard
    )
    await state.set_state(RegistrationState.waiting_for_phone)

@registration_router.message(RegistrationState.waiting_for_phone, F.contact)
async def handler_get_phone(message: Message, state: FSMContext, session_maker: callable):
    phone_number = message.contact.phone_number
    user_id = message.from_user.id
    user_data = await state.get_data()
    user_name = user_data.get('registration_name', message.from_user.first_name)

    async with session_maker() as session:
        user = await db_requests.add_user(
            session,
            user_id=user_id,
            username=message.from_user.username,
            first_name=user_name,
            last_name=message.from_user.last_name
        )
        await db_requests.update_user_phone(session, user_id, phone_number)

    await message.answer(
        "Вы успешно зарегистрированы! 🎉\n"
        "Теперь можете почитать подробнее об услугах и записаться на стрижку.",
        reply_markup=main_menu_keyboard
    )
    await state.clear()

@registration_router.message(RegistrationState.waiting_for_phone)
async def handler_get_phone_text(message: Message):
    await message.answer("Пожалуйста, нажмите кнопку 'Поделиться контактом' или введите корректный номер телефона.")