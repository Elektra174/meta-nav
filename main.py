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
def home(): return "Бот МПТ работает"

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

# --- ОПИСАНИЕ БОТА (то, что видно до старта) ---
# Настройте это в BotFather -> Bot Settings -> Description

@dp.message(Command("start"))
async def start(msg: types.Message, state: FSMContext):
    await state.clear()
    is_sub = await check_sub(msg.from_user.id)
    
    welcome_text = (
        f"Привет! Меня зовут Александр Лазаренко, я психолог МПТ и автор проекта «Метаформула жизни».\n\n"
        "Я помогаю людям выйти из замкнутого круга чужих ожиданий и вернуть себе роль **Автора своей реальности**.\n\n"
        "Этот навигатор поможет подсветить ваши слепые зоны и сформировать четкий запрос для качественных изменений.\n\n"
        "📍 *Готовы проложить свой авторский маршрут?*"
    )
    
    kb_sub = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="📢 Подписаться на проект", url=CHANNEL_URL)],
        [types.InlineKeyboardButton(text="✅ Я подписался", callback_data="recheck")]
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
        await call.answer("Нужна подписка на канал для продолжения 🔄", show_alert=True)

# --- ТЕСТ ---
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
            [types.InlineKeyboardButton(text="Бывает иногда (2)", callback_data=f"t_{step+1}_2")],
            [types.InlineKeyboardButton(text="Да, это про меня (4)", callback_data=f"t_{step+1}_4")]
        ])
        await call.message.answer(f"📝 **Вопрос {step+1} из {len(QUESTIONS)}**\n\n{QUESTIONS[step]}", reply_markup=kb, parse_mode="Markdown")
    else:
        res = "Автор" if score <= 6 else "Начинающий Автор" if score <= 12 else "Заложник обстоятельств" if score <= 18 else "В позиции Жертвы"
        result_text = (
            f"📊 **Ваш результат: {res}**\n\n"
            "Это важная точка осознания. Чтобы двигаться дальше, приглашаю вас на **безоплатную вводную консультацию (30 мин)**.\n\n"
            "Там мы разберем ваш запрос через метод МПТ и найдем корень ситуации."
        )
        kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="📞 Сформировать запрос", callback_data="audit")]])
        await call.message.answer(result_text, reply_markup=kb, parse_mode="Markdown")

# --- МПТ ИССЛЕДОВАНИЕ ЗАПРОСА ---
@dp.callback_query(F.data == "audit")
async def begin_audit(call: types.CallbackQuery, state: FSMContext):
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="💰 Деньги / Карьера", callback_data="s_Деньги"), types.InlineKeyboardButton(text="❤️ Отношения", callback_data="s_Отношения")],
        [types.InlineKeyboardButton(text="💎 Самооценка", callback_data="s_Самооценка"), types.InlineKeyboardButton(text="🔋 Состояние", callback_data="s_Состояние")]
    ])
    await call.message.answer("Выберите сферу, которая сейчас требует внимания:", reply_markup=kb)
    await state.set_state(MPTSteps.sphere)

@dp.callback_query(MPTSteps.sphere)
async def sphere_set(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(sphere=call.data.split("_")[1])
    await call.message.answer("1️⃣ **Точка А.** Опишите ситуацию, которая создает напряжение (факты и ваши чувства):")
    await state.set_state(MPTSteps.problem)

@dp.message(MPTSteps.problem)
async def prob(m: types.Message, state: FSMContext):
    if len(m.text) < 5:
        return await m.answer("Пожалуйста, опишите ситуацию чуть подробнее, чтобы я мог лучше подготовиться.")
    await state.update_data(p=m.text)
    await m.answer("2️⃣ **Точка Б.** Какой результат вы хотите получить? \n\n⚠️ *Важно: опишите это без частицы «НЕ», как конкретное состояние или событие.*")
    await state.set_state(MPTSteps.goal)

@dp.message(MPTSteps.goal)
async def goal(m: types.Message, state: FSMContext):
    text = m.text.lower()
    if "не " in text or "не." in text:
        return await m.answer("В МПТ мы работаем с тем, что мы ХОТИМ, а не с тем, от чего бежим. Переформулируйте без «НЕ».")
    await state.update_data(g=m.text)
    await m.answer("3️⃣ **Авторство.** На сколько % этот результат зависит лично от вас? (введите число от 0 до 100)")
    await state.set_state(MPTSteps.control)

@dp.message(MPTSteps.control)
async def ctrl(m: types.Message, state: FSMContext):
    try:
        val = int(''.join(filter(str.isdigit, m.text)))
        if val < 70:
            return await m.answer(f"Пока вы считаете, что результат зависит от вас только на {val}%, вы отдаете управление другим. Попробуйте найти ресурс в себе — сколько ответственности вы готовы взять на себя ради этой цели?")
        await state.update_data(c=val)
    except:
        return await m.answer("Пожалуйста, введите числовое значение (например, 100).")
    
    await m.answer("4️⃣ **Действие.** Что вы начнете делать иначе, когда почувствуете, что вы — Автор в этой ситуации?")
    await state.set_state(MPTSteps.reality)

@dp.message(MPTSteps.reality)
async def real(m: types.Message, state: FSMContext):
    await state.update_data(r=m.text)
    await m.answer("5️⃣ **Смысл.** Почему для вас критически важно изменить это именно сейчас? (раскройте ответ)")
    await state.set_state(MPTSteps.motivation)

@dp.message(MPTSteps.motivation)
async def final(m: types.Message, state: FSMContext):
    if len(m.text) < 10:
        return await m.answer("Этот пункт очень важен для вашей мотивации. Напишите подробнее: почему это важно?")
    
    d = await state.get_data()
    rep = (f"🔥 **НОВАЯ ЗАЯВКА (МПТ-АУДИТ)**\n"
           f"Клиент: {m.from_user.full_name} (@{m.from_user.username})\n"
           f"Сфера: {d['sphere']}\n"
           f"───────────────────\n"
           f"📍 **Проблема:** {d['p']}\n"
           f"📍 **Цель (Без НЕ):** {d['g']}\n"
           f"📍 **Ответственность:** {d['c']}%\n"
           f"📍 **Действия:** {d['r']}\n"
           f"📍 **Смысл:** {m.text}")
    
    if ADMIN_ID: await bot.send_message(ADMIN_ID, rep)
    
    await m.answer("✅ **Ваш запрос принят!**\n\nЯ изучу ваши ответы и свяжусь с вами в личные сообщения, чтобы договориться о времени вводной консультации.\n\nДо связи!")
    await state.clear()

# --- ЗАПУСК ---
def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))

async def main():
    threading.Thread(target=run_flask, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
