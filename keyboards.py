from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton
)

# Главное меню (инлайн-клавиатура)
Keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="Добавить канал", callback_data="add_channel"),
        InlineKeyboardButton(text="Удалить канал", callback_data="delete_channel")
    ],
    [
        InlineKeyboardButton(text="Список каналов", callback_data="list_channels")
    ],
    [
        InlineKeyboardButton(text="Настройки", callback_data="settings")
    ]
])

settings = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="задержка", callback_data="delay"), InlineKeyboardButton(text="репосты", callback_data="reposts")
    ]
])

# Клавиатура подтверждения добавления канала
add_or_not = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="Да", callback_data="confirm_add_channel"),
        InlineKeyboardButton(text="Нет", callback_data="dont_add")
    ]
])