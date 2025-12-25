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

app = Flask(__name__)
@app.route('/')
def home(): return "Бот МПТ активен"

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
        f"Привет! Меня зовут Александр Лазаренко, я психолог МПТ и автор проекта «Метаформула жизни».\n\n"
        "Я помогаю людям выйти из замкнутого круга чужих ожиданий и вернуть себе роль Автора своей реальности.\n\n"
        "Этот навигатор поможет подсветить ваши слепые зоны и сформировать четкий запрос для качественных изменений.\n\n"
        "Готовы проложить свой авторский маршрут?"
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
        await call.answer("Нужна подписка на канал для продолжения", show_alert=True)

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
        await call.message.answer(f"Вопрос {step+1} из {len(QUESTIONS)}\n\n{QUESTIONS[step]}", reply_markup=kb)
    else:
        if score <= 6:
            res_status = "Автор"
            desc = "Это отличный показатель! Даже у Авторов бывают моменты, когда нужно откалибровать маршрут или выйти на новый уровень масштаба. Если у вас есть актуальный вызов — давайте разберем его."
        elif score <= 12:
            res_status = "Начинающий Автор"
            desc = "Вы уже на пути к управлению своей жизнью, но еще остались сферы, где управление ускользает. Предлагаю найти эти точки утечки."
        else:
            res_status = "Заложник обстоятельств"
            desc = "Сейчас кажется, что внешние факторы сильнее вас. Это энергозатратное состояние. Давайте найдем способ вернуть вам управление вашей жизнью."
        
        result_text = (
            f"Ваш результат: {res_status}\n\n{desc}\n\n"
            "Приглашаю вас на безоплатную вводную консультацию (30 мин), чтобы разобрать ваш запрос через метод МПТ."
        )
        kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="Сформировать запрос", callback_data="audit")]])
        await call.message.answer(result_text, reply_markup=kb)

@dp.callback_query(F.data == "audit")
async def begin_audit(call: types.CallbackQuery, state: FSMContext):
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Деньги / Карьера", callback_data="s_Деньги"), types.InlineKeyboardButton(text="Отношения", callback_data="s_Отношения")],
        [types.InlineKeyboardButton(text="Самооценка", callback_data="s_Самооценка"), types.InlineKeyboardButton(text="Состояние", callback_data="s_Состояние")]
    ])
    await call.message.answer("Выберите сферу, которая сейчас наиболее важна:", reply_markup=kb)
    await state.set_state(MPTSteps.sphere)

@dp.message(MPTSteps.sphere) # Обработка если ввели текст вместо кнопки
async def sphere_text(m: types.Message, state: FSMContext):
    await state.update_data(sphere=m.text)
    await m.answer("Опишите ситуацию, которая сейчас создает напряжение (факты и ваши чувства):")
    await state.set_state(MPTSteps.problem)

@dp.callback_query(MPTSteps.sphere)
async def sphere_set(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(sphere=call.data.split("_")[1])
    await call.message.answer("Опишите ситуацию, которая сейчас создает напряжение (факты и ваши чувства):")
    await state.set_state(MPTSteps.problem)

@dp.message(MPTSteps.problem)
async def prob(m: types.Message, state: FSMContext):
    await state.update_data(p=m.text)
    await m.answer("Какой результат вы хотите получить? Опишите его без частицы «НЕ», как конкретное состояние или событие.")
    await state.set_state(MPTSteps.goal)

@dp.message(MPTSteps.goal)
async def goal(m: types.Message, state: FSMContext):
    if "не " in m.text.lower():
        return await m.answer("В методе МПТ мы фокусируемся на желаемом результате. Попробуйте сформулировать цель без частицы «НЕ». Что именно должно появиться?")
    await state.update_data(g=m.text)
    await m.answer("На сколько % этот результат зависит лично от вас?")
    await state.set_state(MPTSteps.control)

@dp.message(MPTSteps.control)
async def ctrl(m: types.Message, state: FSMContext):
    try:
        val = int(''.join(filter(str.isdigit, m.text)))
        if val < 70:
            return await m.answer(f"Если результат зависит от вас только на {val}%, то кто управляет остальной частью? Попробуйте найти ту грань цели, где ваша ответственность будет максимальной.")
        await state.update_data(c=val)
    except:
        return await m.answer("Пожалуйста, укажите число (например, 100).")
    await m.answer("Как изменятся ваши действия или состояние, когда вы вернете себе роль Автора в этой ситуации?")
    await state.set_state(MPTSteps.reality)

@dp.message(MPTSteps.reality)
async def real(m: types.Message, state: FSMContext):
    await state.update_data(r=m.text)
    await m.answer("Почему для вас важно решить этот запрос именно сейчас?")
    await state.set_state(MPTSteps.motivation)

@dp.message(MPTSteps.motivation)
async def final(m: types.Message, state: FSMContext):
    d = await state.get_data()
    rep = (f"🔥 НОВАЯ ЗАЯВКА\n\n"
           f"Клиент: {m.from_user.full_name} (@{m.from_user.username})\n"
           f"Сфера: {d['sphere']}\n"
           f"Ситуация: {d['p']}\n"
           f"Цель: {d['g']}\n"
           f"Ответственность: {d['c']}%\n"
           f"Изменения: {d['r']}\n"
           f"Почему сейчас: {m.text}")
    if ADMIN_ID: await bot.send_message(ADMIN_ID, rep)
    await m.answer("Запрос принят. Я изучу ваши ответы и напишу вам в личные сообщения, чтобы договориться о времени встречи.")
    await state.clear()

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))

async def main():
    threading.Thread(target=run_flask, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
