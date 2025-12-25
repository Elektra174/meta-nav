import os
import asyncio
import logging
import threading
import re
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

app = Flask(__name__)
@app.route('/')
def home(): return "МПТ-Навигатор активен"

# --- НАСТРОЙКИ ---
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
CHANNEL_ID = '@lazalex_prosto_psychology'
CHANNEL_URL = "https://t.me/lazalex_prosto_psychology"
IMAGE_URL = "https://raw.githubusercontent.com/Elektra174/meta-nav/main/logo.png"
PDF_GUIDE_URL = "https://raw.githubusercontent.com/Elektra174/meta-nav/main/Svoboda_test.pdf"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class MPTSteps(StatesGroup):
    sphere = State(); problem = State(); goal = State(); control = State(); reality = State(); motivation = State()

# --- ФИЛЬТР СМЫСЛА (защита от пустых ответов) ---
def is_meaningful(text):
    if not text: return False
    if not re.search(r'[а-яА-Я]', text): return False
    words = re.findall(r'[а-яА-ЯёЁ]{2,}', text.lower())
    if len(words) < 2 or len(text.strip()) < 8: return False
    return True

async def check_sub(user_id):
    try:
        m = await bot.get_chat_member(CHANNEL_ID, user_id)
        return m.status in ['member', 'administrator', 'creator']
    except: return False

async def give_gift(chat_id):
    welcome_back = (
        "Ваша подписка активна! 🌿\n\n"
        "Привет! Я Александр Лазаренко. Рад, что вы решили заглянуть в тему Автортства и внутренней свободы.\n\n"
        "🎁 Как и обещал, отправляю вам тест **«Свобода быть собой»** в формате PDF. Это хорошая база для начала.\n\n"
        "А прямо здесь я предлагаю вам пройти быстрый интерактивный квиз, чтобы увидеть вашу «точку старта» прямо сейчас."
    )
    kb_start = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="🚀 Сверить часы (квиз)", callback_data="t_0")]])
    try:
        await bot.send_photo(chat_id, photo=IMAGE_URL, caption=welcome_back, parse_mode="Markdown")
        await bot.send_document(chat_id, document=PDF_GUIDE_URL, caption="Ваш подарок 🎁")
        await bot.send_message(chat_id, "Начнем квиз?", reply_markup=kb_start)
    except:
        await bot.send_message(chat_id, "Начнем квиз?", reply_markup=kb_start)

@dp.message(Command("start", "reset"))
async def start(msg: types.Message, state: FSMContext):
    await state.clear()
    if await check_sub(msg.from_user.id):
        await give_gift(msg.chat.id)
    else:
        text = (
            "Привет! Я Александр Лазаренко, психолог МПТ и автор проекта **«Prosto психология | Метаформула жизни»**.\n\n"
            "Здесь мы исследуем, как перестать бороться с обстоятельствами и вернуть себе право быть Автором своей жизни.\n\n"
            "🎁 Чтобы забрать подарок (тест «Свобода быть собой») и запустить Навигатор, подпишитесь на мой канал."
        )
        kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="📢 Подписаться", url=CHANNEL_URL)],
            [types.InlineKeyboardButton(text="✅ Я подписался", callback_data="recheck")]
        ])
        await bot.send_photo(msg.chat.id, photo=IMAGE_URL, caption=text, reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data == "recheck")
async def recheck(call: types.CallbackQuery, state: FSMContext):
    if await check_sub(call.from_user.id):
        await call.message.delete()
        await give_gift(call.message.chat.id)
    else:
        await call.answer("Жду вашей подписки на канал... 🔄", show_alert=True)

@dp.callback_query(F.data.startswith("t_"))
async def run_test(call: types.CallbackQuery, state: FSMContext):
    q = [
        "Часто думаю: «А что обо мне подумают?»",
        "Чувствую вину, когда выбираю себя.",
        "Сложно сказать «нет», даже если ресурс на нуле.",
        "Подстраиваюсь под чужое настроение.",
        "Мои планы легко рушатся из-за чужих просьб.",
        "Нужно одобрение со стороны, что я всё делаю правильно."
    ]
    step = int(call.data.split("_")[1])
    data = await state.get_data()
    score = data.get("score", 0)
    if step > 0: score += int(call.data.split("_")[-1])
    await state.update_data(score=score)

    if step < len(q):
        kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="Нет (0)", callback_data=f"t_{step+1}_0")],
            [types.InlineKeyboardButton(text="Иногда (2)", callback_data=f"t_{step+1}_2")],
            [types.InlineKeyboardButton(text="Да (4)", callback_data=f"t_{step+1}_4")]
        ])
        await call.message.answer(f"Вопрос {step+1} из 6:\n\n{q[step]}", reply_markup=kb)
    else:
        res = "Автор" if score <= 6 else "Начинающий Автор" if score <= 12 else "Заложник обстоятельств"
        txt = (
            f"Ваш текущий результат: **{res}**.\n\n"
            "Это лишь снимок момента. Хотите пойти глубже и исследовать, как это проявляется в конкретной сфере вашей жизни?"
        )
        kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="🔍 Исследовать ситуацию", callback_data="audit")]])
        await call.message.answer(txt, reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data == "audit")
async def begin_audit(call: types.CallbackQuery, state: FSMContext):
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Деньги", callback_data="s_Деньги"), types.InlineKeyboardButton(text="Отношения", callback_data="s_Отношения")],
        [types.InlineKeyboardButton(text="Самооценка", callback_data="s_Самооценка"), types.InlineKeyboardButton(text="Состояние", callback_data="s_Состояние")]
    ])
    await call.message.answer("Выберите сферу, которая сейчас больше всего требует внимания:", reply_markup=kb)
    await state.set_state(MPTSteps.sphere)

@dp.callback_query(MPTSteps.sphere)
async def sphere_set(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(sphere=call.data.split("_")[1])
    await call.message.answer("Опишите коротко ситуацию, в которой вы чувствуете потерю легкости или авторства:")
    await state.set_state(MPTSteps.problem)

@dp.message(MPTSteps.problem)
async def prob(m: types.Message, state: FSMContext):
    if not is_meaningful(m.text): return await m.answer("Поделитесь чуть подробнее, что именно происходит?")
    await state.update_data(p=m.text)
    await m.answer("К какому внутреннему состоянию вы бы хотели прийти? (опишите его без частицы «НЕ»)")
    await state.set_state(MPTSteps.goal)

@dp.message(MPTSteps.goal)
async def goal(m: types.Message, state: FSMContext):
    if not is_meaningful(m.text): return await m.answer("Как бы вы назвали это желаемое состояние?")
    await state.update_data(g=m.text)
    kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="🔄 Сменить сферу исследования", callback_data="audit")]])
    await m.answer("На сколько % ваше самоощущение в этой ситуации зависит от вашего внутреннего внимания и выбора?", reply_markup=kb)
    await state.set_state(MPTSteps.control)

@dp.message(MPTSteps.control)
async def ctrl(m: types.Message, state: FSMContext):
    if any(x in m.text.lower() for x in ["назад", "сфер", "занов", "сначала"]):
        kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="🔄 К выбору сферы", callback_data="audit")]])
        return await m.answer("Вы можете изменить тему исследования:", reply_markup=kb)
    try:
        val = int(''.join(filter(str.isdigit, m.text)))
        if val < 70:
            kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="🔄 Сменить тему", callback_data="audit")]])
            return await m.answer(f"Похоже, сейчас фокус внимания смещен на внешние факторы ({val}%). В МПТ мы ищем ту грань, где выбор остается за вами. Попробуйте найти её или смените тему.", reply_markup=kb)
        await state.update_data(c=val)
        await m.answer("Что нового обнаружится в вашем состоянии и действиях, когда вы вернёте себе роль Автора?")
        await state.set_state(MPTSteps.reality)
    except: await m.answer("Пожалуйста, напишите число (например, 100).")

@dp.message(MPTSteps.reality)
async def real(m: types.Message, state: FSMContext):
    if not is_meaningful(m.text): return await m.answer("Поделитесь ощущениями подробнее.")
    await state.update_data(r=m.text)
    await m.answer("Почему для вас важно обнаружить эту внутреннюю свободу именно сейчас?")
    await state.set_state(MPTSteps.motivation)

@dp.message(MPTSteps.motivation)
async def final(m: types.Message, state: FSMContext):
    if not is_meaningful(m.text): return await m.answer("Поделитесь вашим истинным смыслом — почему это важно?")
    d = await state.get_data()
    rep = (f"🔍 РЕЗУЛЬТАТ ИССЛЕДОВАНИЯ\n"
           f"Клиент: {m.from_user.full_name} (@{m.from_user.username})\n"
           f"Сфера: {d['sphere']}\n"
           f"Ситуация: {d['p']}\n"
           f"Желаемое состояние: {d['g']}\n"
           f"Субъектность: {d['c']}%\n"
           f"Новое восприятие: {d['r']}\n"
           f"Смысл: {m.text}")
    
    if ADMIN_ID: await bot.send_message(ADMIN_ID, rep)
    
    await m.answer(
        "Благодарю за доверие и ваше исследование. Я внимательно изучу ваши ответы и напишу вам в личные сообщения, "
        "чтобы договориться о **бесплатной вводной встрече (30 мин)**, где мы вместе проложим маршрут к вашей Свободе.",
        parse_mode="Markdown"
    )
    await state.clear()

async def main():
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000))), daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
