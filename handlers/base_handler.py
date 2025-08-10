from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

import keyboards as kb

base_router = Router()


@base_router.message(CommandStart())
async def start(message, state: FSMContext):
    await state.clear()
    await message.reply("Hello, I'm a bot!", reply_markup=kb.Keyboard)


@base_router.callback_query(F.data == "back_to_main")
async def back_to_main(callback_query, state: FSMContext):
    await state.clear()
    await callback_query.message.edit_text("Главное меню", reply_markup=kb.Keyboard)
    await callback_query.answer()
