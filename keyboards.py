from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton
)

Keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="Удалить канал", callback_data="delete_channel")
    ],
    [
        InlineKeyboardButton(text="Список каналов", callback_data="list_channels")
    ],
    [
        InlineKeyboardButton(text="Настройки", callback_data="settings")
    ]
])

settings_delayed_check = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="1", callback_data="delay"),
        InlineKeyboardButton(text="2", callback_data="reposts"),
        InlineKeyboardButton(text="3", callback_data="enable_ai")
    ],
    [
        InlineKeyboardButton(text="сменить режим", callback_data="change_mode")
    ],
    [
        InlineKeyboardButton(text="назад", callback_data="back_to_main")
    ]
])

settings_periodic_collection = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="1", callback_data="interval"),
        InlineKeyboardButton(text="2", callback_data="number_of_posts"),
        InlineKeyboardButton(text="3", callback_data="enable_ai"),
    ],
    [
        InlineKeyboardButton(text="сменить режим", callback_data="change_mode")
    ],
    [
        InlineKeyboardButton(text="назад", callback_data="back_to_main")
    ]
])

add_or_not = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="Да", callback_data="confirm_add_channel"),
        InlineKeyboardButton(text="Нет", callback_data="dont_add")
    ]
])

back_to_main = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="назад", callback_data="back_to_main")
    ]
])

change_mode = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="Отложенная проверка", callback_data="delayed_check"),
        InlineKeyboardButton(text="Периодический сбор", callback_data="periodic_collection")
    ],
    [
        InlineKeyboardButton(text="назад", callback_data="back_to_main")
    ]
])

back_to_settings = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="назад", callback_data="settings")
    ]
])
