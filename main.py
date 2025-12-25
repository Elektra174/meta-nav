import logging
import os
import threading
from flask import Flask
from aiogram import Bot, Dispatcher, types, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- 1. ВЕБ-СЕРВЕР ДЛЯ RENDER ---
# Flask нужен, чтобы Render видел активный порт и не выключал бота
app = Flask(__name__)

@app.route('/')
def home():
    return "Бот Александр Лазаренко: Статус Live"

# --- 2. НАСТРОЙКИ БОТА ---
API_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CHANNEL_ID = '@lazalex_prosto_psychology'
CHANNEL_URL = "https://t.me/lazalex_prosto_psychology"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# --- 3. ЛОГИКА МПТ-АУДИТА (СОСТОЯНИЯ) ---
class MPTRequest(StatesGroup):
    sphere = State()
    problem = State()
    goal = State()
    control = State()
    reality = State()
    motivation = State()

QUESTIONS = [
    "Я часто думаю о том, что скажут или подумают другие, когда принимаю решение.",
    "Я чувствую вину, когда делаю что-то для себя, а не для других.",
    "Мне трудно сказать «нет», даже если я очень устал(а).",
    "Я чувствую ответственность за настроение близких и подстраиваюсь под них.",
    "Мои планы на день чаще зависят от потребностей других, чем от моих.",
    "Мне трудно понять, чего я хочу на самом деле, без одобрения со стороны."
]

# --- 4. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
async def is_subscribed(user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception:
        return False

async def send_welcome(message: types.Message):
    text = (
        "Привет! Я Александр Лазаренко. В рамках проекта «Метаформула жизни» я помогаю возвращать управление реальностью.\n\n"
        "Навигатор за 2 минуты подсветит твои слепые зоны и поможет подготовить фундамент для изменений."
    )
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("🚀 Начать тест", callback_data="test_0"))
    await bot.send_message(message.chat.id, text, reply_markup=kb)

# --- 5. ОБРАБОТЧИКИ (HANDLERS) ---
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    if await is_subscribed(message.from_user.id):
        await send_welcome(message)
    else:
        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("📢 Подписаться", url=CHANNEL_URL),
            InlineKeyboardButton("✅ Я подписался", callback_data="check")
        )
        await message.answer("Для запуска, пожалуйста, подпишись на канал проекта:", reply_markup=kb)

@dp.callback_query_handler(text="check")
async def check_sub(call: types.CallbackQuery):
    if await is_subscribed(call.from_user.id):
        await call.message.delete()
        await send_welcome(call.message)
    else:
        await call.answer("Подписка не найдена", show_alert=True)

@dp.callback_query_handler(lambda c: c.data.startswith('test_'))
async def run_test(call: types.CallbackQuery, state: FSMContext):
    step = int(call.data.split('_')[1])
    data = await state.get_data()
    score = data.get('score', 0)
    
    if step > 0:
        score += int(call.data.split('_')[2])
        await state.update_data(score=score)

    if step < len(QUESTIONS):
        kb = InlineKeyboardMarkup(row_width=1)
        for val, label in [(0, "Никогда"), (2, "Иногда"), (4, "Почти всегда")]:
            kb.add(InlineKeyboardButton(label, callback_data=f"test_{step+1}_{val}"))
        await call.message.edit_text(f"Вопрос {step+1}: {QUESTIONS[step]}", reply_markup=kb)
    else:
        await show_results(call.message, score)

async def show_results(message, score):
    res = "Автор" if score <= 6 else "Начинающий Автор" if score <= 12 else "Заложник" if score <= 18 else "Жертва"
    text = (
        f"📊 **Результат: {res}**\n\n"
        "Приглашаю тебя на **безоплатную встречу**, чтобы найти точку выхода из ситуации.\n\n"
        "На встрече ты получишь разбор запроса по методу МПТ и индивидуальный план действий."
    )
    kb = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("📞 Записаться и подготовить запрос", callback_data="start_audit")
    )
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

@dp.callback_query_handler(text="start_audit")
async def start_audit(call: types.CallbackQuery):
    intro = (
        "🔥 **Важно:** В МПТ мы работаем через **образы, ощущения в теле и движения**. "
        "Это позволяет обойти ловушки ума и найти решение в разы быстрее."
    )
    await call.message.answer(intro, parse_mode="Markdown")
    kb = InlineKeyboardMarkup(row_width=2)
    for s in ["Деньги", "Отношения", "Самооценка", "Состояние"]:
        kb.insert(InlineKeyboardButton(s, callback_data=f"sphere_{s}"))
    await call.message.answer("Выбери сферу для проработки:", reply_markup=kb)
    await MPTRequest.sphere.set()

@dp.callback_query_handler(state=MPTRequest.sphere)
async def sphere_chosen(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(sphere=call.data.split('_')[1])
    await call.message.answer("1. Опиши ситуацию, которая создает сейчас наибольшее напряжение:")
    await MPTRequest.problem.set()

@dp.message_handler(state=MPTRequest.problem)
async def step_1(msg: types.Message, state: FSMContext):
    await state.update_data(p=msg.text)
    await msg.answer("2. Какое состояние ты хочешь получить вместо этого? (Опиши без частицы 'НЕ')")
    await MPTRequest.goal.set()

@dp.message_handler(state=MPTRequest.goal)
async def step_2(msg: types.Message, state: FSMContext):
    await state.update_data(g=msg.text)
    await msg.answer("3. Насколько это состояние зависит лично от тебя? (0-100%)")
    await MPTRequest.control.set()

@dp.message_handler(state=MPTRequest.control)
async def step_3(msg: types.Message, state: FSMContext):
    await state.update_data(c=msg.text)
    await msg.answer("4. Что ты начнешь делать иначе, когда результат будет достигнут?")
    await MPTRequest.reality.set()

@dp.message_handler(state=MPTRequest.reality)
async def step_4(msg: types.Message, state: FSMContext):
    await state.update_data(r=msg.text)
    await msg.answer("5. Почему тебе важно решить этот запрос именно сейчас?")
    await MPTRequest.motivation.set()

@dp.message_handler(state=MPTRequest.motivation)
async def final_step(msg: types.Message, state: FSMContext):
    d = await state.get_data()
    user = msg.from_user
    report = (
        f"🔥 **НОВАЯ ЗАЯВКА**\n"
        f"Клиент: {user.full_name} (@{user.username})\n"
        f"Сфера: {d['sphere']}\n\n"
        f"📍 Проблема: {d['p']}\n"
        f"📍 Цель: {d['g']}\n"
        f"📍 Контроль: {d['c']}\n"
        f"📍 Действие: {d['r']}\n"
        f"📍 Смысл: {msg.text}"
    )
    if ADMIN_ID:
        try:
            await bot.send_message(ADMIN_ID, report)
        except Exception as e:
            logging.error(f"Ошибка отправки админу: {e}")

    practice = (
        "✅ **Запрос принят! Напишу тебе в ближайшее время.**\n\n"
        "Твоё первое задание (практика **«Разворот внимания»**):\n"
        "Закрой глаза на 30 сек. Перенеси внимание с мыслей на тело: где сейчас сжатие или тяжесть? "
        "Просто признай: «Да, это есть». Не борись, просто наблюдай. До связи!"
    )
    await msg.answer(practice)
    await state.finish()

# --- 6. ЗАПУСК ---
def run_bot():
    executor.start_polling(dp, skip_updates=True)

if __name__ == '__main__':
    # При обычном запуске (python main.py)
    run_bot()
else:
    # При запуске через Gunicorn (gunicorn main:app)
    thread = threading.Thread(target=run_bot)
    thread.daemon = True
    thread.start()
