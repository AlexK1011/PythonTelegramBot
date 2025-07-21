import asyncio
import json
import os

from redis.asyncio import Redis
from pyrogram.errors import FloodWait

from bots import bot, monitor_bot

import pyrogram
import sqlite3
import db
from keybpards import Keyboard, add_or_not
from monitor_channels import monitor_channels

from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from dotenv import load_dotenv
import logging
logging.basicConfig(level=logging.INFO)



db.init_db()

r = Redis(host='localhost', port=6379, db=0)
add_channel_mode = False
delete_channel_mode = False



channels_list = {
    "id": '',
    "title": ''
}


@bot.on_message(filters.command("start"))
async def start(client, message):
    await message.reply("Hello, I'm a bot!", reply_markup=Keyboard)


@bot.on_message(filters.forwarded)
async def add_channel(client, message):
    user_id = message.from_user.id
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
        if message.forward_from_chat and not db.channel_exists(user_id, message.forward_from_chat.id):
            db.add_channel(user_id, message.forward_from_chat.id, message.forward_from_chat.title or "Без названия")
            print(message.forward_from_chat.username)
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
    user_id = callback_query.from_user.id
    channels = db.get_channels(user_id)
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
    user_id = callback_query.from_user.id
    global channels_list
    channel_id = channels_list["id"]
    title = channels_list["title"]
    if channel_id and title:  # Проверяем, что данные есть
        db.add_channel(user_id, channel_id, title)
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
    user_id = callback_query.from_user.id
    channels = db.get_channels(user_id)
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
        global delete_channel_mode
        delete_channel_mode = True

    await callback_query.message.reply(text)
    await callback_query.answer("")


@bot.on_message(filters.text)
async def delete_channel(client, message):
    user_id = message.from_user.id
    global delete_channel_mode

    if delete_channel_mode:
        number = message.text.strip()
        if number.isdigit():
            try:
                number = int(number)
                channels = db.get_channels(user_id)

                if 1 <= number <= len(channels):
                    channel_id, title = channels[number - 1]
                    db.delete_channel(user_id, channel_id)
                    await message.reply(f"✅ Канал '{title}' удалён!", reply_markup=Keyboard)
                else:
                    await message.reply("❌ Нет канала с таким номером. Пожалуйста, введите правильный номер.",
                                        reply_markup=Keyboard)

            except Exception as e:
                await message.reply(f"❌ Произошла ошибка при удалении канала: ", reply_markup=Keyboard)

            delete_channel_mode = False  # Сбрасываем режим удаления в любом случае

        else:
            await message.reply("❌ Пожалуйста, введите номер канала цифрами.", reply_markup=Keyboard)
            delete_channel_mode = False




async def process_pubsub_messages():
    pubsub = r.pubsub()
    await pubsub.subscribe("new_posts")
    logging.info("👂 Подписан на канал 'new_posts'")

    # get_message — неблокирующий вариант
    while True:
        msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
        if msg and msg["type"] == "message":
            data = json.loads(msg["data"])
            text = data["message_text"]
            for uid in data["user_ids"]:
                try:
                    await bot.send_message(uid, text[:4096])
                except FloodWait as e:
                    await asyncio.sleep(e.value)
        await asyncio.sleep(0.1)  # уступаем управление другим таскам

# 5) стартуем всё
if __name__ == "__main__":
    # 5.1) запускаем бот (инициализируется loop, регистрируются декораторы)
    bot.start()
    # 5.2) создаём фоновую задачу внутри того же loop
    asyncio.get_event_loop().create_task(process_pubsub_messages())
    # 5.3) уходим в idle — теперь обрабатываются и /start, и колбеки
    idle()
    # 5.4) по Ctrl+C завершаем клиент
    bot.stop()
