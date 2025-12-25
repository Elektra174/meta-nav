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

# АКТУАЛЬНЫЙ ФАЙЛ (прямая ссылка)
PDF_GUIDE_URL = "https://raw.githubusercontent.com/Elektra174/meta-nav/main/Svoboda_test.pdf"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class MPTSteps(StatesGroup):
    sphere = State(); problem = State(); goal = State(); control = State(); reality = State(); motivation = State()

# --- УЛУЧШЕННЫЙ ФИЛЬТР СМЫСЛА ---
def is_meaningful(text):
    if not text: return False
    # 1. Проверка на русский язык
    if not re.search(r'[а-яА-Я]', text): return False
    # 2. Исключаем чистые вопросы или знаки
    if text.strip() == "?" or (text.count('?') > 1 and len(text) < 10): return False
    # 3. Список отписок
    stop_words = {'привет', 'здравствуйте', 'тест', 'проверка', 'понятно', 'хорошо', 'нормально', 'окей', 'иди', 'нету', 'гладиолус', 'зачем', 'почему', 'хз', 'просто'}
    words = re.findall(r'[а-яА-ЯёЁ]{2,}', text.lower())
    meaningful_words = {w for w in words if w not in stop_words}
    # 4. Порог уникальности и длины
    if len(meaningful_words) < 2 or len(text.strip()) < 12:
        return False
    return True

async def check_sub(user_id):
    try:
        m = await bot.get_chat_member(CHANNEL_ID, user_id)
        return m.status in ['member', 'administrator', 'creator']
    except: return False

async def give_gift(chat_id):
    welcome_back = (
        "Ваша подписка активна.\n\n"
        "Привет! Меня зовут Александр Лазаренко, я психолог МПТ и автор проекта **«Prosto психология | Метаформула жизни»**.\n\n"
        "Я помогаю людям обрести роль Автора своей реальности и выйти из режима ожидания.\n\n"
        "🎁 Ваш подарок: полный тест «Свобода быть собой» в формате PDF (отправляю ниже).\n\n"
        "Также предлагаю пройти мини-квиз, чтобы определить ваш текущий уровень авторства."
    )
    kb_start = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="🚀 Запустить мини-квиз", callback_data="t_0")]])
    try:
        await bot.send_photo(chat_id, photo=IMAGE_URL, caption=welcome_back, parse_mode="Markdown")
        await bot.send_document(chat_id, document=PDF_GUIDE_URL, caption="Ваш подарок — Полный тест «Свобода быть собой» 🎁")
        await bot.send_message(chat_id, "Нажмите кнопку ниже, чтобы начать:", reply_markup=kb_start)
    except:
        await bot.send_message(chat_id, "Начинаем?", reply_markup=kb_start)

@dp.message(Command("start", "reset"))
async def start(msg: types.Message, state: FSMContext):
    await state.clear()
    is_sub = await check_sub(msg.from_user.id)
    if is_sub:
        await give_gift(msg.chat.id)
    else:
        welcome_text = (
            "Привет! Меня зовут Александр Лазаренко, я психолог МПТ и автор проекта **«Prosto психология | Метаформула жизни»**.\n\n"
            "Я помогаю людям обрести роль Автора своей реальности и выйти из режима ожидания.\n\n"
            "🎁 Ваш подарок готов: полный тест «Свобода быть собой» в формате PDF.\n\n"
            "Чтобы забрать подарок и начать путь, подпишитесь на мой канал."
        )
        kb_sub = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="📢 Подписаться и получить подарок", url=CHANNEL_URL)],
            [types.InlineKeyboardButton(text="✅ Я подписался", callback_data="recheck")]
        ])
        try:
            await bot.send_photo(msg.chat.id, photo=IMAGE_URL, caption=welcome_text, reply_markup=kb_sub, parse_mode="Markdown")
        except:
            await msg.answer(welcome_text, reply_markup=kb_sub, parse_mode="Markdown")

@dp.callback_query(F.data == "recheck")
async def recheck(call: types.CallbackQuery, state: FSMContext):
    if await check_sub(call.from_user.id):
        await call.message.delete()
        await give_gift(call.message.chat.id)
    else:
        await call.answer("Нужна подписка на канал для получения подарка 🔄", show_alert=True)

@dp.callback_query(F.data.startswith("t_"))
async def run_test(call: types.CallbackQuery, state: FSMContext):
    questions = [
        "Часто ловлю себя на мысли: «А что обо мне подумают?»",
        "Чувствую фоновую вину, когда выбираю отдых вместо дел.",
        "Мне сложно сказать «нет», даже если ресурс на нуле.",
        "Я автоматически подстраиваюсь под настроение других.",
        "Мои планы легко рушатся из-за чужих просьб.",
        "Мне нужно подтверждение со стороны, что я всё делаю правильно."
    ]
    step = int(call.data.split("_")[1])
    data = await state.get_data()
    score = data.get("score", 0)
    if step > 0:
        score += int(call.data.split("_")[-1])
        await state.update_data(score=score)

    if step < len(questions):
        kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="Никогда (0)", callback_data=f"t_{step+1}_0")],
            [types.InlineKeyboardButton(text="Бывает иногда (2)", callback_data=f"t_{step+1}_2")],
            [types.InlineKeyboardButton(text="Да, это про меня (4)", callback_data=f"t_{step+1}_4")]
        ])
        await call.message.answer(f"Вопрос {step+1} из 6\n\n{questions[step]}", reply_markup=kb)
    else:
        if score <= 6: res_s = "Автор"; dsc = "У вас отличный уровень владения своей жизнью!"
        elif score <= 12: res_s = "Начинающий Автор"; dsc = "Вы уже на пути к управлению своей жизнью."
        else: res_s = "Заложник обстоятельств"; dsc = "Сейчас может казаться, что внешние факторы сильнее вас."
        
        await call.message.answer(f"Ваш результат: **{res_s}**\n\n{dsc}\n\nСформулируйте ваш запрос на бесплатную вводную консультацию (30 мин).", 
                                  reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="📝 Сформулировать запрос", callback_data="audit")]]),
                                  parse_mode="Markdown")

@dp.callback_query(F.data == "audit")
async def begin_audit(call: types.CallbackQuery, state: FSMContext):
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Деньги / Карьера", callback_data="s_Деньги"), types.InlineKeyboardButton(text="Отношения", callback_data="s_Отношения")],
        [types.InlineKeyboardButton(text="Самооценка", callback_data="s_Самооценка"), types.InlineKeyboardButton(text="Состояние", callback_data="s_Состояние")]
    ])
    await call.message.answer("Выберите сферу, которая требует внимания:", reply_markup=kb)
    await state.set_state(MPTSteps.sphere)

@dp.callback_query(MPTSteps.sphere)
async def sphere_set(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(sphere=call.data.split("_")[1])
    await call.message.answer("Опишите ситуацию (факты и ваши чувства):")
    await state.set_state(MPTSteps.problem)

@dp.message(MPTSteps.problem)
async def prob(m: types.Message, state: FSMContext):
    if not is_meaningful(m.text): return await m.answer("Опишите ситуацию чуть подробнее, чтобы наш диалог был конструктивным.")
    await state.update_data(p=m.text)
    await m.answer("Какой результат вы хотите получить? (опишите без частицы «НЕ»)")
    await state.set_state(MPTSteps.goal)

@dp.message(MPTSteps.goal)
async def goal(m: types.Message, state: FSMContext):
    if not is_meaningful(m.text): return await m.answer("Пожалуйста, опишите цель более развернуто.")
    await state.update_data(g=m.text)
    kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="🔄 Изменить запрос/сферу", callback_data="audit")]])
    await m.answer("На сколько % этот результат зависит лично от вас?", reply_markup=kb)
    await state.set_state(MPTSteps.control)

@dp.message(MPTSteps.control)
async def ctrl(m: types.Message, state: FSMContext):
    txt = m.text.lower()
    if any(x in txt for x in ["мен", "назад", "сфер", "занов"]):
        kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="🔄 Вернуться в начало", callback_data="audit")]])
        return await m.answer("Вы можете изменить запрос:", reply_markup=kb)

    try:
        val = int(''.join(filter(str.isdigit, m.text)))
        if val < 70:
            kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="🔄 Сменить сферу/запрос", callback_data="audit")]])
            return await m.answer(f"Когда ответственность {val}%, управление не в ваших руках. Попробуйте найти грань, где вы отвечаете за результат максимально, или измените запрос.", reply_markup=kb)
        await state.update_data(c=val)
        await m.answer("Что вы начнете делать иначе, когда почувствуете себя Автором в этой ситуации?")
        await state.set_state(MPTSteps.reality)
    except:
        await m.answer("Напишите число (например, 100) или нажмите кнопку выше для смены сферы.")

@dp.message(MPTSteps.reality)
async def real(m: types.Message, state: FSMContext):
    if not is_meaningful(m.text): return await m.answer("Опишите ваши изменения чуть подробнее.")
    await state.update_data(r=m.text)
    await m.answer("Почему для вас важно решить этот вопрос именно сейчас?")
    await state.set_state(MPTSteps.motivation)

@dp.message(MPTSteps.motivation)
async def final(m: types.Message, state: FSMContext):
    if not is_meaningful(m.text): return await m.answer("Поделитесь вашим смыслом — почему это важно?")
    d = await state.get_data()
    rep = (f"🔥 ЗАЯВКА\nКлиент: {m.from_user.full_name} (@{m.from_user.username})\n"
           f"Сфера: {d['sphere']}\nСитуация: {d['p']}\nЦель: {d['g']}\n"
           f"Ответственность: {d['c']}%\nИзменения: {d['r']}\nСмысл: {m.text}")
    if ADMIN_ID: await bot.send_message(ADMIN_ID, rep)
    await m.answer("Ваш запрос принят! Я свяжусь с вами в личные сообщения.")
    await state.clear()

async def main():
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000))), daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
