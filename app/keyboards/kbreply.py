from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

main_menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💈 Записаться")],
        [KeyboardButton(text="🗓 Мои записи"), KeyboardButton(text="ℹ️ О нас")],
        [KeyboardButton(text="📞 Поддержка")]
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите действие..."
)

cancel_booking_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Отменить запись")]
    ],
    resize_keyboard=True,
    input_field_placeholder="Подтвердите отмену..."
)

request_contact_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Поделиться контактом", request_contact=True)]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)