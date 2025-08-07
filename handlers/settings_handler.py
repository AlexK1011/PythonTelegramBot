import re

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

import keyboards as kb

import db

settings_router = Router()
class SettingsState(StatesGroup):
    set_delay = State()
    min_forward_rate = State()
    set_reposts_rate = State()

@settings_router.callback_query(F.data == "settings")
async def show_settings(callback_query):
    user_id = callback_query.from_user.id
    settings = db.get_settings(user_id)

    delay_seconds = settings.get("delay", 3600)
    delay_hours = delay_seconds // 3600
    delay_minutes = (delay_seconds % 3600) // 60

    if delay_hours > 0 and delay_minutes > 0:
        delay_text = f"{delay_hours} ч {delay_minutes} мин"
    elif delay_hours > 0:
        delay_text = f"{delay_hours} ч"
    else:
        delay_text = f"{delay_minutes} мин"

    reposts_percent = settings.get("min_forward_rate", 1.0)
    reposts_text = f"{reposts_percent}%" if reposts_percent == int(reposts_percent) else f"{reposts_percent}%"

    await callback_query.message.edit_text(f"""⚙️ Настройки

1. <b>Задержка</b> - время ожидания перед анализом статистики поста. Бот будет ждать указанное время, а затем проверять процент репостов. Это нужно для сбора полной статистики поста.

2. <b>Минимальный процент репостов</b> - пороговое значение репостов в процентах от просмотров. Пост будет отправлен вам только если процент репостов достигнет или превысит это значение.

Нажмите на нужную настройку для изменения.

📋 <b>Текущие настройки:</b>
• Задержка: <b>{delay_text}</b>
• Минимальный процент репостов: <b>{reposts_text}</b>""", reply_markup=kb.settings, parse_mode="html")
    await callback_query.answer()


@settings_router.callback_query(F.data == "delay")
async def set_delay(callback_query, state: FSMContext):
    await state.set_state(SettingsState.set_delay)
    await callback_query.message.edit_text("Введите время в часах, которое нужно ждать для сбора статистики по каждому посту")
    await callback_query.answer()


@settings_router.message(SettingsState.set_delay)
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
            await message.reply(f"❌ задержка не может быть нулевой", reply_markup=kb.Keyboard)
            await state.clear()
            return
        elif total_seconds > 86400:
            await message.reply(f"❌ задержка не может быть больше 24 часов", reply_markup=kb.Keyboard)
            await state.clear()
            return

        db.set_settings(user_id, "delay", total_seconds)

        if int_part == 0 and minutes > 0:
            await message.reply(f"✅ Время задержки изменено на {minutes} минут!", reply_markup=kb.Keyboard)
        elif int_part > 0 and minutes == 0:
            await message.reply(f"✅ Время задержки изменено на {int_part} часов!", reply_markup=kb.Keyboard)
        else:
            await message.reply(f"✅ Время задержки изменено на {int_part} часов, {minutes} минут!",
                                reply_markup=kb.Keyboard)

        await state.clear()


    elif len(numbers) == 2:
        # Разделенный ввод: часы и минуты
        if numbers[0][1] and numbers[0][1] != "":
            await message.reply(f"❌ при указании отдельно часов и минут, количество часов не может быть дробным",
                                reply_markup=kb.Keyboard)
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
            await message.reply(f"❌ задержка не может быть нулевой", reply_markup=kb.Keyboard)
            await state.clear()
            return
        elif total_seconds > 86400:
            await message.reply(f"❌ задержка не может быть больше 24 часов", reply_markup=kb.Keyboard)
            await state.clear()
            return

        db.set_settings(user_id, "delay", total_seconds)

        if hours == 0:
            await message.reply(f"✅ Время задержки изменено на {minutes} минут!", reply_markup=kb.Keyboard)
        elif minutes == 0:
            await message.reply(f"✅ Время задержки изменено на {hours} часов!", reply_markup=kb.Keyboard)
        else:
            await message.reply(f"✅ Время задержки изменено на {hours} часов, {minutes} минут!", reply_markup=kb.Keyboard)

        await state.clear()

    else:
        await message.reply("❌ не удалось распознать время", reply_markup=kb.Keyboard)
        await state.clear()


@settings_router.callback_query(F.data == "reposts")
async def set_reposts_rate(callback_query, state: FSMContext):
    await state.set_state(SettingsState.set_reposts_rate)
    await callback_query.message.edit_text("Введите процент репостов")
    await callback_query.answer()


@settings_router.message(SettingsState.set_reposts_rate)
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
        await message.reply(f"❌ Пожалуйста, введите число от 1 до 100", reply_markup=kb.Keyboard)
        await state.clear()
        return

    try:
        show_number = int(number)
    except ValueError:
        show_number = number

    db.set_settings(user_id, "min_forward_rate", number)
    await message.reply(f"✅ Процент репостов изменен на {show_number}%", reply_markup=kb.Keyboard)
    await state.clear()

