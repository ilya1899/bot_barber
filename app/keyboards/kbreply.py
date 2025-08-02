from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Клавиатура для запроса контакта
request_contact_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Поделиться контактом", request_contact=True)]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

# Главное меню
main_menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💈 Записаться"), KeyboardButton(text="🗓 Мои записи")],
        [KeyboardButton(text="ℹ️ Подробнее об услугах"), KeyboardButton(text="📞 Поддержка")]
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите действие из меню",
    one_time_keyboard=True
)

admin_menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Услуги"), KeyboardButton(text="Мастера")],
        [KeyboardButton(text="Статистика"), KeyboardButton(text='Календарь')],
        [KeyboardButton(text="⬅️ Выйти из админ-панели")]
    ],
    resize_keyboard=True,
    input_field_placeholder="Админ-панель"
)