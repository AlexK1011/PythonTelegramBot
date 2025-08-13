import re

from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

import keyboards as kb

import db
from config import get_settings_text, change_mode_text

settings_router = Router()


class SettingsState(StatesGroup):
    set_delay = State()
    set_reposts_rate = State()
    enable_ai = State()
    set_system_prompt = State()
    change_mode = State()


@settings_router.callback_query(F.data == "settings")
async def show_settings(callback_query):
    user_id = callback_query.from_user.id
    settings = db.get_settings(user_id)
    mode = settings.get("mode", 'delayed_check')

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
    reposts_text = f"{reposts_percent}%" if reposts_percent == int(reposts_percent) \
        else f"{round(reposts_percent, 2)}%"
    ai_enabled = settings.get("ai_enabled", 0)
    settings_text = get_settings_text(mode, delay_text, reposts_text, ai_enabled)
    if mode == "delayed_check":
        await callback_query.message.edit_text(settings_text, reply_markup=kb.settings_delayed_check, parse_mode="html")
        await callback_query.answer()
    else:
        await callback_query.message.edit_text(settings_text, reply_markup=kb.settings_periodic_collection, parse_mode="html")
        await callback_query.answer()


@settings_router.callback_query(F.data == "delay")
async def set_delay(callback_query, state: FSMContext):
    await state.set_state(SettingsState.set_delay)
    await callback_query.message.edit_text(
        "Введите время в часах, которое нужно ждать для сбора статистики по каждому посту")
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

        db.set_settings(user_id,"delay", total_seconds)

        if hours == 0:
            await message.reply(f"✅ Время задержки изменено на {minutes} минут!", reply_markup=kb.Keyboard)
        elif minutes == 0:
            await message.reply(f"✅ Время задержки изменено на {hours} часов!", reply_markup=kb.Keyboard)
        else:
            await message.reply(f"✅ Время задержки изменено на {hours} часов, {minutes} минут!",
                                reply_markup=kb.Keyboard)

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


@settings_router.callback_query(F.data == "enable_ai")
async def enable_ai(callback_query, state: FSMContext):
    await state.set_state(SettingsState.enable_ai)
    await callback_query.message.edit_text("Вы хотите использовать обработку постов через ИИ?")
    await callback_query.answer()


@settings_router.message(SettingsState.enable_ai)
async def ask_system_prompt(message, state: FSMContext):
    text = message.text.strip()

    if text.lower() == "да":
        answer = True
    elif text.lower() == "нет":
        answer = False
    else:
        await message.reply("❌ Пожалуйста, введите да или нет")
        return

    current_settings = db.get_settings(message.from_user.id)
    if answer == bool(current_settings["ai_enabled"]):
        await message.reply("ИИ уже включен" if answer else "ИИ уже выключен")
        return

    if answer:
        await state.set_state(SettingsState.set_system_prompt)
        await message.reply("Теперь введите промпт, который будет использоваться для обработки постов через ИИ")
    else:
        db.set_settings(message.from_user.id, "ai_enabled", False)
        db.set_settings(message.from_user.id, "system_prompt", "")
        await message.reply("✅ ИИ выключен!", reply_markup=kb.Keyboard)
        await state.clear()


@settings_router.message(SettingsState.set_system_prompt)
async def save_system_prompt(message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text.strip()
    if text == "":
        await message.reply("❌ Пожалуйста, введите промпт")
        return
    elif len(text) <= 5:
        await message.reply("❌ промпт должен быть длиннее 5 символов")
        return

    db.set_settings(user_id, "ai_enabled", True)
    db.set_settings(user_id, "system_prompt", text)
    await message.reply("✅ Промпт сохранен!", reply_markup=kb.Keyboard)
    await state.clear()


@settings_router.callback_query(F.data == "change_mode")
async def change_mode(callback_query, state: FSMContext):
    await state.set_state(SettingsState.change_mode)
    await callback_query.message.edit_text(change_mode_text, reply_markup=kb.change_mode, parse_mode="HTML")
    await callback_query.answer()


@settings_router.callback_query(StateFilter(SettingsState.change_mode))
async def set_mode(callback_query, state: FSMContext):
    await state.clear()
    current_mode = db.get_settings(callback_query.from_user.id).get("mode", "delayed_check")
    mode = callback_query.data
    if mode == current_mode:
        await callback_query.message.edit_text("❌ Этот режим уже выбран", reply_markup=kb.Keyboard)
        return
    db.set_settings(callback_query.from_user.id, "mode", mode)
    await callback_query.message.edit_text("✅ Режим изменен!", reply_markup=kb.Keyboard)


@settings_router.callback_query(F.data == "interval")
async def set_interval(callback_query, state: FSMContext):
    await state.set_state(SettingsState.set_interval)
    await callback_query.message.edit_text("Введите интервал в минутах", reply_markup=kb.cancel)
    await callback_query.answer()


