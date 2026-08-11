# ==============================================================================
# FULL PRODUCTION-READY 24/7 TELEGRAM KINO BOT
# Stack: Aiogram 3, Aiosqlite, Aiohttp (Keep-Alive Server for Render)
# Bot Token: 8798034167:AAHSY5h3gCQkQhboftc4CTvljW61lSxCKjA
# Admin ID: 8405366288 (@Abdugani_177)
# Mandatory Channel: @UzKinoFilmss
# ==============================================================================

import os
import sys
import asyncio
import logging
import sqlite3
import aiosqlite
from aiohttp import web, ClientSession

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    CallbackQuery,
    Message,
    FSInputFile
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

# --- LOGGING SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
BOT_TOKEN = "8798034167:AAHSY5h3gCQkQhboftc4CTvljW61lSxCKjA"
ADMIN_ID = 8405366288
ADMIN_USERNAME = "@Abdugani_177"
CHANNEL_USERNAME = "@UzKinoFilmss"
CHANNEL_URL = "https://t.me/UzKinoFilmss"
DB_PATH = "kino_database.db"
PORT = int(os.environ.get("PORT", 10000))

# --- FSM STATES ---
class AdminStates(StatesGroup):
    waiting_for_movie_code = State()
    waiting_for_movie_file = State()
    waiting_for_movie_caption = State()
    waiting_for_delete_code = State()
    waiting_for_broadcast_msg = State()
    waiting_for_channel_username = State()

# --- DATABASE SETUP ---
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS movies (
                code TEXT PRIMARY KEY,
                file_id TEXT NOT NULL,
                caption TEXT,
                views INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        await db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('channel', ?)", (CHANNEL_USERNAME,))
        await db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('channel_url', ?)", (CHANNEL_URL,))
        await db.commit()

async def get_setting(key: str, default: str = "") -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM settings WHERE key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else default

async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        await db.commit()

# --- BOT & DISPATCHER INIT ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- HELPER FUNCTIONS ---
async def check_user_subscription(user_id: int) -> bool:
    target_channel = await get_setting("channel", CHANNEL_USERNAME)
    try:
        member = await bot.get_chat_member(chat_id=target_channel, user_id=user_id)
        return member.status in ["creator", "administrator", "member"]
    except Exception as e:
        logger.error(f"Error checking subscription for user {user_id}: {e}")
        return True  # If bot error occurs, do not block user

async def get_subscription_keyboard():
    channel_link = await get_setting("channel_url", CHANNEL_URL)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Kanalga obuna bo'lish", url=channel_link)],
        [InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_subscription")]
    ])
    return keyboard

def get_admin_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎬 Kino Qo'shish"), KeyboardButton(text="🗑 Kino O'chirish")],
            [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="📢 Xabar Yuborish")],
            [KeyboardButton(text="📁 Barcha Kinolar"), KeyboardButton(text="⚙️ Kanal Sozlamasi")],
            [KeyboardButton(text="◀️ Bosh sahifa")]
        ],
        resize_keyboard=True
    )
    return keyboard

def get_main_keyboard(user_id: int):
    buttons = [
        [KeyboardButton(text="🔍 Kino qidirish"), KeyboardButton(text="🔥 Top kinolar")],
        [KeyboardButton(text="ℹ️ Yordam / Biz haqimizda")]
    ]
    if user_id == ADMIN_ID:
        buttons.append([KeyboardButton(text="👨‍💻 Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# --- USER HANDLERS ---

@dp.message(CommandStart())
async def start_handler(message: Message):
    user_id = message.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        await db.commit()

    is_subscribed = await check_user_subscription(user_id)
    if not is_subscribed:
        await message.answer(
            "⚠️ **Botdan foydalanish uchun quyidagi kanalimizga obuna bo'lishingiz shart!**\n\n"
            "Obuna bo'lgach **'✅ Obunani tekshirish'** tugmasini bosing.",
            reply_markup=await get_subscription_keyboard(),
            parse_mode="Markdown"
        )
        return

    text = (
        f"👋 **Xush kelibsiz, {message.from_user.first_name}!**\n\n"
        f"🎬 Ushbu bot orqali siz o'zingizga yoqqan kinolarni kodini yuborib yuklab olishingiz mumkin.\n\n"
        f"🔍 **Kino kodini kiriting:** (Masalan: `101`, `102`)"
    )
    await message.answer(text, reply_markup=get_main_keyboard(user_id), parse_mode="Markdown")

@dp.callback_query(F.data == "check_subscription")
async def check_subscription_callback(call: CallbackQuery):
    user_id = call.from_user.id
    is_subscribed = await check_user_subscription(user_id)
    if is_subscribed:
        await call.message.delete()
        await call.message.answer(
            "✅ **Rahmat! Obuna tasdiqlandi.**\n\nEndi kino kodini yuborishingiz mumkin:",
            reply_markup=get_main_keyboard(user_id),
            parse_mode="Markdown"
        )
    else:
        await call.answer("❌ Siz hali kanalga obuna bo'lmadingiz! Iltimos, avval obuna bo'ling.", show_alert=True)

@dp.message(F.text == "◀️ Bosh sahifa")
async def back_to_main(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🏠 Bosh sahifadasiz.", reply_markup=get_main_keyboard(message.from_user.id))

@dp.message(F.text == "🔍 Kino qidirish")
async def search_movie_btn(message: Message):
    await message.answer("🔍 Kino yuklab olish uchun uning **kodini** yuboring (Masalan: `101`):", parse_mode="Markdown")

@dp.message(F.text == "🔥 Top kinolar")
async def top_movies(message: Message):
    if not await check_user_subscription(message.from_user.id):
        await message.answer("⚠️ Botdan foydalanish uchun kanalga obuna bo'ling:", reply_markup=await get_subscription_keyboard())
        return

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT code, views FROM movies ORDER BY views DESC LIMIT 10") as cursor:
            rows = await cursor.fetchall()

    if not rows:
        await message.answer("📋 Hozircha hech qanday kino mavjud emas.")
        return

    msg = "🔥 **Eng ko'p ko'rilgan TOP 10 kinolar:**\n\n"
    for idx, (code, views) in enumerate(rows, start=1):
        msg += f"{idx}. Kod: `{code}` — 👁 {views} marta ko'rilgan\n"
    msg += "\n🎬 Kinoni ko'rish uchun uning kodini botga yuboring!"
    await message.answer(msg, parse_mode="Markdown")

@dp.message(F.text == "ℹ️ Yordam / Biz haqimizda")
async def help_about(message: Message):
    msg = (
        "🤖 **Kino Bot haqida**\n\n"
        "Siz ushbu bot orqali istalgan koddagi kinolarni bir necha sekundda topishingiz mumkin.\n\n"
        f"👨‍💻 **Admin:** {ADMIN_USERNAME}\n"
        f"📢 **Rasmiy Kanal:** {CHANNEL_USERNAME}\n\n"
        "💡 Kinoni izlash uchun shunchaki uning raqamli kodini botga yozib yuboring."
    )
    await message.answer(msg, parse_mode="Markdown")

# --- ADMIN PANEL HANDLERS ---

@dp.message(F.text == "👨‍💻 Admin Panel")
async def admin_panel_btn(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Siz admin emassiz!")
        return
    await message.answer("👨‍💻 **Admin Boshqaruv Paneliga xush kelibsiz!**\nKerakli bo'limni tanlang:", reply_markup=get_admin_keyboard(), parse_mode="Markdown")

@dp.message(F.text == "📊 Statistika")
async def admin_stats(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as c1:
            total_users = (await c1.fetchone())[0]
        async with db.execute("SELECT COUNT(*), SUM(views) FROM movies") as c2:
            row = await c2.fetchone()
            total_movies = row[0] or 0
            total_views = row[1] or 0

    stats_text = (
        "📊 **Bot Statistikasi:**\n\n"
        f"👥 **Jami foydalanuvchilar:** `{total_users}` ta\n"
        f"🎬 **Jami kinolar soni:** `{total_movies}` ta\n"
        f"👁 **Jami ko'rishlar:** `{total_views}` marta\n\n"
        f"⚡️ Server holati: **24/7 Bepul Aktiv (Render)**"
    )
    await message.answer(stats_text, parse_mode="Markdown")

@dp.message(F.text == "🎬 Kino Qo'shish")
async def add_movie_start(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminStates.waiting_for_movie_code)
    await message.answer("🔑 Yangi kino uchun **kod** kiriting (Masalan: `101` yoki `A15`):", parse_mode="Markdown")

@dp.message(AdminStates.waiting_for_movie_code)
async def process_movie_code(message: Message, state: FSMContext):
    code = message.text.strip()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT code FROM movies WHERE code = ?", (code,)) as cursor:
            if await cursor.fetchone():
                await message.answer(f"⚠️ `{code}` kodli kino allaqachon mavjud! Boshqa kod kiriting:", parse_mode="Markdown")
                return

    await state.update_data(movie_code=code)
    await state.set_state(AdminStates.waiting_for_movie_file)
    await message.answer(f"✅ Kod `{code}` qabul qilindi.\n\n🎥 Endi **kino videosini** yuboring:")

@dp.message(AdminStates.waiting_for_movie_file, F.video | F.document)
async def process_movie_file(message: Message, state: FSMContext):
    file_id = message.video.file_id if message.video else message.document.file_id
    data = await state.get_data()
    code = data["movie_code"]

    caption = message.caption or f"🎬 Kino kodi: {code}\n🤖 @{(await bot.get_me()).username}"

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO movies (code, file_id, caption) VALUES (?, ?, ?)",
            (code, file_id, caption)
        )
        await db.commit()

    await state.clear()
    await message.answer(
        f"🎉 **Kino muvaffaqiyatli saqlandi!**\n\n🔑 Kino kodi: `{code}`",
        reply_markup=get_admin_keyboard(),
        parse_mode="Markdown"
    )

@dp.message(F.text == "🗑 Kino O'chirish")
async def delete_movie_start(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminStates.waiting_for_delete_code)
    await message.answer("🗑 O'chirmoqchi bo'lgan kinoning **kodini** kiriting:", parse_mode="Markdown")

@dp.message(AdminStates.waiting_for_delete_code)
async def process_delete_code(message: Message, state: FSMContext):
    code = message.text.strip()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT code FROM movies WHERE code = ?", (code,)) as cursor:
            row = await cursor.fetchone()

        if not row:
            await message.answer(f"❌ `{code}` kodli kino topilmadi. Qayta kiriting:", parse_mode="Markdown")
            return

        await db.execute("DELETE FROM movies WHERE code = ?", (code,))
        await db.commit()

    await state.clear()
    await message.answer(f"✅ `{code}` kodli kino bazadan o'chirib tashlandi!", reply_markup=get_admin_keyboard(), parse_mode="Markdown")

@dp.message(F.text == "📁 Barcha Kinolar")
async def list_all_movies(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT code, views FROM movies ORDER BY created_at DESC LIMIT 50") as cursor:
            rows = await cursor.fetchall()

    if not rows:
        await message.answer("📂 Bazada hech qanday kino yo'q.")
        return

    text = "📁 **Bazasidagi oxirgi 50 ta kino:**\n\n"
    for code, views in rows:
        text += f"• Kod: `{code}` | Ko'rishlar: {views}\n"
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "⚙️ Kanal Sozlamasi")
async def channel_setting_start(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    curr_channel = await get_setting("channel", CHANNEL_USERNAME)
    await state.set_state(AdminStates.waiting_for_channel_username)
    await message.answer(
        f"📢 Hozirgi majburiy obuna kanali: `{curr_channel}`\n\n"
        f"Yangi kanal username-ni yuboring (Masalan: `@UzKinoFilmss`):",
        parse_mode="Markdown"
    )

@dp.message(AdminStates.waiting_for_channel_username)
async def process_channel_username(message: Message, state: FSMContext):
    new_channel = message.text.strip()
    if not new_channel.startswith("@"):
        await message.answer("⚠️ Kanal username `@` bilan boshlanishi kerak. Qayta kiriting:")
        return

    await set_setting("channel", new_channel)
    await set_setting("channel_url", f"https://t.me/{new_channel.replace('@', '')}")
    await state.clear()
    await message.answer(f"✅ Majburiy obuna kanali `{new_channel}` ga o'zgartirildi!", reply_markup=get_admin_keyboard(), parse_mode="Markdown")

# --- BROADCASTING ---
@dp.message(F.text == "📢 Xabar Yuborish")
async def broadcast_start(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminStates.waiting_for_broadcast_msg)
    await message.answer("📢 Barcha foydalanuvchilarga yubormoqchi bo'lgan xabaringizni yuboring:")

@dp.message(AdminStates.waiting_for_broadcast_msg)
async def process_broadcast(message: Message, state: FSMContext):
    await state.clear()
    status_msg = await message.answer("⏳ Xabar yuborish boshlandi...")

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users") as cursor:
            users = await cursor.fetchall()

    success, failed = 0, 0
    for row in users:
        uid = row[0]
        try:
            await message.copy_to(chat_id=uid)
            success += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1

    await status_msg.edit_text(
        f"✅ **Xabar yuborish yakunlandi!**\n\n"
        f"🟢 Muvaffaqiyatli: `{success}` ta\n"
        f"🔴 Etib bormadi (bloklangan): `{failed}` ta",
        parse_mode="Markdown"
    )

# --- MOVIE SEARCH BY CODE ---
@dp.message(F.text)
async def search_movie_by_code(message: Message):
    user_id = message.from_user.id

    if not await check_user_subscription(user_id):
        await message.answer(
            "⚠️ **Botdan foydalanish uchun quyidagi kanalimizga obuna bo'lishingiz shart!**",
            reply_markup=await get_subscription_keyboard(),
            parse_mode="Markdown"
        )
        return

    code = message.text.strip()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT file_id, caption FROM movies WHERE code = ?", (code,)) as cursor:
            row = await cursor.fetchone()

        if row:
            file_id, caption = row
            await db.execute("UPDATE movies SET views = views + 1 WHERE code = ?", (code,))
            await db.commit()

            try:
                await message.answer_video(video=file_id, caption=caption or f"🎬 Kino kodi: {code}")
            except Exception:
                await message.answer_document(document=file_id, caption=caption or f"🎬 Kino kodi: {code}")
        else:
            await message.answer(
                f"❌ `{code}` kodli kino topilmadi!\n\n"
                f"Iltimos, kodni to'g'ri kiritganingizni tekshiring.",
                parse_mode="Markdown"
            )

# --- RENDER KEEP-ALIVE SERVER & SELF-PING TASK ---
async def handle_ping(request):
    return web.Response(text="Bot 24/7 ishlamoqda! Status: OK", status=200)

async def self_ping_task():
    """ Keeps Render Free instances awake 24/7 by pinging itself every 5 minutes """
    await asyncio.sleep(10)
    logger.info("Self-ping background task started.")
    while True:
        try:
            url = f"http://localhost:{PORT}/"
            async with ClientSession() as session:
                async with session.get(url) as resp:
                    logger.info(f"Self ping result: status {resp.status}")
        except Exception as e:
            logger.warning(f"Self-ping warning: {e}")
        await asyncio.sleep(300) # Every 5 minutes

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Web server running on port {PORT}")

# --- MAIN ENTRY POINT ---
async def main():
    await init_db()
    
    # Start web server
    asyncio.create_task(start_web_server())
    # Start self ping
    asyncio.create_task(self_ping_task())

    logger.info("Starting Bot Polling...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
