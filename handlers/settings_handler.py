import re

from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

import keyboards as kb

import db
from config import get_settings_text, change_mode_text
from format_time import format_time

settings_router = Router()


class SettingsState(StatesGroup):
    set_delay = State()
    set_reposts_rate = State()
    enable_ai = State()
    set_system_prompt = State()
    change_mode = State()
    set_interval = State()
    set_number_of_posts = State()


@settings_router.callback_query(F.data == "settings")
async def show_settings(callback_query):
    user_id = callback_query.from_user.id
    settings = db.get_settings(user_id)
    mode = settings.get("mode", 'delayed_check')

    settings_text = get_settings_text(settings)
    if mode == "delayed_check":
        await callback_query.message.edit_text(settings_text, reply_markup=kb.settings_delayed_check,
                                               parse_mode="html")
        await callback_query.answer()
    else:
        await callback_query.message.edit_text(settings_text, reply_markup=kb.settings_periodic_collection,
                                               parse_mode="html")
        await callback_query.answer()


@settings_router.callback_query(F.data == "delay")
async def set_delay(callback_query, state: FSMContext):
    await state.set_state(SettingsState.set_delay)
    await callback_query.message.edit_text(
        "Установите время ожидания\n\nФормат: часы (1.5) или часы:минуты (1:30)")
    await callback_query.answer()


def parse_time(text: str) -> dict:
    match = re.fullmatch(r'^(\d+)(?:[.,](\d+))?$|^(\d+):(\d+)$', text.strip())

    if not match:
        return {
            "error": True,
            "reply_text": "❌ Неверный формат времени\n\nИспользуйте:\n• Часы с дробью: 1.5 или 2,75"
                          "\n• Часы и минуты: 1:30 или 2:45"
        }

    groups = match.groups()
    total_seconds = 0

    if groups[0] is not None:
        hours = int(groups[0])
        if groups[1]:
            fraction = float(f"0.{groups[1]}")
            minutes = round(fraction * 60)
            total_seconds = hours * 3600 + minutes * 60
        else:
            total_seconds = hours * 3600

    elif groups[2] is not None:
        hours = int(groups[2])
        minutes = int(groups[3])
        total_seconds = hours * 3600 + minutes * 60

    return {
        "error": False,
        "total_seconds": total_seconds
    }


@settings_router.message(SettingsState.set_delay)
async def save_delay(message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text.strip()

    parsed = parse_time(text)

    if parsed["error"]:
        await message.reply(parsed["reply_text"], reply_markup=kb.Keyboard)
        await state.clear()
        return

    total_seconds = parsed["total_seconds"]

    if total_seconds <= 0:
        await message.reply("❌ Задержка не может быть нулевой", reply_markup=kb.Keyboard)
        await state.clear()
        return

    if total_seconds > 86400:
        await message.reply("❌ Максимальная задержка: 24 часа\n\nУкажите меньшее значение.",
                            reply_markup=kb.Keyboard)
        await state.clear()
        return

    db.set_settings(user_id, "delay", total_seconds)

    time_str = format_time(total_seconds)
    response = f"✅ Время задержки изменено на <b>{time_str}</b>"

    await message.reply(response, parse_mode="HTML", reply_markup=kb.Keyboard)
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
        await message.reply(f"❌ Введите число от 1 до 100", reply_markup=kb.Keyboard)
        await state.clear()
        return

    try:
        show_number = int(number)
    except ValueError:
        show_number = number

    db.set_settings(user_id, "min_forward_rate", number)
    await message.reply(f"✅ Процент репостов изменен на <b>{show_number}%</b>",
                        parse_mode="HTML", reply_markup=kb.Keyboard)
    await state.clear()


@settings_router.callback_query(F.data == "enable_ai")
async def enable_ai(callback_query, state: FSMContext):
    await state.set_state(SettingsState.enable_ai)
    await callback_query.message.edit_text("Вы хотите использовать обработку постов через ИИ?\n\nОтветьте: да/нет")
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
        db.set_settings(message.from_user.id, "ai_enabled", 0)
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
        await message.reply("❌ Промпт должен содержать минимум 5 символов")
        return

    db.set_settings(user_id, "ai_enabled", 1)
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
        await callback_query.message.edit_text("ℹ️ Этот режим уже активен", reply_markup=kb.Keyboard)
        return
    db.set_settings(callback_query.from_user.id, "mode", mode)
    await callback_query.message.edit_text("✅ Режим изменен!", reply_markup=kb.Keyboard)


@settings_router.callback_query(F.data == "interval")
async def set_interval(callback_query, state: FSMContext):
    await state.set_state(SettingsState.set_interval)
    await callback_query.message.edit_text("Установите интервал проверки"
                                           "\n\nФормат: часы (1.5) или часы:минуты (1:30)", reply_markup=kb.cancel)
    await callback_query.answer()


@settings_router.message(SettingsState.set_interval)
async def save_interval(message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text.strip()
    parsed = parse_time(text)

    if parsed["error"]:
        await message.reply(parsed["reply_text"], reply_markup=kb.Keyboard)
        await state.clear()
        return

    total_seconds = parsed["total_seconds"]

    if total_seconds <= 0:
        await message.reply("❌ Интервал не может быть нулевым", reply_markup=kb.Keyboard)
        await state.clear()
        return

    if total_seconds > 86400:
        await message.reply("❌ Интервал не может быть больше 24 часов", reply_markup=kb.Keyboard)
        await state.clear()
        return

    db.set_settings(user_id, "interval", total_seconds)

    time_str = format_time(total_seconds)
    await message.reply(f"✅ Интервал изменен на {time_str}!", reply_markup=kb.Keyboard)
    await state.clear()


@settings_router.callback_query(F.data == "number_of_posts")
async def set_number_of_posts(callback_query, state: FSMContext):
    await state.set_state(SettingsState.set_number_of_posts)
    await callback_query.message.edit_text("Установите размер топа", reply_markup=kb.cancel)
    await callback_query.answer()


@settings_router.message(SettingsState.set_number_of_posts)
async def save_number_of_posts(message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text.strip()
    if not text.isdigit():
        await message.reply("❌ Количество постов должно быть числом", reply_markup=kb.Keyboard)
        await state.clear()
        return
    db.set_settings(user_id, "number_of_posts", int(text))
    await message.reply(f"✅ изменено на <b>{text}</b>!", parse_mode="HTML", reply_markup=kb.Keyboard)
    await state.clear()
