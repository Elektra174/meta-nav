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

# --- ВЕБ-СЕРВЕР ---
app = Flask(__name__)
@app.route('/')
def home(): return "Бот работает"

# --- НАСТРОЙКИ ---
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
CHANNEL_ID = '@lazalex_prosto_psychology'
CHANNEL_URL = "https://t.me/lazalex_prosto_psychology"
IMAGE_URL = "https://raw.githubusercontent.com/Elektra174/meta-nav/main/logo.png"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class MPTSteps(StatesGroup):
    sphere = State(); problem = State(); goal = State(); control = State(); reality = State(); motivation = State()

QUESTIONS = [
    "Часто ловлю себя на мысли: «А что обо мне подумают?»",
    "Чувствую фоновую вину, когда выбираю отдых вместо дел.",
    "Мне сложно сказать «нет», даже если ресурс на нуле.",
    "Я автоматически подстраиваюсь под настроение других.",
    "Мои планы легко рушатся из-за чужих просьб.",
    "Мне нужно подтверждение со стороны, что я всё делаю правильно."
]

async def check_sub(user_id):
    try:
        m = await bot.get_chat_member(CHANNEL_ID, user_id)
        return m.status in ['member', 'administrator', 'creator']
    except: return False

@dp.message(Command("start"))
async def start(msg: types.Message, state: FSMContext):
    await state.clear()
    is_sub = await check_sub(msg.from_user.id)
    welcome_text = (
        f"👋 **Здравствуйте, {msg.from_user.first_name}!**\n\n"
        "Я Александр Лазаренко. В рамках проекта «Метаформула жизни» я помогаю вернуть себе роль **Автора своей реальности**.\n\n"
        "📍 *Готовы проложить свой авторский маршрут?*"
    )
    kb_sub = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="📢 Подписаться", url=CHANNEL_URL)],
        [types.InlineKeyboardButton(text="✅ Проверить подписку", callback_data="recheck")]
    ])
    kb_start = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="🚀 Запустить навигатор", callback_data="t_0")]])
    
    try:
        await bot.send_photo(msg.chat.id, photo=IMAGE_URL, caption=welcome_text, reply_markup=kb_start if is_sub else kb_sub, parse_mode="Markdown")
    except:
        await msg.answer(welcome_text, reply_markup=kb_start if is_sub else kb_sub, parse_mode="Markdown")

@dp.callback_query(F.data == "recheck")
async def recheck(call: types.CallbackQuery, state: FSMContext):
    if await check_sub(call.from_user.id):
        await call.message.delete()
        await start(call.message, state)
    else:
        await call.answer("Подписка не найдена", show_alert=True)

@dp.callback_query(F.data.startswith("t_"))
async def run_test(call: types.CallbackQuery, state: FSMContext):
    step = int(call.data.split("_")[1])
    data = await state.get_data()
    score = data.get("score", 0)
    if step > 0:
        score += int(call.data.split("_")[-1])
        await state.update_data(score=score)

    if step < len(QUESTIONS):
        kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="Никогда (0)", callback_data=f"t_{step+1}_0")],
            [types.InlineKeyboardButton(text="Иногда (2)", callback_data=f"t_{step+1}_2")],
            [types.InlineKeyboardButton(text="Часто (4)", callback_data=f"t_{step+1}_4")]
        ])
        await call.message.answer(f"📝 **Вопрос {step+1} из {len(QUESTIONS)}**\n\n{QUESTIONS[step]}", reply_markup=kb, parse_mode="Markdown")
    else:
        res = "Автор" if score <= 6 else "Начинающий Автор" if score <= 12 else "Заложник" if score <= 18 else "Жертва"
        kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="📞 Записаться на аудит", callback_data="audit")]])
        await call.message.answer(f"📊 **Ваш результат: {res}**\n\nЗапишитесь на стратегическую встречу (30 мин).", reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data == "audit")
async def begin_audit(call: types.CallbackQuery, state: FSMContext):
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="💰 Деньги", callback_data="s_Деньги"), types.InlineKeyboardButton(text="❤️ Отношения", callback_data="s_Отношения")],
        [types.InlineKeyboardButton(text="💎 Самооценка", callback_data="s_Самооценка"), types.InlineKeyboardButton(text="🔋 Состояние", callback_data="s_Состояние")]
    ])
    await call.message.answer("Выбери сферу:", reply_markup=kb)
    await state.set_state(MPTSteps.sphere)

@dp.callback_query(MPTSteps.sphere)
async def sphere_set(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(sphere=call.data.split("_")[1])
    await call.message.answer("1. Что создает напряжение?")
    await state.set_state(MPTSteps.problem)

@dp.message(MPTSteps.problem)
async def prob(m: types.Message, state: FSMContext):
    await state.update_data(p=m.text); await m.answer("2. Какой результат хотите?"); await state.set_state(MPTSteps.goal)

@dp.message(MPTSteps.goal)
async def goal(m: types.Message, state: FSMContext):
    await state.update_data(g=m.text); await m.answer("3. На сколько % это зависит от вас?"); await state.set_state(MPTSteps.control)

@dp.message(MPTSteps.control)
async def ctrl(m: types.Message, state: FSMContext):
    await state.update_data(c=m.text); await m.answer("4. Что начнете делать иначе?"); await state.set_state(MPTSteps.reality)

@dp.message(MPTSteps.reality)
async def real(m: types.Message, state: FSMContext):
    await state.update_data(r=m.text); await m.answer("5. Почему важно решить это сейчас?"); await state.set_state(MPTSteps.motivation)

@dp.message(MPTSteps.motivation)
async def final(m: types.Message, state: FSMContext):
    d = await state.get_data()
    rep = (f"🔥 ЗАЯВКА\nКлиент: {m.from_user.full_name} (@{m.from_user.username})\nСфера: {d['sphere']}\n"
           f"📍 Проблема: {d['p']}\n📍 Цель: {d['g']}\n📍 Смысл: {m.text}")
    if ADMIN_ID: await bot.send_message(ADMIN_ID, rep)
    await m.answer("✅ Принято! Свяжусь с вами в ближайшее время."); await state.clear()

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))

async def main():
    threading.Thread(target=run_flask, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
