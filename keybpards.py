from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

Keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("добавить канал", callback_data="add_channel"), InlineKeyboardButton("список каналов", callback_data="list_channels")],
    [InlineKeyboardButton("удалить канал", callback_data="delete_channel")]
])
add_or_not = InlineKeyboardMarkup([
    [InlineKeyboardButton("да", callback_data="confirm_add_channel"), InlineKeyboardButton("нет", callback_data="dont_add")],
])

delete_or_not = InlineKeyboardMarkup([
    [InlineKeyboardButton("да", callback_data="confirm_delete_channel"), InlineKeyboardButton("нет", callback_data="dont_delete")],
])