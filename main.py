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
PDF_GUIDE_URL = "https://raw.githubusercontent.com/Elektra174/meta-nav/main/Test_Svoboda.pdf"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class MPTSteps(StatesGroup):
    sphere = State(); problem = State(); goal = State(); control = State(); reality = State(); motivation = State()

def is_meaningful(text):
    if not text: return False
    text = text.strip().lower()
    if len(text) < 10: return False 
    if not re.search(r'[аеёиоуыэюя]', text): return False
    if re.search(r'[бвгджзйклмнпрстфхцчшщ]{5,}', text): return False
    return True

async def check_sub(user_id):
    try:
        m = await bot.get_chat_member(CHANNEL_ID, user_id)
        return m.status in ['member', 'administrator', 'creator']
    except: return False

async def give_gift(chat_id):
    welcome_back = (
        "Ваша подписка активна! 🌿\n\n"
        "Привет! Я Александр Лазаренко. Рад вашему интересу к теме Авторства и внутренней свободы.\n\n"
        "🎁 Как и обещал, отправляю вам **полный тест «Свобода быть собой»** в формате PDF.\n\n"
        "Также предлагаю пройти короткий квиз, чтобы увидеть, насколько вы сейчас проявляетесь как Автор своей жизни."
    )
    kb_start = types.InlineKeyboardMarkup(inline_keyboard=[[
        types.InlineKeyboardButton(text="🚀 Начать квиз", callback_data="t_0")
    ]])
    try:
        await bot.send_photo(chat_id, photo=IMAGE_URL, caption=welcome_back, parse_mode="Markdown")
        await bot.send_document(chat_id, document=PDF_GUIDE_URL, caption="Ваш подарок 🎁")
        await bot.send_message(chat_id, "Начнем?", reply_markup=kb_start)
    except:
        await bot.send_message(chat_id, "Начать квиз?", reply_markup=kb_start)

@dp.message(Command("start", "reset"))
async def start(msg: types.Message, state: FSMContext):
    await state.clear()
    if await check_sub(msg.from_user.id):
        await give_gift(msg.chat.id)
    else:
        text = (
            "Привет! Я Александр Лазаренко, психолог МПТ и автор проекта **«Prosto психология | Метаформула жизни»**.\n\n"
            "Здесь мы исследуем, как перестать бороться с обстоятельствами и обнаружить право быть Автором своей жизни.\n\n"
            "🎁 Чтобы забрать подарок и запустить Навигатор, подпишитесь на мой канал."
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
    questions = [
        "Часто думаю о том, что скажут другие, когда принимаю решение.",
        "Мне трудно сделать выбор, если близкие будут недовольны.",
        "Я чувствую сильную вину, когда делаю что-то «для себя».",
        "Мне трудно отказать, даже когда просьба мне неудобна.",
        "Я регулярно подстраиваю свои планы под желания других.",
        "Мне нужно одобрение, чтобы понять, что я всё делаю правильно."
    ]
    step = int(call.data.split("_")[1])
    data = await state.get_data()
    score = data.get("score", 0)
    if step > 0: score += int(call.data.split("_")[-1])
    await state.update_data(score=score)

    if step < len(questions):
        kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="Никогда (0)", callback_data=f"t_{step+1}_0")],
            [types.InlineKeyboardButton(text="Иногда (2)", callback_data=f"t_{step+1}_2")],
            [types.InlineKeyboardButton(text="Всегда (4)", callback_data=f"t_{step+1}_4")]
        ])
        await call.message.answer(f"Вопрос {step+1} из {len(questions)}:\n\n{questions[step]}", reply_markup=kb)
    else:
        if score <= 6:
            res_n, res_t = "Автор", "Поздравляю! Это состояние, когда вы ясно слышите себя и действуете из внутреннего выбора."
        elif score <= 12:
            res_n, res_t = "Начинающий Автор", "Вы уже на пути к свободе. Но всё ещё есть зоны, где привычка быть удобным берет верх."
        elif score <= 18:
            res_n, res_t = "Заложник", "Сейчас значительная часть внимания захвачена Контролером. Это забирает много сил."
        else:
            res_n, res_t = "Жертва", "Сейчас вы в эпицентре давления. Но именно отсюда начинается переход к себе."
        
        full_res = f"Ваш текущий результат: **{res_n}**\n\n{res_t}\n\nХотите исследовать ситуацию детальнее?"
        kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="🔍 Исследовать ситуацию", callback_data="audit")]])
        await call.message.answer(full_res, reply_markup=kb, parse_mode="Markdown")

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
    if not is_meaningful(m.text): return await m.answer("Пожалуйста, опишите ситуацию подробнее (хотя бы одно полноценное предложение).")
    await state.update_data(p=m.text)
    await m.answer("К какому внутреннему состоянию вы бы хотели прийти? (опишите его без частицы «НЕ»)")
    await state.set_state(MPTSteps.goal)

@dp.message(MPTSteps.goal)
async def goal(m: types.Message, state: FSMContext):
    if not is_meaningful(m.text): return await m.answer("Попробуйте описать ваше желаемое состояние словами.")
    await state.update_data(g=m.text)
    await m.answer("На сколько % ваше самоощущение зависит от вашего внутреннего выбора?")
    await state.set_state(MPTSteps.control)

@dp.message(MPTSteps.control)
async def ctrl(m: types.Message, state: FSMContext):
    try:
        val = int(''.join(filter(str.isdigit, m.text)))
        if val < 70:
            kb = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="🔄 Попробовать еще раз", callback_data="audit")],
                [types.InlineKeyboardButton(text="➡️ Всё равно продолжить", callback_data="skip_low_percent")]
            ])
            return await m.answer(
                f"Похоже, сейчас фокус смещен на внешние факторы ({val}%). В МПТ мы ищем ту грань, где выбор остается за вами.\n\n"
                "Хотите попробовать описать ситуацию иначе или продолжим как есть?", 
                reply_markup=kb
            )
        await state.update_data(c=val)
        await m.answer("Что нового обнаружится в вашем состоянии, когда вы вернёте себе роль Автора?")
        await state.set_state(MPTSteps.reality)
    except: await m.answer("Напишите число (например, 80).")

@dp.callback_query(F.data == "skip_low_percent")
async def skip_low(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("Хорошо, идем дальше. Что нового обнаружится в вашем состоянии, когда вы вернёте себе роль Автора?")
    await state.set_state(MPTSteps.reality)

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
    rep = (f"🚀 НОВАЯ ЗАЯВКА\n"
           f"Клиент: {m.from_user.full_name} (@{m.from_user.username})\n"
           f"Сфера: {d['sphere']}\n"
           f"Ситуация: {d['p']}\n"
           f"Цель: {d['g']}\n"
           f"Субъектность: {d.get('c', 'менее 70') or 'менее 70'}%\n"
           f"Новое восприятие: {d['r']}\n"
           f"Смысл/Почему важно: {m.text}")
    
    if ADMIN_ID: await bot.send_message(ADMIN_ID, rep)
    
    final_text = (
        "✅ **Ваше исследование успешно завершено!**\n\n"
        "Благодарю за доверие. Я получил ваш запрос и внимательно изучу его.\n\n"
        "Это осознание — ваш первый шаг к выходу из привычных паттернов. "
        "Я свяжусь с вами в ближайшее время, чтобы договориться о бесплатной вводной встрече (30 мин), "
        "где мы вместе разберем точки самоблокировки и наметим кратчайший путь к вашему естественному Авторству в жизни."
    )
    await m.answer(final_text, parse_mode="Markdown")
    await state.clear()

async def main():
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000))), daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
