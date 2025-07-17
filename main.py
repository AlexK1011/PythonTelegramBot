import os
import pyrogram
import sqlite3

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from dotenv import load_dotenv


load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")




bot = Client(
    "my_bot",
    bot_token=BOT_TOKEN,
    api_id=API_ID,
    api_hash=API_HASH
)

add_channel_mode = False

Keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("добавить канал", callback_data="add_channel"), InlineKeyboardButton("список каналов", callback_data="list_channels")],
])
add_or_not = InlineKeyboardMarkup([
    [InlineKeyboardButton("да", callback_data="confirm_add_channel"), InlineKeyboardButton("нет", callback_data="nothing")],
])

temp_channels_list = []
channels_list = []


@bot.on_message(filters.command("start"))
async def start(client, message):
    await message.reply("Hello, I'm a bot!", reply_markup=Keyboard)


@bot.on_message(filters.forwarded)
async def add_channel(client, message):
    global add_channel_mode
    if add_channel_mode:
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
        else:
            await message.reply(
                f"Канал {message.forward_from_chat.title} уже добавлен!",
                reply_markup=Keyboard
            )
        add_channel_mode = False
    else:
        temp_channels_list.append({
            "id": message.forward_from_chat.id,
            "title": message.forward_from_chat.title or "Без названия"
        })
        await message.reply("предлагаю, вы пытаетесь добавить канал", reply_markup=add_or_not)


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


@bot.on_callback_query(callback_data_filter("nothing"))
async def nothing(client, callback_query: CallbackQuery):
    temp_channels_list.clear()
    await callback_query.answer("отменено")


@bot.on_callback_query(callback_data_filter("confirm_add_channel"))
async def confirm_add_channel(client, callback_query: CallbackQuery):
    global channels_list
    channels_list.append(temp_channels_list[len(temp_channels_list) - 1])
    await callback_query.message.edit_text(
        f"Канал {channels_list[len(channels_list) - 1]['title']} добавлен!",
        reply_markup=Keyboard)
bot.run()