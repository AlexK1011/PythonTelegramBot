from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

Keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("добавить канал", callback_data="add_channel"), InlineKeyboardButton("список каналов", callback_data="list_channels")],

])


channels_list = []

def register_handlers(client):
    @client.on_message(filters.command("start"))
    async def start(client, message):
        await message.reply("Hello, I'm a bot!", reply_markup=Keyboard)


    @client.on_message(filters.forwarded)
    async def echo(client, message):
        global channels_list
        if message.forward_from_chat and message.forward_from_chat.id not in channels_list:
            channels_list.append({
                "id": message.forward_from_chat.id,
                "title": message.forward_from_chat.title or "Без названия"
            })
            await message.reply(
                f"Канал {message.forward_from_chat.title} добавлен!",
                reply_markup=Keyboard
            )

    @client.on_callback_query()
    async def handle_callback(client, callback_query: CallbackQuery):
        data = callback_query.data

        if data == "add_channel":
            await callback_query.answer("Перешлите сообщение из канала, который нужно добавить")

        elif data == "list_channels":
            if not channels_list:
                text = "Список каналов пуст"
            else:
                text = "Добавленные каналы:\n" + "\n".join(
                    f"• {channel['title']} (ID: {channel['id']})"
                    for channel in channels_list
                )

            await callback_query.message.edit_text(
                text,
                reply_markup=Keyboard
            )

