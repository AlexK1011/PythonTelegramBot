from aiogram import Router, F
import db
from keyboards import Keyboard, add_or_not

# Глобальные переменные для состояний
add_channel_mode = {}
delete_channel_mode = {}
channels_list = {}

def get_user_state(user_id):
    return add_channel_mode.get(user_id, False), delete_channel_mode.get(user_id, False)

def set_add_channel_mode(user_id, value):
    add_channel_mode[user_id] = value

def set_delete_channel_mode(user_id, value):
    delete_channel_mode[user_id] = value

def set_channels_list(user_id, value):
    channels_list[user_id] = value

def get_channels_list(user_id):
    return channels_list.get(user_id, {"id": '', "title": ''})

router = Router()

@router.message(F.text == "/start")
async def start(message):
    user_id = message.from_user.id
    set_add_channel_mode(user_id, False)
    set_delete_channel_mode(user_id, False)
    await message.reply("Hello, I'm a bot!", reply_markup=Keyboard)

@router.message(lambda m: m.forward_from_chat and m.forward_from_chat.type == 'channel')
async def add_channel(message):
    user_id = message.from_user.id
    add_mode, _ = get_user_state(user_id)
    if add_mode:
        if not db.channel_exists(user_id, message.forward_from_chat.id):
            db.add_channel(user_id, message.forward_from_chat.id, message.forward_from_chat.title or "Без названия")
            await message.reply(f"Канал {message.forward_from_chat.title} добавлен!", reply_markup=Keyboard)
        else:
            await message.reply(f"Канал {message.forward_from_chat.title} уже добавлен!", reply_markup=Keyboard)
        set_add_channel_mode(user_id, False)
    else:
        set_channels_list(user_id, {
            "id": message.forward_from_chat.id,
            "title": message.forward_from_chat.title or "Без названия"
        })
        await message.reply("Вы пытаетесь добавить этот канал?", reply_markup=add_or_not)

@router.callback_query(F.data == "add_channel")
async def adding_channel(callback_query):
    user_id = callback_query.from_user.id
    set_add_channel_mode(user_id, True)
    await callback_query.answer("Перешлите сообщение из канала, который нужно добавить")

@router.callback_query(F.data == "list_channels")
async def show_channels(callback_query):
    user_id = callback_query.from_user.id
    channels = db.get_channels(user_id)
    if not channels:
        text = "Список каналов пуст"
    else:
        channel_lines = [f"{i+1}. {title}" for i, (_, title) in enumerate(channels)]
        text = "Сохраненные каналы:\n" + "\n".join(channel_lines)
    await callback_query.answer()
    await callback_query.message.edit_text(text, reply_markup=Keyboard)

@router.callback_query(F.data == "dont_add")
async def nothing(callback_query):
    user_id = callback_query.from_user.id
    set_channels_list(user_id, {"id": '', "title": ''})
    await callback_query.answer("отменено")

@router.callback_query(F.data == "confirm_add_channel")
async def confirm_add_channel(callback_query):
    user_id = callback_query.from_user.id
    channel_info = get_channels_list(user_id)
    channel_id = channel_info["id"]
    title = channel_info["title"]
    if channel_id and title:
        db.add_channel(user_id, channel_id, title)
        await callback_query.answer("Канал добавлен!")
        await callback_query.message.edit_text(f"Канал {title} добавлен!", reply_markup=Keyboard)
    else:
        await callback_query.answer("Нет данных для добавления канала")
    set_channels_list(user_id, {"id": '', "title": ''})

@router.callback_query(F.data == "delete_channel")
async def start_deleting_channel(callback_query):
    user_id = callback_query.from_user.id
    channels = db.get_channels(user_id)
    if not channels:
        text = "Список каналов пуст"
    else:
        channel_lines = [f"{i+1}. {title}" for i, (_, title) in enumerate(channels)]
        text = "Введите номер канала который нужно удалить:\n" + "\n".join(channel_lines)
        set_delete_channel_mode(user_id, True)
    await callback_query.message.reply(text)
    await callback_query.answer()

@router.message(lambda m: m.text and m.text.isdigit())
async def delete_channel(message):
    user_id = message.from_user.id
    _, del_mode = get_user_state(user_id)
    if del_mode:
        number = int(message.text.strip())
        channels = db.get_channels(user_id)
        if 1 <= number <= len(channels):
            channel_id, title = channels[number - 1]
            db.delete_channel(user_id, channel_id)
            await message.reply(f"✅ Канал '{title}' удалён!", reply_markup=Keyboard)
        else:
            await message.reply("❌ Нет канала с таким номером. Пожалуйста, введите правильный номер.", reply_markup=Keyboard)
        set_delete_channel_mode(user_id, False)

@router.message(lambda m: m.text and not m.text.isdigit())
async def reset_delete_mode(message):
    user_id = message.from_user.id
    _, del_mode = get_user_state(user_id)
    if del_mode:
        await message.reply("❌ Пожалуйста, введите номер канала цифрами.", reply_markup=Keyboard)
        set_delete_channel_mode(user_id, False)