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
# Прямая RAW ссылка на файл
PDF_GUIDE_URL = "https://raw.githubusercontent.com/Elektra174/meta-nav/main/Svoboda_guide.pdf"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class MPTSteps(StatesGroup):
    sphere = State(); problem = State(); goal = State(); control = State(); reality = State(); motivation = State()

# --- СУПЕР-ФИЛЬТР СМЫСЛА ---
def is_meaningful(text):
    if not text: return False
    
    # 1. Только кириллица
    if not re.search(r'[а-яА-Я]', text): return False
    
    # 2. Исключаем сообщения, состоящие только из знаков вопроса
    if text.strip() == "?" or (text.count('?') > 1 and len(text) < 10): return False
    
    # 3. Список "пустых" слов и отписок
    stop_words = {'привет', 'здравствуйте', 'тест', 'проверка', 'понятно', 'хорошо', 'нормально', 'окей', 'иди', 'нету', 'гладиолус', 'зачем', 'почему', 'хз', 'просто'}
    
    # 4. Считаем значимые уникальные слова
    words = re.findall(r'[а-яА-ЯёЁ]{2,}', text.lower())
    meaningful_words = {w for w in words if w not in stop_words}
    
    # ЛОГИКА: Минимум 3 уникальных слова И длина сообщения от 15 символов
    if len(meaningful_words) < 3 or len(text.strip()) < 15:
        return False
    
    return True

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

async def give_gift(chat_id):
    welcome_back = (
        "Ваша подписка активна.\n\n"
        "Привет! Меня зовут Александр Лазаренко, я психолог МПТ и автор проекта «Prosto психология | Метаформула жизни».\n\n"
        "Я помогаю людям обрести роль Автора своей реальности и выйти из режима ожидания.\n\n"
        "🎁 Ваш подарок: полный тест «Свобода быть собой» в формате PDF (отправляю ниже).\n\n"
        "Также предлагаю пройти мини-квиз, чтобы определить ваш текущий уровень авторства."
    )
    kb_start = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="🚀 Запустить мини-квиз", callback_data="t_0")]])
    try:
        await bot.send_photo(chat_id, photo=IMAGE_URL, caption=welcome_back)
        await bot.send_document(chat_id, document=PDF_GUIDE_URL, caption="Ваш подарок — Полный тест «Свобода быть собой» 🎁")
        await bot.send_message(chat_id, "Нажмите кнопку ниже, чтобы начать:", reply_markup=kb_start)
    except:
        await bot.send_message(chat_id, "Начинаем?", reply_markup=kb_start)

@dp.message(Command("start"))
async def start(msg: types.Message, state: FSMContext):
    await state.clear()
    is_sub = await check_sub(msg.from_user.id)
    if is_sub:
        await give_gift(msg.chat.id)
    else:
        welcome_text = (
            "Привет! Меня зовут Александр Лазаренко, я психолог МПТ и автор проекта «Prosto психология | Метаформула жизни».\n\n"
            "Я помогаю людям обрести роль Автора своей реальности и выйти из режима ожидания.\n\n"
            "🎁 Ваш подарок готов: полный тест «Свобода быть собой» в формате PDF.\n\n"
            "Чтобы забрать подарок и начать путь, подпишитесь на мой канал."
        )
        kb_sub = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="📢 Подписаться и получить подарок", url=CHANNEL_URL)],
            [types.InlineKeyboardButton(text="✅ Я подписался", callback_data="recheck")]
        ])
        try:
            await bot.send_photo(msg.chat.id, photo=IMAGE_URL, caption=welcome_text, reply_markup=kb_sub)
        except:
            await msg.answer(welcome_text, reply_markup=kb_sub)

@dp.callback_query(F.data == "recheck")
async def recheck(call: types.CallbackQuery, state: FSMContext):
    if await check_sub(call.from_user.id):
        await call.message.delete()
        await give_gift(call.message.chat.id)
    else:
        await call.answer("Нужна подписка на канал для получения подарка 🔄", show_alert=True)

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
            desc = "У вас отличный уровень владения своей жизнью! Чтобы выйти на новый масштаб и калибровать свои ориентиры, предлагаю сделать профессиональный разбор вашего актуального вызова."
        elif score <= 12:
            res_status = "Начинающий Автор"
            desc = "Вы уже на пути к управлению своей жизнью, но еще, возможно, остались сферы, где старые сценарии мешают двигаться быстрее. Предлагаю найти эти моменты и трансформировать их в ресурс."
        else:
            res_status = "Заложник обстоятельств"
            desc = "Сейчас может казаться, что внешние факторы сильнее вас. Это состояние забирает много сил, но его можно изменить, вернув фокус на свою личную силу."
        
        result_text = (
            f"Ваш результат: **{res_status}**\n\n{desc}\n\n"
            "Сформулируйте ваш запрос на бесплатную вводную консультацию (30 мин), и мы вместе проложим ваш авторский маршрут."
        )
        kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="📝 Сформулировать запрос", callback_data="audit")]])
        await call.message.answer(result_text, reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data == "audit")
async def begin_audit(call: types.CallbackQuery, state: FSMContext):
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Деньги / Карьера", callback_data="s_Деньги"), types.InlineKeyboardButton(text="Отношения", callback_data="s_Отношения")],
        [types.InlineKeyboardButton(text="Самооценка", callback_data="s_Самооценка"), types.InlineKeyboardButton(text="Состояние", callback_data="s_Состояние")]
    ])
    await call.message.answer("Выберите сферу, которая требует внимания в первую очередь:", reply_markup=kb)
    await state.set_state(MPTSteps.sphere)

@dp.callback_query(MPTSteps.sphere)
async def sphere_set(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(sphere=call.data.split("_")[1])
    await call.message.answer("Опишите ситуацию, которая сейчас создает напряжение (факты и ваши чувства):")
    await state.set_state(MPTSteps.problem)

@dp.message(MPTSteps.problem)
async def prob(m: types.Message, state: FSMContext):
    if not is_meaningful(m.text):
        return await m.answer("Пожалуйста, опишите ситуацию более развернуто (хотя бы одно предложение), чтобы я мог подготовиться к нашей встрече.")
    await state.update_data(p=m.text)
    await m.answer("Какой результат вы хотите получить? Опишите это без частицы «НЕ», как конкретное событие или состояние.")
    await state.set_state(MPTSteps.goal)

@dp.message(MPTSteps.goal)
async def goal(m: types.Message, state: FSMContext):
    if not is_meaningful(m.text): 
        return await m.answer("Пожалуйста, опишите цель более подробно.")
    if "не " in m.text.lower():
        return await m.answer("В МПТ мы идем К результату. Попробуйте сформулировать цель без частицы «НЕ».")
    await state.update_data(g=m.text)
    await m.answer("На сколько % этот результат зависит лично от вас?")
    await state.set_state(MPTSteps.control)

@dp.message(MPTSteps.control)
async def ctrl(m: types.Message, state: FSMContext):
    try:
        val_str = ''.join(filter(str.isdigit, m.text))
        if not val_str: raise ValueError
        val = int(val_str)
        if val < 70:
            return await m.answer(f"Когда ответственность составляет {val}%, управление остается в чужих руках. Попробуйте найти ту грань запроса, где вы будете отвечать за результат максимально.")
        await state.update_data(c=val)
    except: return await m.answer("Напишите числом (например, 100).")
    await m.answer("Что вы начнете делать иначе, когда почувствуете себя Автором в этой ситуации?")
    await state.set_state(MPTSteps.reality)

@dp.message(MPTSteps.reality)
async def real(m: types.Message, state: FSMContext):
    if not is_meaningful(m.text): 
        return await m.answer("Опишите ваши будущие действия чуть подробнее.")
    await state.update_data(r=m.text)
    await m.answer("Почему для вас важно решить этот вопрос именно сейчас?")
    await state.set_state(MPTSteps.motivation)

@dp.message(MPTSteps.motivation)
async def final(m: types.Message, state: FSMContext):
    if not is_meaningful(m.text): 
        return await m.answer("Поделитесь вашим истинным смыслом — почему это действительно важно?")
    d = await state.get_data()
    rep = (f"🔥 НОВАЯ ЗАЯВКА\n\n"
           f"Клиент: {m.from_user.full_name} (@{m.from_user.username})\n"
           f"Сфера: {d['sphere']}\n"
           f"Ситуация: {d['p']}\n"
           f"Цель: {d['g']}\n"
           f"Ответственность: {d['c']}%\n"
           f"Изменения: {d['r']}\n"
           f"Смысл: {m.text}")
    if ADMIN_ID: await bot.send_message(ADMIN_ID, rep)
    await m.answer("Ваш запрос принят! Я изучу ваши ответы и напишу вам в личные сообщения, чтобы договориться о встрече.")
    await state.clear()

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))

async def main():
    threading.Thread(target=run_flask, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
