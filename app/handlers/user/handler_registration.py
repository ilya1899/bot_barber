# app/handlers/user/handler_registration.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.keyboards.kbreply import request_contact_keyboard, main_menu_keyboard
from app.keyboards.kbinline import continue_registration_keyboard
from app.database import requests as db_requests

registration_router = Router()

class RegistrationState(StatesGroup):
    waitingForName = State()
    waitingForPhone = State()

@registration_router.callback_query(F.data == "continueRegistration")
async def handlerContinueRegistration(callback: CallbackQuery, state: FSMContext):
    """
    Обрабатывает нажатие кнопки "Продолжить регистрацию".
    Запрашивает имя пользователя.
    """
    await callback.message.edit_text("Отлично! Как вас зовут? Напишите ваше имя:")
    await state.set_state(RegistrationState.waitingForName)
    await callback.answer()

@registration_router.message(RegistrationState.waitingForName)
async def handlerGetName(message: Message, state: FSMContext):
    """
    Обрабатывает ввод имени пользователя.
    Запрашивает номер телефона.
    """
    user_name = message.text.strip()
    if not user_name:
        await message.answer("Пожалуйста, введите ваше имя.")
        return

    await state.update_data(registrationName=user_name) # camelCase для ключа в state
    await message.answer(
        f"Приятно познакомиться, {user_name}!\n"
        "Теперь, пожалуйста, поделитесь своим номером телефона, чтобы мы могли с вами связаться.",
        reply_markup=request_contact_keyboard
    )
    await state.set_state(RegistrationState.waitingForPhone)

@registration_router.message(RegistrationState.waitingForPhone, F.contact)
async def handlerGetPhone(message: Message, state: FSMContext): # session_maker удален
    """
    Обрабатывает получение номера телефона пользователя через кнопку "Поделиться контактом".
    Завершает регистрацию и сохраняет данные в БД.
    """
    phone_number = message.contact.phone_number
    user_id = message.from_user.id
    user_data = await state.get_data()
    user_name = user_data.get('registrationName', message.from_user.first_name) # camelCase для ключа

    # Вызовы db_requests без передачи сессии
    user = await db_requests.addUser(
        user_id=user_id,
        username=message.from_user.username,
        firstName=user_name,
        lastName=message.from_user.last_name
    )
    await db_requests.updateUserPhone(user_id, phone_number)

    await message.answer(
        "Вы успешно зарегистрированы! 🎉\n"
        "Теперь можете почитать подробнее об услугах и записаться на стрижку.",
        reply_markup=main_menu_keyboard
    )
    await state.clear()

@registration_router.message(RegistrationState.waitingForPhone)
async def handlerGetPhoneText(message: Message):
    """
    Обрабатывает некорректный ввод, когда ожидается номер телефона.
    """
    await message.answer("Пожалуйста, нажмите кнопку 'Поделиться контактом' или введите корректный номер телефона.")