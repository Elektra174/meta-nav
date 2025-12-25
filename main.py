import os
import asyncio
import logging
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# --- ВЕБ-СЕРВЕР ---
app = Flask(__name__)
@app.route('/')
def home(): return "Бот Александр Лазаренко: Работает"

# --- НАСТРОЙКИ ---
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
CHANNEL_ID = '@lazalex_prosto_psychology'
CHANNEL_URL = "https://t.me/lazalex_prosto_psychology"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class MPTSteps(StatesGroup):
    sphere = State(); problem = State(); goal = State(); control = State(); reality = State(); motivation = State()

QUESTIONS = [
    "Я часто думаю о том, что скажут или подумают другие.",
    "Я чувствую вину, когда делаю что-то для себя.",
    "Мне трудно сказать «нет», даже если я устал(а).",
    "Я чувствую ответственность за настроение близких.",
    "Мои планы зависят от потребностей других.",
    "Мне трудно понять свои желания без одобрения."
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
    if is_sub:
        kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="🚀 Начать тест", callback_data="t_0")]])
        await msg.answer(f"Привет, {msg.from_user.first_name}! Я Александр Лазаренко. Навигатор поможет подготовить ваш запрос.", reply_markup=kb)
    else:
        kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="📢 Подписаться", url=CHANNEL_URL)],
            [types.InlineKeyboardButton(text="✅ Проверить подписку", callback_data="recheck")]
        ])
        await msg.answer("Для запуска, пожалуйста, подпишись на канал проекта:", reply_markup=kb)

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
        await call.message.edit_text(f"Вопрос {step+1}: {QUESTIONS[step]}", reply_markup=kb)
    else:
        res = "Автор" if score <= 6 else "Заложник" if score <= 18 else "Жертва"
        kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="📞 Записаться на МПТ-аудит", callback_data="audit")]])
        await call.message.answer(f"📊 Результат: {res}\n\nЭтот показатель говорит о том, насколько вы управляете своей жизнью. Приглашаю на безоплатную встречу!", reply_markup=kb)

@dp.callback_query(F.data == "audit")
async def begin_audit(call: types.CallbackQuery, state: FSMContext):
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Деньги", callback_data="s_Деньги"), types.InlineKeyboardButton(text="Отношения", callback_data="s_Отношения")],
        [types.InlineKeyboardButton(text="Самооценка", callback_data="s_Самооценка"), types.InlineKeyboardButton(text="Состояние", callback_data="s_Состояние")]
    ])
    await call.message.answer("Выбери сферу, в которой хочешь вернуть управление:", reply_markup=kb)
    await state.set_state(MPTSteps.sphere)

@dp.callback_query(MPTSteps.sphere)
async def sphere_set(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(sphere=call.data.split("_")[1])
    await call.message.answer("1. Опиши ситуацию, которая создает напряжение:")
    await state.set_state(MPTSteps.problem)

@dp.message(MPTSteps.problem)
async def prob(m: types.Message, state: FSMContext):
    await state.update_data(p=m.text); await m.answer("2. Какой результат хочешь получить (без частицы 'НЕ')?"); await state.set_state(MPTSteps.goal)

@dp.message(MPTSteps.goal)
async def goal(m: types.Message, state: FSMContext):
    await state.update_data(g=m.text); await m.answer("3. На сколько % это зависит лично от тебя?"); await state.set_state(MPTSteps.control)

@dp.message(MPTSteps.control)
async def ctrl(m: types.Message, state: FSMContext):
    await state.update_data(c=m.text); await m.answer("4. Что ты начнешь делать иначе, когда цель будет достигнута?"); await state.set_state(MPTSteps.reality)

@dp.message(MPTSteps.reality)
async def real(m: types.Message, state: FSMContext):
    await state.update_data(r=m.text); await m.answer("5. Почему важно решить это именно сейчас?"); await state.set_state(MPTSteps.motivation)

@dp.message(MPTSteps.motivation)
async def final(m: types.Message, state: FSMContext):
    d = await state.get_data()
    rep = (f"🔥 ЗАЯВКА\nКлиент: {m.from_user.full_name} (@{m.from_user.username})\nСфера: {d['sphere']}\n"
           f"📍 Проблема: {d['p']}\n📍 Цель: {d['g']}\n📍 Действие: {d['r']}\n📍 Смысл: {m.text}")
    if ADMIN_ID: await bot.send_message(ADMIN_ID, rep)
    await m.answer("✅ Запрос принят! Я напишу тебе для записи.\n\nПрактика: закрой глаза на 30 сек и ощути тело. Признай напряжение: «Да, оно есть». До встречи!"); await state.clear()

# --- ЗАПУСК ---
def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))

async def main():
    # Запускаем Flask в отдельном потоке
    Thread(target=run_flask, daemon=True).start()
    # Запускаем бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.info("Starting bot...")
    asyncio.run(main())
