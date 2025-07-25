from aiogram import Router, F
from aiogram.types import Message

from app.keyboards.kbreply import main_menu_keyboard

about_us_router = Router()

@about_us_router.message(F.text == "ℹ️ О нас")
async def handler_about_us(message: Message):
    about_text = (
        "<b>💈 Наш Барбершоп</b>\n\n"
        "Мы предлагаем широкий спектр услуг по уходу за волосами и бородой для мужчин.\n"
        "Наши мастера - настоящие профессионалы своего дела, которые любят свою работу.\n\n"
        "📍 <b>Адрес:</b> Ул. Примерная, д. 10, Город N\n"
        "⏰ <b>Часы работы:</b> Ежедневно с 09:00 до 21:00\n"
        "📞 <b>Телефон:</b> +7 (XXX) XXX-XX-XX\n\n"
        "Ждем вас!"
    )
    await message.answer(about_text, reply_markup=main_menu_keyboard)