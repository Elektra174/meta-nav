import os
import asyncio
import logging
import threading
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# --- ВЕБ-СЕРВЕР ---
app = Flask(__name__)
@app.route('/')
def home(): return "Бот активен"

# --- НАСТРОЙКИ ---
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
CHANNEL_ID = '@lazalex_prosto_psychology'
CHANNEL_URL = "https://t.me/lazalex_prosto_psychology"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class MPTSteps(StatesGroup):
    test = State()
    sphere = State()
    problem = State()
    goal = State()
    control = State()
    reality = State()
    motivation = State()

QUESTIONS = [
    "Я часто думаю о том, что скажут или подумают другие.",
    "Я чувствую вину, когда делаю что-то для себя.",
    "Мне трудно сказать «нет», даже если я устал(а).",
    "Я чувствую ответственность за настроение близких.",
    "Мои планы зависят от потребностей других.",
    "Мне трудно понять свои желания без одобрения."
]

# --- ЛОГИКА ---
async def check_sub(user_id):
    try:
        m = await bot.get_chat_member(CHANNEL_ID, user_id)
        return m.status in ['member', 'administrator', 'creator']
    except: return False

@dp.message(Command("start"))
async def start(msg: types.Message, state: FSMContext):
    await state.clear()
    if await check_sub(msg.from_user.id):
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🚀 Начать тест", callback_data="t_0")]])
        await msg.answer("Привет! Я Александр Лазаренко. Навигатор поможет подготовить ваш запрос.", reply_markup=kb)
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Подписаться", url=CHANNEL_URL)],
            [InlineKeyboardButton(text="✅ Проверить", callback_data="recheck")]
        ])
        await msg.answer("Для запуска подпишись на канал:", reply_markup=kb)

@dp.callback_query(F.data == "recheck")
async def recheck(call: CallbackQuery, state: FSMContext):
    if await check_sub(call.from_user.id):
        await call.message.delete()
        await start(call.message, state)
    else: await call.answer("Подписка не найдена", show_alert=True)

@dp.callback_query(F.data.startswith("t_"))
async def run_test(call: CallbackQuery, state: FSMContext):
    step = int(call.data.split("_")[1])
    score = (await state.get_data()).get("score", 0)
    if step > 0:
        score += int(call.data.split("_")[-1])
        await state.update_data(score=score)

    if step < len(QUESTIONS):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Никогда (0)", callback_data=f"t_{step+1}_0")],
            [InlineKeyboardButton(text="Иногда (2)", callback_data=f"t_{step+1}_2")],
            [InlineKeyboardButton(text="Всегда (4)", callback_data=f"t_{step+1}_4")]
        ])
        await call.message.edit_text(f"Вопрос {step+1}: {QUESTIONS[step]}", reply_markup=kb)
    else:
        res = "Автор" if score <= 6 else "Заложник" if score <= 18 else "Жертва"
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📞 Записаться на МПТ-аудит", callback_data="audit")]])
        await call.message.answer(f"📊 Результат: {res}\nПриглашаю на безоплатную встречу!", reply_markup=kb)

@dp.callback_query(F.data == "audit")
async def begin_audit(call: CallbackQuery, state: FSMContext):
    await call.message.answer("В МПТ мы работаем через тело и образы. Выбери сферу:")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Деньги", callback_data="s_Деньги"), InlineKeyboardButton(text="Отношения", callback_data="s_Отношения")],
        [InlineKeyboardButton(text="Самооценка", callback_data="s_Самооценка"), InlineKeyboardButton(text="Состояние", callback_data="s_Состояние")]
    ])
    await call.message.answer("Сфера:", reply_markup=kb)
    await state.set_state(MPTSteps.sphere)

@dp.callback_query(MPTSteps.sphere)
async def sphere_set(call: CallbackQuery, state: FSMContext):
    await state.update_data(sphere=call.data.split("_")[1])
    await call.message.answer("1. Что сейчас создает напряжение?")
    await state.set_state(MPTSteps.problem)

@dp.message(MPTSteps.problem)
async def prob(m: types.Message, state: FSMContext):
    await state.update_data(p=m.text); await m.answer("2. Какой результат хочешь (без 'НЕ')?"); await state.set_state(MPTSteps.goal)

@dp.message(MPTSteps.goal)
async def goal(m: types.Message, state: FSMContext):
    await state.update_data(g=m.text); await m.answer("3. На сколько % это зависит от тебя?"); await state.set_state(MPTSteps.control)

@dp.message(MPTSteps.control)
async def ctrl(m: types.Message, state: FSMContext):
    await state.update_data(c=m.text); await m.answer("4. Что начнешь делать иначе при успехе?"); await state.set_state(MPTSteps.reality)

@dp.message(MPTSteps.reality)
async def real(m: types.Message, state: FSMContext):
    await state.update_data(r=m.text); await m.answer("5. Почему важно решить это сейчас?"); await state.set_state(MPTSteps.motivation)

@dp.message(MPTSteps.motivation)
async def final(m: types.Message, state: FSMContext):
    d = await state.get_data()
    rep = (f"🔥 ЗАЯВКА\nКлиент: {m.from_user.full_name}\nСфера: {d['sphere']}\n"
           f"📍 Проблема: {d['p']}\n📍 Цель: {d['g']}\n📍 Действие: {d['r']}\n📍 Смысл: {m.text}")
    if ADMIN_ID: await bot.send_message(ADMIN_ID, rep)
    await m.answer("✅ Запрос принят! Практика: закрой глаза на 30 сек и ощути тело. До связи!"); await state.clear()

async def main():
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000))), daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
