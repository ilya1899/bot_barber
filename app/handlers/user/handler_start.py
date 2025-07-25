from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.keyboards.kbreply import main_menu_keyboard
from app.keyboards.kbinline import continue_registration_keyboard
from app.database import requests as db_requests

start_router = Router()

class RegistrationState(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()

@start_router.message(CommandStart())
async def handler_start(message: Message, session_maker: callable, state: FSMContext):
    async with session_maker() as session:
        user = await db_requests.get_user(session, message.from_user.id)
        if not user or not user.first_name or not user.phone_number:
            await message.answer(
                """<b>Привет!</b> 👋 Добро пожаловать в наш барбершоп!
            Мы предлагаем <i>лучшие</i> стрижки и бритье в городе.
            Чтобы записаться, пожалуйста, пройдите быструю регистрацию.""",
                reply_markup=continue_registration_keyboard
            )
            await state.set_state(RegistrationState.waiting_for_name)
        else:
            await message.answer(
                f"С возвращением, {user.first_name}! 👋",
                reply_markup=main_menu_keyboard
            )
