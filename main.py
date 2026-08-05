import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

# --- SOZLAMALAR ---
BOT_TOKEN = "8902585083:AAE0reQEDoaolOyhySA1kwi0K27SA9PZxWU"  # Yangi tokeningizni qo'ying
ADMIN_ID = 8661312143

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- MA'LUMOTLAR BAZASI ---
def init_db():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            is_vip INTEGER DEFAULT 0,
            interval_sec REAL DEFAULT 300.0,
            auto_status INTEGER DEFAULT 0,
            msg_text TEXT DEFAULT 'Salom! Bu avto-xabar.'
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_user(user_id):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT is_vip, interval_sec, auto_status, msg_text FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    if not res:
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        res = (0, 300.0, 0, 'Salom! Bu avto-xabar.')
    conn.close()
    return {"is_vip": res[0], "interval": res[1], "status": res[2], "text": res[3]}

def update_user(user_id, **kwargs):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    for key, val in kwargs.items():
        cursor.execute(f"UPDATE users SET {key} = ? WHERE user_id = ?", (val, user_id))
    conn.commit()
    conn.close()

# --- HOLATLAR (FSM) ---
class BotState(StatesGroup):
    waiting_for_text = State()
    waiting_for_interval = State()

# --- TUGMALAR ---
def main_keyboard(user_id):
    kb = [
        [KeyboardButton(text="⚡️ Boshqaruv paneli")],
        [KeyboardButton(text="👤 Profillar"), KeyboardButton(text="👑 Pro tarif")],
        [KeyboardButton(text="👤 Kabinet"), KeyboardButton(text="⚙️ Sozlamalar")],
        [KeyboardButton(text="🗓 Kalendar"), KeyboardButton(text="🔧 Foydali funksiyalar")],
        [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="❓ Yordam")],
        [KeyboardButton(text="📖 Qo'llanma")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def control_panel_inline():
    kb = [
        [InlineKeyboardButton(text="🔮 Autohabar yuborish", callback_data="toggle_auto"),
         InlineKeyboardButton(text="💬 Habar matni", callback_data="set_text")],
        [InlineKeyboardButton(text="⏱ Interval", callback_data="set_interval"),
         InlineKeyboardButton(text="💬 Guruhlarni sozlash", callback_data="set_groups")],
        [InlineKeyboardButton(text="🔄 Autoreply", callback_data="set_autoreply")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- HANDLERLAR ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    u = get_user(message.from_user.id)
    vip_str = "💎 VIP" if u["is_vip"] else "💙 Bepul"
    status_str = "🟢 Yoqilgan" if u["status"] else "❌ O'chiq"
    
    text = (
        f"🚀 Avtorassylka Botiga Xush Kelibsiz!\n\n"
        f"🌌 Auto Habar: {status_str}\n"
        f"⭐️ Sizning Tarifingiz: {vip_str}\n"
        f"⏱ Interval: {u['interval']} soniya\n\n"
        f"👇 *Kerakli tugmani pastdan tanlang:*"
    )
    await message.answer(text, reply_markup=main_keyboard(message.from_user.id), parse_mode="Markdown")

@dp.message(F.text == "⚡️ Boshqaruv paneli")
async def control_panel_msg(message: types.Message):
    u = get_user(message.from_user.id)
    vip_str = "💎 VIP" if u["is_vip"] else "💙 Bepul"
    status_str = "🟢 Yoqilgan" if u["status"] else "❌ O'chiq"
    
    text = (
        f"⚙️ Boshqaruv Paneli\n\n"
        f"🌌 Auto Habar: {status_str}\n"
        f"⭐️ Sizning Tarifingiz: {vip_str}\n"
        f"⏱ Interval: {u['interval']} soniya\n"
        f"💬 Joriy matn: {u['text']}"
    )
    await message.answer(text, reply_markup=control_panel_inline(), parse_mode="Markdown")

@dp.callback_query(F.data == "toggle_auto")
async def toggle_auto_send(call: types.CallbackQuery):
    u = get_user(call.from_user.id)
    new_status = 0 if u["status"] else 1
    update_user(call.from_user.id, auto_status=new_status)
    
    st_text = "yoqildi 🟢" if new_status else "o'chirildi ❌"
    await call.answer(f"Autohabar {st_text}", show_alert=True)
    await control_panel_msg(call.message)

@dp.callback_query(F.data == "set_text")
async def ask_text(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("📝 Avto-yuboriladigan yangi matnni kiriting:")
    await state.set_state(BotState.waiting_for_text)
    await call.answer()

@dp.message(BotState.waiting_for_text)
async def save_text(message: types.Message, state: FSMContext):
    update_user(message.from_user.id, msg_text=message.text)
    await message.answer("✅ Matn muvaffaqiyatli saqlandi!")
    await state.clear()

@dp.callback_query(F.data == "set_interval")
async def ask_interval(call: types.CallbackQuery, state: FSMContext):
    u = get_user(call.from_user.id)
    limit_info = "VIP foydalanuvchilar: minimum 0.1s\nOddiy foydalanuvchilar: minimum 0.5s - maximum 300s (5 minut)" if u["is_vip"] else "Oddiy tarifdasiz: Min 0.5s, Max 300s."
    await call.message.answer(f"⏱ Yangi intervalni soniyalarda kiriting:\n\n{limit_info}")
    await state.set_state(BotState.waiting_for_interval)
    await call.answer()

@dp.message(BotState.waiting_for_interval)
async def save_interval(message: types.Message, state: FSMContext):
    u = get_user(message.from_user.id)
    try:
        val = float(message.text)
        min_limit = 0.1 if u["is_vip"] else 0.5
        if val < min_limit:
            await message.answer(f"❌ Siz uchun minimal interval: {min_limit} soniya!")
            return
        update_user(message.from_user.id, interval_sec=val)
        await message.answer(f"✅ Interval {val} soniyaga o'zgartirildi.")
        await state.clear()
    except ValueError:
        await message.answer("⚠️ Iltimos, faqat raqam kiriting (masalan: 5 yoki 0.5).")

@dp.message(F.text == "👑 Pro tarif")
async def pro_tariff(message: types.Message):
    await message.answer(f"👑 VIP Status Olish\n\nVIP imkoniyatlari:\n• Minimal interval 0.1 sekunda\n• Cheksiz guruhlarga yuborish\n\nAdmin bilan bog'lanish: @id{ADMIN_ID}", parse_mode="Markdown")

# --- AVTO YUBORISH FON VAZIFASI ---
async def auto_sender_loop():
    while True:
        await asyncio.sleep(5)
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, interval_sec, msg_text FROM users WHERE auto_status = 1")
        active_users = cursor.fetchall()
        conn.close()

        for u_id, interval, msg in active_users:
            # Bu yerda guruhlarga xabar yuborish kodi bajariladi
            pass

async def main():
    asyncio.create_task(auto_sender_loop())
    await dp.start_polling(bot)

if name == "main":
    asyncio.run(main())
