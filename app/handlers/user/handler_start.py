# app/handlers/user/handler_start.py
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.keyboards.kbreply import main_menu_keyboard
from app.keyboards.kbinline import continue_registration_keyboard
from app.database import requests as db_requests  # Импортируем db_requests

start_router = Router()


class RegistrationState(StatesGroup):
    waitingForName = State()
    waitingForPhone = State()


@start_router.message(CommandStart())
async def handlerStart(message: Message, state: FSMContext):  # session_maker удален из сигнатуры
    """
    Обрабатывает команду /start.
    Проверяет регистрацию пользователя и предлагает зарегистрироваться или показывает главное меню.
    """
    user = await db_requests.getUser(message.from_user.id)  # ИСПРАВЛЕНО: session_maker удален из вызова

    reply_kb = main_menu_keyboard

    if not user or not user.first_name or not user.phone_number:
        await message.answer(
            """Привет! 👋 Добро пожаловать в наш барбершоп!
Мы предлагаем лучшие стрижки и бритье в городе.
Чтобы записаться, пожалуйста, пройдите быструю регистрацию.""",
            reply_markup=continue_registration_keyboard
        )
        await state.set_state(RegistrationState.waitingForName)
    else:
        await message.answer(
            f"С возвращением, {user.first_name}! 👋",
            reply_markup=reply_kb
        )