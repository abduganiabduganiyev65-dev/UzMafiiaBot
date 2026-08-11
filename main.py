import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web

# ==================== SOZLAMALAR ====================
BOT_TOKEN = "8798034167:AAHSY5h3gCQkQhboftc4CTvljW61lSxCKjA"
ADMIN_ID = 8405366288
CHANNEL_USERNAME = "@UzKinoFilmss"  # Majburiy obuna kanali
CHANNEL_URL = "https://t.me/UzKinoFilmss"

# ==================== MA'LUMOTLAR BAZASI ====================
def init_db():
    conn = sqlite3.connect("kino_base.db")
    cursor = conn.cursor()
    # Kinolar jadvali
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS movies (
            code TEXT PRIMARY KEY,
            file_id TEXT NOT NULL,
            caption TEXT
        )
    """)
    # Foydalanuvchilar jadvali
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ==================== BOT VA DISPATCHER ====================
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Majburiy obunani tekshirish funksiyasi
async def check_sub(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ["creator", "administrator", "member"]
    except Exception as e:
        logging.error(f"Obuna tekshirishda xatolik: {e}")
        return True # Xatolik bo'lsa bot to'xtab qolmasligi uchun

# Obuna bo'lish tugmasi
def get_sub_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Kanalga a'zo bo'lish", url=CHANNEL_URL)],
        [InlineKeyboardButton(text="✅ A'zo bo'ldim (Tekshirish)", callback_data="check_subscription")]
    ])
    return keyboard

# ==================== HANDLERLAR ====================

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    # Foydalanuvchini bazaga qo'shish
    conn = sqlite3.connect("kino_base.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.from_user.id,))
    conn.commit()
    conn.close()

    if not await check_sub(message.from_user.id):
        await message.answer(
            "⚠️ Botdan foydalanish uchun avval kanalimizga a'zo bo'ling:",
            reply_markup=get_sub_keyboard()
        )
        return

    await message.answer("👋 Xush kelibsiz!\n\n🔍 Kerakli kino kodini yuboring (Masalan: `101`):", parse_mode="Markdown")

@dp.callback_query(F.data == "check_subscription")
async def check_sub_callback(call: types.CallbackQuery):
    if await check_sub(call.from_user.id):
        await call.message.delete()
        await call.message.answer("✅ Rahmat! Endi kino kodini yuborishingiz mumkin.")
    else:
        await call.answer("❌ Siz hali kanalga a'zo bo'lmadingiz!", show_alert=True)

# Admin uchun kino qo'shish: Kino faylini yuborib, izohiga kodini yozadi (Masalan: 101)
@dp.message(F.video | F.document)
async def add_movie_handler(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    code = message.caption
    if not code:
        await message.answer("⚠️ Kinoga kod berish uchun videoni yuklayotganda Izoh (caption) qismiga kino kodini yozing (Masalan: 101).")
        return

    file_id = message.video.file_id if message.video else message.document.file_id

    conn = sqlite3.connect("kino_base.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO movies (code, file_id) VALUES (?, ?)", (code.strip(), file_id))
    conn.commit()
    conn.close()

    await message.answer(f"✅ Kino muvaffaqiyatli saqlandi!\n🔑 **Kino kodi:** `{code.strip()}`", parse_mode="Markdown")

# Kod bo'yicha kinoni qidirish
@dp.message(F.text)
async def search_movie(message: types.Message):
    if not await check_sub(message.from_user.id):
        await message.answer(
            "⚠️ Botdan foydalanish uchun avval kanalimizga a'zo bo'ling:",
            reply_markup=get_sub_keyboard()
        )
        return

    code = message.text.strip()
    
    conn = sqlite3.connect("kino_base.db")
    cursor = conn.cursor()
    cursor.execute("SELECT file_id FROM movies WHERE code = ?", (code,))
    result = cursor.fetchone()
    conn.close()

    if result:
        file_id = result[0]
        await message.answer_video(video=file_id, caption=f"🎬 Kino kodi: {code}\n\n🤖 @{(await bot.get_me()).username}")
    else:
        await message.answer("❌ Bunday kodli kino topilmadi. Qaytadan tekshirib ko'ring.")

# ==================== RENDER 24/7 ISHLASHI UCHUN VEB SERVER ====================
async def handle_ping(request):
    return web.Response(text="Bot 24/7 aktiv holatda ishlayapti!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 10000)
    await site.start()

# Main ishga tushirish
async def main():
    # Veb serverni orqa fonda berilgan portda yoqamiz
    asyncio.create_task(start_web_server())
    # Botni ishga tushiramiz
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
