import os


import pyrogram
import sqlite3
import db
from keybpards import Keyboard, add_or_not

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from dotenv import load_dotenv


load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")


db.init_db()

bot = Client(
    "my_bot",
    bot_token=BOT_TOKEN,
    api_id=API_ID,
    api_hash=API_HASH
)

add_channel_mode = False
delete_channel_mode = False



channels_list = {
    "channel_id": '',
    "title": ''
}


@bot.on_message(filters.command("start"))
async def start(client, message):
    await message.reply("Hello, I'm a bot!", reply_markup=Keyboard)


@bot.on_message(filters.forwarded)
async def add_channel(client, message):
    global channels_list
    global add_channel_mode
    if not message.forward_from_chat or message.forward_from_chat.type.value != "channel":
        return
    if message.media_group_id:
        # Получаем все сообщения из этой медиа-группы
        messages = await client.get_media_group(message.chat.id, message.id)
        # Обрабатываем только первое сообщение
        if message.id != messages[0].id:
            return

    if add_channel_mode:
        if message.forward_from_chat and not db.channel_exists(message.forward_from_chat.id):
            db.add_channel(message.forward_from_chat.id, message.forward_from_chat.title or "Без названия")
            await message.reply(
                f"Канал {message.forward_from_chat.title} добавлен!",
                reply_markup=Keyboard
            )
        else:
            await message.reply(
                f"Канал {message.forward_from_chat.title} уже добавлен!",
                reply_markup=Keyboard
            )
        add_channel_mode = False
    else:
        channels_list = {
            "id": message.forward_from_chat.id,
            "title": message.forward_from_chat.title or "Без названия"
        }
        await message.reply("Вы пытаетесь добавить этот канал?", reply_markup=add_or_not)


def callback_data_filter(data):
    async def func(flt, _, query):
        return flt.data == query.data
    return filters.create(func, data=data)


@bot.on_callback_query(callback_data_filter("add_channel"))
async def adding_channel(client, callback_query: CallbackQuery):
    global add_channel_mode
    add_channel_mode = True
    await callback_query.answer("Перешлите сообщение из канала, который нужно добавить")


@bot.on_callback_query(callback_data_filter("list_channels"))
async def show_channels(client, callback_query: CallbackQuery):
    channels = db.get_channels()
    if not channels:
        text = "Список каналов пуст"
    else:
        channel_lines = []
        counter = 1
        for channel_id, title in channels:
            channel_lines.append(f"{counter}. {title}")
            counter += 1

        # Объединяем все строки
        text = "Сохраненные каналы:\n" + "\n".join(channel_lines)

    await callback_query.answer()  # Добавляем ответ на callback
    await callback_query.message.edit_text(
        text,
        reply_markup=Keyboard
    )


@bot.on_callback_query(callback_data_filter("dont_add"))
async def nothing(client, callback_query: CallbackQuery):
    global channels_list
    channels_list = {
        "id": '',
        "title": ''
    }
    await callback_query.answer("отменено")


@bot.on_callback_query(callback_data_filter("confirm_add_channel"))
async def confirm_add_channel(client, callback_query: CallbackQuery):
    global channels_list
    channel_id = channels_list["id"]
    title = channels_list["title"]
    if channel_id and title:  # Проверяем, что данные есть
        db.add_channel(channel_id, title)
        await callback_query.answer("Канал добавлен!")
        await callback_query.message.edit_text(
            f"Канал {title} добавлен!",
            reply_markup=Keyboard
        )
    else:
        await callback_query.answer("Нет данных для добавления канала")
    channels_list = {
        "id": '',
        "title": ''
    }

@bot.on_callback_query(callback_data_filter("delete_channel"))
async def start_deleting_channel(client, callback_query: CallbackQuery):
    channels = db.get_channels()
    if not channels:
        text = "Список каналов пуст"
    else:
        channel_lines = []
        counter = 1
        for channel_id, title in channels:
            channel_lines.append(f"{counter}. {title}")
            counter += 1

        # Объединяем все строки
        text = "Введите номер канала который нужно удалить:\n" + "\n".join(channel_lines)
    await callback_query.message.reply(text)
    await callback_query.answer("")


@bot.on_message(filters.text)
async def delete_channel(client, message):
    global delete_channel_mode
    if delete_channel_mode:
        number = message.text
        if number.isdigit():
            try:
                number = int(number)
            except ValueError:
                await message.reply("Некорректное число", reply_markup=Keyboard)
                delete_channel_mode = False
                return
            channels = db.get_channels()
            if number >= len(channels) or number <= 0:
                await message.reply("Нет такого канала", reply_markup=Keyboard)
                delete_channel_mode = False
                return
            channel_id, title = channels[number - 1]
            db.delete_channel(channel_id)
            await message.reply(f"Канал {title} удален!")
            delete_channel_mode = False
        else:
            await message.reply("Некорректное число", reply_markup=Keyboard)
            delete_channel_mode = False





bot.run()