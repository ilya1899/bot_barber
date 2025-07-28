from aiogram import Router, F
from aiogram.types import Message

from app.keyboards.kbreply import main_menu_keyboard
from app.keyboards.kbinline import support_inline_keyboard

support_router = Router()

@support_router.message(F.text == "📞 Поддержка")
async def handler_support(message: Message):
    manager_username = "YourSupportUsername"

    support_text = (
        """У Вас возникла проблема? Не работает бот? Не получается записаться? Обратитесь в поддержку!"""
    )
    await message.answer(support_text, reply_markup=support_inline_keyboard(manager_username))