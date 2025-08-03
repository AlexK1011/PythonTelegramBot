from aiogram import Router, F
from aiogram.filters import CommandStart
import re
import db
from keyboards import Keyboard, add_or_not, settings
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext



channels_list = {}

def set_channels_list(user_id, value):
    channels_list[user_id] = value

def get_channels_list(user_id):
    return channels_list.get(user_id, {"id": '', "title": ''})


class UserState(StatesGroup):
    add_channel = State()
    delete_channel = State()
    set_delay = State()
    min_forward_rate = State()
    set_reposts_rate = State()


router = Router()

@router.message(CommandStart())
async def start(message, state: FSMContext):
    await state.clear()
    await message.reply("Hello, I'm a bot!", reply_markup=Keyboard)

@router.message(lambda m: m.forward_from_chat and m.forward_from_chat.type == 'channel')
async def add_channel(message, state: FSMContext):
    user_id = message.from_user.id
    username = message.forward_from_chat.username
    title = message.forward_from_chat.title or "Без названия"
    channel_id = message.forward_from_chat.id
    current_state = await state.get_state()

    if current_state == UserState.add_channel.state:
        if not db.channel_exists(user_id, channel_id):
            db.add_channel(user_id, channel_id, title, username)
            await message.reply(f"Канал {title} добавлен!", reply_markup=Keyboard)
        else:
            await message.reply(f"Канал {title} уже добавлен!", reply_markup=Keyboard)
        await state.clear()
    else:
        set_channels_list(user_id, {
            "id": channel_id,
            "title": title,
            "username": username
        })
        await message.reply("Вы пытаетесь добавить этот канал?", reply_markup=add_or_not)

@router.callback_query(F.data == "add_channel")
async def adding_channel(callback_query, state: FSMContext):
    await state.set_state(UserState.add_channel)
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
async def nothing(callback_query, state: FSMContext):
    user_id = callback_query.from_user.id
    set_channels_list(user_id, {"id": '', "title": ''})
    await state.clear()
    await callback_query.answer("отменено")

@router.callback_query(F.data == "confirm_add_channel")
async def confirm_add_channel(callback_query):
    user_id = callback_query.from_user.id
    channel_info = get_channels_list(user_id)
    channel_id = channel_info["id"]
    title = channel_info["title"]
    username = channel_info.get("username")
    if channel_id and title:
        db.add_channel(user_id, channel_id, title, username)
        await callback_query.answer("Канал добавлен!")
        await callback_query.message.edit_text(f"Канал {title} добавлен!", reply_markup=Keyboard)
    else:
        await callback_query.answer("Нет данных для добавления канала")
    set_channels_list(user_id, {"id": '', "title": '', "username": ''})

@router.callback_query(F.data == "delete_channel")
async def start_deleting_channel(callback_query, state: FSMContext):
    user_id = callback_query.from_user.id
    channels = db.get_channels(user_id)
    if not channels:
        text = "Список каналов пуст"
    else:
        channel_lines = [f"{i+1}. {title}" for i, (_, title) in enumerate(channels)]
        text = "Введите номер канала который нужно удалить:\n" + "\n".join(channel_lines)
        await state.set_state(UserState.delete_channel)
    await callback_query.message.reply(text)
    await callback_query.answer()

@router.message(UserState.delete_channel, F.text.isdigit())
async def delete_channel(message, state: FSMContext):
    user_id = message.from_user.id
    number = int(message.text.strip())
    channels = db.get_channels(user_id)
    if 1 <= number <= len(channels):
        channel_id, title = channels[number - 1]
        db.delete_channel(user_id, channel_id)
        await message.reply(f"✅ Канал '{title}' удалён!", reply_markup=Keyboard)
    else:
        await message.reply("❌ Нет канала с таким номером. Пожалуйста, введите правильный номер.", reply_markup=Keyboard)
    await state.clear()


@router.message(UserState.delete_channel, ~F.text.isdigit())
async def reset_delete_mode(message, state: FSMContext):
    user_id = message.from_user.id
    await message.reply("❌ Пожалуйста, введите номер канала цифрами.", reply_markup=Keyboard)
    await state.clear()



@router.callback_query(F.data == "settings")
async def show_settings(callback_query):
    await callback_query.message.edit_text("Настройки", reply_markup=settings)
    await callback_query.answer()


@router.callback_query(F.data == "delay")
async def set_delay(callback_query, state: FSMContext):
    await state.set_state(UserState.set_delay)
    await callback_query.message.edit_text("Введите время в часах, которое нужно ждать для сбора статистики по каждому посту")
    await callback_query.answer()


@router.message(UserState.set_delay)
async def save_delay(message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text.strip()
    pattern = r'(\d+)(?:[.,]?(\d+))?'
    numbers = re.findall(pattern, text)

    def safe_int(val):
        try:
            return int(val)
        except (ValueError, TypeError):
            return 0

    if len(numbers) == 1:
        int_part = safe_int(numbers[0][0])
        frac_part_str = numbers[0][1]
        frac_part = float('0.' + frac_part_str) if frac_part_str else 0

        minutes = round(frac_part * 60)
        total_seconds = int_part * 3600 + minutes * 60
        total_seconds = round(total_seconds)

        if total_seconds == 0:
            await message.reply(f"❌ задержка не может быть нулевой", reply_markup=Keyboard)
            await state.clear()
            return
        elif total_seconds > 86400:
            await message.reply(f"❌ задержка не может быть больше 24 часов", reply_markup=Keyboard)
            await state.clear()
            return

        db.set_settings(user_id, "delay", total_seconds)

        if int_part == 0 and minutes > 0:
            await message.reply(f"✅ Время задержки изменено на {minutes} минут!", reply_markup=Keyboard)
        elif int_part > 0 and minutes == 0:
            await message.reply(f"✅ Время задержки изменено на {int_part} часов!", reply_markup=Keyboard)
        else:
            await message.reply(f"✅ Время задержки изменено на {int_part} часов, {minutes} минут!",
                                reply_markup=Keyboard)

        await state.clear()


    elif len(numbers) == 2:
        # Разделенный ввод: часы и минуты
        if numbers[0][1] and numbers[0][1] != "":
            await message.reply(f"❌ при указании отдельно часов и минут, количество часов не может быть дробным",
                                reply_markup=Keyboard)
            await state.clear()
            return

        hours = safe_int(numbers[0][0])
        minutes_int_part = safe_int(numbers[1][0])
        minutes_frac_part_str = numbers[1][1]
        minutes_frac_part = float('0.' + minutes_frac_part_str) if minutes_frac_part_str else 0

        minutes = round(minutes_int_part + minutes_frac_part)

        total_seconds = hours * 3600 + minutes * 60
        total_seconds = round(total_seconds)

        if total_seconds == 0:
            await message.reply(f"❌ задержка не может быть нулевой", reply_markup=Keyboard)
            await state.clear()
            return
        elif total_seconds > 86400:
            await message.reply(f"❌ задержка не может быть больше 24 часов", reply_markup=Keyboard)
            await state.clear()
            return

        db.set_settings(user_id, "delay", total_seconds)

        if hours == 0:
            await message.reply(f"✅ Время задержки изменено на {minutes} минут!", reply_markup=Keyboard)
        elif minutes == 0:
            await message.reply(f"✅ Время задержки изменено на {hours} часов!", reply_markup=Keyboard)
        else:
            await message.reply(f"✅ Время задержки изменено на {hours} часов, {minutes} минут!", reply_markup=Keyboard)

        await state.clear()

    else:
        await message.reply("❌ не удалось распознать время", reply_markup=Keyboard)
        await state.clear()


@router.callback_query(F.data == "reposts")
async def set_reposts_rate(callback_query, state: FSMContext):
    await state.set_state(UserState.set_reposts_rate)
    await callback_query.message.edit_text("Введите процент репостов")
    await callback_query.answer()


@router.message(UserState.set_reposts_rate)
async def save_reposts_rate(message, state: FSMContext):
    def safe_float(val):
        try:
            return float(val)
        except (ValueError, TypeError):
            return 0
    user_id = message.from_user.id
    text = message.text.strip()
    pattern = r'(\d+(?:[.,]\d*)?)%?'
    number = re.findall(pattern, text)[0]
    number = safe_float(number)
    if number <= 0 or number > 100:
        await message.reply(f"❌ Пожалуйста, введите число от 1 до 100", reply_markup=Keyboard)
        await state.clear()
        return

    try:
        show_number = int(number)
    except ValueError:
        show_number = number

    db.set_settings(user_id, "min_forward_rate", number)
    await message.reply(f"✅ Процент репостов изменен на {show_number}%", reply_markup=Keyboard)
    await state.clear()
