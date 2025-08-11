import re

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

import keyboards as kb

import db
from config import max_channels

channel_router = Router()


class ChannelState(StatesGroup):
    add_channel = State()
    delete_channel = State()


@channel_router.message(lambda m: m.forward_from_chat and m.forward_from_chat.type == 'channel')
async def add_channel(message, state: FSMContext):
    user_id = message.from_user.id
    username = message.forward_from_chat.username
    title = message.forward_from_chat.title or "Без названия"
    channel_id = message.forward_from_chat.id
    user_channels = db.get_channels(user_id)

    if len(user_channels) >= max_channels:
        await message.reply(f"❌ Превышено максимальное количество каналов (50)", reply_markup=kb.Keyboard)
        await state.clear()
        return

    if username is not None:
        if not db.channel_exists(user_id, username):
            db.add_channel(user_id, title, username)
            await message.reply(f"Канал {title} добавлен!", reply_markup=kb.Keyboard)
        else:
            await message.reply(f"Канал {title} уже добавлен!", reply_markup=kb.Keyboard)
    else:
        await message.reply(f"❌ мониторить можно только публичные каналы", reply_markup=kb.Keyboard)
    await state.clear()


@channel_router.callback_query(F.data == "list_channels")
async def show_channels(callback_query):
    user_id = callback_query.from_user.id
    channels = db.get_channels(user_id)
    if not channels:
        text = "Список каналов пуст"
    else:
        channel_lines = [f"{i + 1}. {title}" for i, (_, title) in enumerate(channels)]
        text = "Сохраненные каналы:\n" + "\n".join(channel_lines)
    await callback_query.answer()
    await callback_query.message.edit_text(text, reply_markup=kb.Keyboard)


@channel_router.callback_query(F.data == "delete_channel")
async def start_deleting_channel(callback_query, state: FSMContext):
    user_id = callback_query.from_user.id
    channels = db.get_channels(user_id)
    if not channels:
        text = "Список каналов пуст"
    else:
        channel_lines = [f"{i + 1}. {title}" for i, (_, title) in enumerate(channels)]
        text = "Введите номер канала который нужно удалить:\n" + "\n".join(channel_lines)
        await state.set_state(ChannelState.delete_channel)
    await callback_query.message.edit_text(text, reply_markup=kb.cancel)
    await callback_query.answer()


@channel_router.message(ChannelState.delete_channel)
async def delete_channel(message, state: FSMContext):
    user_id = message.from_user.id
    pattern = r'\d+'
    numbers = re.findall(pattern, message.text)
    channels = db.get_channels(user_id)
    deleted = 0
    valid = []
    invalid = []
    for number in numbers:
        number = int(number)
        if 1 <= number <= len(channels):
            channel_id, title = channels[number - 1]
            db.delete_channel(user_id, channel_id)
            deleted += 1
            valid.append(title)

        else:
            invalid.append(number)
    if deleted > 0:
        invalid_message = (
            f"\nОднако, не удалось удалить каналы с номерами: {', '.join(map(str, invalid))}"
            if invalid
            else ""
        )

        if deleted == 1:
            await message.reply(
                f"✅ канал {valid[0]} удалён!{invalid_message}",
                reply_markup=kb.Keyboard)
        elif deleted == 2:
            await message.reply(
                f"✅ каналы {valid[0]} и {valid[1]} удалены!{invalid_message}",
                reply_markup=kb.Keyboard)
        else:
            await message.reply(
                f"✅ {deleted} каналов удалены!{invalid_message}",
                reply_markup=kb.Keyboard)
    else:
        await message.reply(f"❌ Не удалось удалить эти каналы. Проверьте номера и повторите попытку.",
                            reply_markup=kb.Keyboard)
    await state.clear()
