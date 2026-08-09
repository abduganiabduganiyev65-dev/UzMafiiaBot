import telebot
from telebot import types
from pyrogram import Client, enums, errors
import asyncio
import os
import threading
import json
import time
import random

# ==========================================
# ⚙️ ASOSIY KONFIGURATSIYA
# ==========================================
API_ID = 20442311
API_HASH = '76105fee0bca80c50bb4fb41ef9626df'
BOT_TOKEN = '8719639167:AAGZz24ve7izCgN54xLBvmJkzqc09pb6SHo'
ADMIN_ID = 8503132512 
MJ_KANAL = "AutoXabarci" 
FOLDER_LINK = "https://t.me/addlist/kHJRM1BD0zFiNTVi"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")
main_loop = asyncio.new_event_loop()

def run_async_loop():
    asyncio.set_event_loop(main_loop)
    try: main_loop.run_forever()
    except: pass

threading.Thread(target=run_async_loop, daemon=True).start()

# ==========================================
# 📂 DATA MANAGER
# ==========================================
DATA_FILE = "autoxabarci_pro_v3.json"
def load_all_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return {"users": {}, "admins": [], "fwd_active": True}
    return {"users": {}, "admins": [], "fwd_active": True}

db = load_all_data()
def save_all_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

active_clients = {}
stop_flags = {}
user_ads = {}
user_intervals = {}
group_limits = {}
msg_counters = {}

# ==========================================
# 🛡 CHEKLOVLAR (SUB & LOG)
# ==========================================
def check_sub(uid):
    if uid == ADMIN_ID: return True
    try:
        status = bot.get_chat_member(f"@{MJ_KANAL}", uid).status
        return status in ['member', 'administrator', 'creator']
    except: return False

def is_logged_in(uid):
    return os.path.exists(f"session_{uid}.session")

# ==========================================
# 🛠 KLAVIATURALAR (RASMDEGIDEK)
# ==========================================
def get_main_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    # Agar obuna bo'lmagan yoki login qilmagan bo'lsa faqat cheklangan menyu
    if not check_sub(user_id) or not is_logged_in(user_id):
        markup.add(types.KeyboardButton("📱 Akkauntni Ulash", request_contact=True))
        return markup

    # To'liq menyu faqat login qilgandan keyin
    markup.add(types.KeyboardButton("🚀 Reklamani Yoqish"), types.KeyboardButton("🛑 To'xtatish"))
    markup.add(types.KeyboardButton("🖼 Reklamani Sozlash"), types.KeyboardButton("🔄 Forward Sozlash"))
    markup.add(types.KeyboardButton("⏱ Interval"), types.KeyboardButton("🔢 Guruh Limiti"))
    markup.add(types.KeyboardButton("📂 Guruhlarga qo'shilish"))
    markup.add(types.KeyboardButton("📊 Statistika"), types.KeyboardButton("👤 Akkauntni o'chirish"))
    
    if int(user_id) == ADMIN_ID:
        markup.add(types.KeyboardButton("👨‍💻 Admin Panel"))
    return markup

# ==========================================
# 🚀 START & AUTH (RASMDI TEXTLARI BILAN)
# ==========================================
@bot.message_handler(commands=['start'])
def welcome_message(message):
    uid = message.from_user.id
    if not check_sub(uid):
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("A'zo bo'lish ➕", url=f"https://t.me/{MJ_KANAL}"))
        return bot.send_message(message.chat.id, "❌ Botdan foydalanish uchun kanalga a'zo bo'ling!", reply_markup=kb)
    
    if not is_logged_in(uid):
        text = ("👋 Assalomu alaykum!\nAutoHabar botga xush kelibsiz!\n\n"
                "✅ Autohabar yuborish uchun akkauntingizni ulang\n"
                "📧 Hammasi xavfsiz saqlanadi\n\n"
                "🟢 Telefon raqamingizni yuboring:\n"
                "yoki pastdagi tugmani bosing")
        return bot.send_message(uid, text, reply_markup=get_main_keyboard(uid))

    bot.send_message(uid, "✨ AutoXabarci V11 Pro menyusi:", reply_markup=get_main_keyboard(uid))
    @bot.message_handler(content_types=['contact'])
def handle_contact_auth(m):
    uid = m.from_user.id
    if not check_sub(uid): return
    phone = m.contact.phone_number
    bot.send_message(uid, "⏳ Kod so'ralmoqda...")
    
    async def login_task():
        cl = Client(f"session_{uid}", API_ID, API_HASH)
        await cl.connect()
        try:
            code_info = await cl.send_code(phone)
            active_clients[uid] = {"cl": cl, "phone": phone, "hash": code_info.phone_code_hash}
            
            text = (f"✅ Tasdiqlash kodi yuborildi!\n\n📱 Raqam: {phone}\n\n"
                    "⚠️ MUHIM: Kod Telegramingizga keldi\n\n"
                    "✏️ Kodni shunday yozing:\n"
                    "• Orasiga nuqta qo'ying: 1.2.3.4.5\n\n"
                    "❌ /cancel — bekor qilish")
            bot.send_message(uid, text)
            bot.register_next_step_handler(m, verify_telegram_code)
        except Exception as e: bot.send_message(uid, f"❌ Xato: {e}")
    
    asyncio.run_coroutine_threadsafe(login_task(), main_loop)

def verify_telegram_code(m):
    uid = m.from_user.id
    if m.text == "/cancel": return bot.send_message(uid, "Bekor qilindi.", reply_markup=get_main_keyboard(uid))
    code = m.text.replace(".", "").strip()
    
    async def verify_task():
        try:
            d = active_clients[uid]
            await d["cl"].sign_in(d["phone"], d["hash"], code)
            bot.send_message(uid, "✅ Ulandi!", reply_markup=get_main_keyboard(uid))
        except errors.SessionPasswordNeeded:
            text = "🔐 2 bosqichli tasdiqlash\n\nParolni kiriting:\n\n❌ /cancel — bekor qilish"
            bot.send_message(uid, text)
            bot.register_next_step_handler(m, verify_2fa)
        except Exception as e: bot.send_message(uid, f"❌ Xato: {e}")
    
    asyncio.run_coroutine_threadsafe(verify_task(), main_loop)

def verify_2fa(m):
    uid = m.from_user.id
    if m.text == "/cancel": return bot.send_message(uid, "Bekor qilindi.", reply_markup=get_main_keyboard(uid))
    
    async def check_2fa_task():
        try:
            await active_clients[uid]["cl"].check_password(m.text)
            bot.send_message(uid, "✅ 2FA tasdiqlandi! Ulandi.", reply_markup=get_main_keyboard(uid))
        except: bot.send_message(uid, "❌ Parol noto'g'ri!")
    
    asyncio.run_coroutine_threadsafe(check_2fa_task(), main_loop)

# ==========================================
# 🚀 ENGINE & OTHERS (O'ZGARISHSIZ QOLDI)
# ==========================================
@bot.message_handler(func=lambda m: m.text == "🚀 Reklamani Yoqish")
def start_advertising_process(m):
    uid = m.from_user.id
    if not is_logged_in(uid): return
    if uid not in user_ads: return bot.send_message(uid, "❌ Avval reklamani sozlang!")

    stop_flags[uid] = False
    interval = user_intervals.get(uid, 10)
    status_msg = bot.send_message(uid, "📡 Ishga tushirilmoqda...")

    async def broadcast():
        try:
            cl = active_clients[uid]["cl"] if uid in active_clients else Client(f"session_{uid}", API_ID, API_HASH)
            if not cl.is_connected: await cl.start(); active_clients[uid] = {"cl": cl}
            
            sent_count = 0
            while not stop_flags.get(uid):
                ad = user_ads[uid]
                async for dialog in cl.get_dialogs():
                    if stop_flags.get(uid): break
                    if dialog.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
                        try:
                            if ad["type"] == "photo": await cl.send_photo(dialog.chat.id, ad["file_id"], caption=ad["caption"])
                            elif ad["type"] == "text": await cl.send_message(dialog.chat.id, ad["text"])
                            elif ad["type"] == "forward": await cl.forward_messages(dialog.chat.id, ad["from_chat_id"], ad["message_id"])
                                sent_count += 1
                            if sent_count % 5 == 0:
                                bot.edit_message_text(f"⏳ Yuborildi: {sent_count} ta guruhga.", uid, status_msg.id)
                            await asyncio.sleep(interval)
                        except errors.FloodWait as e: await asyncio.sleep(e.value + 5)
                        except: continue
                await asyncio.sleep(30)
        except Exception as e: bot.send_message(uid, f"❌ Xato: {e}")

    asyncio.run_coroutine_threadsafe(broadcast(), main_loop)

@bot.message_handler(func=lambda m: m.text == "🛑 To'xtatish")
def stop_process(m):
    stop_flags[m.from_user.id] = True
    bot.send_message(m.chat.id, "🛑 Reklama to'xtatildi!")

@bot.message_handler(func=lambda m: m.text == "📂 Guruhlarga qo'shilish")
def send_folder_link(message):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📂 Jildni qo'shish", url=FOLDER_LINK))
    bot.send_message(message.chat.id, "✅ Guruhlar jildi tayyor!", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "👤 Akkauntni o'chirish")
def delete_session(m):
    uid = m.from_user.id
    if os.path.exists(f"session_{uid}.session"):
        os.remove(f"session_{uid}.session")
        bot.send_message(m.chat.id, "🗑 Akkaunt o'chirildi.", reply_markup=get_main_keyboard(uid))

# Qolgan funksiyalar (Sozlash, Interval va h.k.) o'zgarishsiz ishlayveradi...

if name == "main":
    bot.infinity_polling()
