import telebot
from telebot import types
from pyrogram import Client, enums, errors
import asyncio
import os
import threading
import json
import time
import random
import sys
from flask import Flask

# ==========================================
# 🌐 RENDER 24/7 KEEP-ALIVE SERVER
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "AutoXabarci Bot 24/7 Active!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_flask, daemon=True).start()

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
    try:
        main_loop.run_forever()
    except Exception:
        pass

threading.Thread(target=run_async_loop, daemon=True).start()

# ==========================================
# 📂 DATA MANAGER
# ==========================================
DATA_FILE = "autoxabarci_pro_v3.json"

def load_all_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                content = json.load(f)
                defaults = {
                    "users": {}, "admins": [], "pro_users": {}, "global_ad": None,
                    "global_ad_status": True, "total_messages": 0,
                    "active_file": None, "admin_fwd_chat": None,
                    "admin_fwd_id": None, "fwd_active": True
                }
                for key, val in defaults.items():
                    if key not in content:
                        content[key] = val
                return content
        except Exception:
            return {"users": {}, "admins": [], "pro_users": {}, "fwd_active": True}
    return {"users": {}, "admins": [], "pro_users": {}, "fwd_active": True}

db = load_all_data()

def save_all_data(data_to_save):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, indent=4, ensure_ascii=False)
    except Exception:
        pass

active_clients = {}
stop_flags = {}
user_ads = {}
user_autoreply = {}
user_intervals = {}
msg_counters = {}

# ==========================================
# 🛡 MAJBURIY A'ZOLIK VA SESSION TEKSHIRUVI
# ==========================================
def check_sub(uid):
    if uid == ADMIN_ID or str(uid) in db.get("admins", []):
        return True
    try:
        status = bot.get_chat_member(f"@{MJ_KANAL}", uid).status
        return status in ['member', 'administrator', 'creator']
    except Exception:
        return False

def is_logged_in(uid):
    return os.path.exists(f"session_{uid}.session") or uid in active_clients

def is_pro(uid):
    return str(uid) in db.get("pro_users", {}) or uid == ADMIN_ID

# ==========================================
# 🛠 KLAVIATURALAR
# ==========================================
def get_main_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("🚀 Reklamani Yoqish"), types.KeyboardButton("🛑 To'xtatish"))
    markup.add(types.KeyboardButton("🖼 Reklamani Sozlash"), types.KeyboardButton("🔄 Forward Sozlash"))
    markup.add(types.KeyboardButton("💬 Avto-Javob Sozlash"), types.KeyboardButton("⏱ Interval"))
    markup.add(types.KeyboardButton("📂 Guruhlarga qo'shilish"), types.KeyboardButton("⭐ PRO Tarif"))
    markup.add(types.KeyboardButton("📊 Statistika"), types.KeyboardButton("❓ Yordam"))
    if not is_logged_in(user_id):
        markup.add(types.KeyboardButton("📱 Akkauntni Ulash", request_contact=True))
    
    if int(user_id) == ADMIN_ID or str(user_id) in db.get("admins", []):
        markup.add(types.KeyboardButton("👨‍💻 Admin Panel"))
    return markup

# ==========================================
# 📂 JILD (FOLDER) HANDLER
# ==========================================
@bot.message_handler(func=lambda m: m.text == "📂 Guruhlarga qo'shilish")
def send_folder_link(message):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📂 Jildni qo'shish", url=FOLDER_LINK))
    bot.send_message(
        message.chat.id, 
        "✅ Reklama tarqatish uchun guruhlar jildi tayyor!\n\nPastdagi tugmani bosib barcha guruhlarga bir marta qo'shilishingiz mumkin:", 
        reply_markup=kb
    )

# ==========================================
# 🚀 START HANDLER
# ==========================================
@bot.message_handler(commands=['start'])
def welcome_message(message):
    uid = message.from_user.id
    if not check_sub(uid):
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("A'zo bo'lish ➕", url=f"https://t.me/{MJ_KANAL}"))
        return bot.send_message(message.chat.id, "❌ Botdan foydalanish uchun kanalga a'zo bo'ling!", reply_markup=kb)
    
    if str(uid) not in db["users"]:
        db["users"][str(uid)] = {"name": message.from_user.first_name, "date": time.ctime()}
        save_all_data(db)
        
    bot.send_message(message.chat.id, "👋 Xush kelibsiz! AutoXabarci PRO xizmatingizda.", reply_markup=get_main_keyboard(uid))

# ==========================================
# ⭐ PRO TARIF VA YORDAM
# ==========================================
@bot.message_handler(func=lambda m: m.text == "⭐ PRO Tarif")
def pro_tariff_info(m):
    uid = m.from_user.id
    status = "🟢 Faol" if is_pro(uid) else "🔴 Oddiy foydalanuvchi"
    text = (
        f"⭐ PRO Tarif imkoniyatlari:\n\n"
        f"📌 Sizning maqomingiz: {status}\n\n"
        f"⚡ Imkoniyatlar:\n"
        f"• Cheksiz guruhlarga reklama yuborish\n"
        f"• Minimum 1 soniyalik interval imkoniyati\n"
        f"• Guruhdagi aktiv odamlarni avto-teg qilib yozish\n"
        f"• Serverda 24/7 ustuvor (priority) ishlash\n\n"
        f"💳 PRO faollashtirish uchun adminga murojaat qiling: @AutoXabarciAdmin"
    )
    bot.send_message(m.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "❓ Yordam")
def help_info(m):
    text = (
        "❓ Botdan foydalanish yo'riqnomasi:\n\n"
        "1️⃣ 📱 Akkauntni Ulash: Tugmani bosib telefon raqamingizni yuboring va Telegram kodingizni kiriting.\n"
        "2️⃣ 📂 Guruhlarga qo'shilish: Tayyor jild havolasi orqali barcha reklama guruhlariga qo'shiling.\n"
        "3️⃣ 🖼 Reklamani Sozlash: Guruhlarga yuborilishi kerak bo'lgan matn yoki rasmli reklamani saqlang.\n"
        "4️⃣ 💬 Avto-Javob Sozlash: Guruhlardagi oxirgi yozgan aktiv odamlarni avtomatiq teg qilib e'tiborini tortuvchi reklama sozlang.\n"
        "5️⃣ 🚀 Reklamani Yoqish: Boshlash tugmasini bosing va jarayon 24/7 avtomatik davom etadi."
    )
    bot.send_message(m.chat.id, text)

# ==========================================
# 💬 AVTO-JAVOB / AKTIV ODAMLARNI TEG QILISH
# ==========================================
@bot.message_handler(func=lambda m: m.text == "💬 Avto-Javob Sozlash")
def setup_autoreply(m):
    msg = bot.send_message(m.chat.id, "💬 Guruhdagi aktiv odamlarga qo'shib yuboriladigan matn yoki rasm+matn yuboring:")
    bot.register_next_step_handler(msg, process_autoreply_save)

def process_autoreply_save(m):
    if m.photo: 
        user_autoreply[m.from_user.id] = {"type": "photo", "file_id": m.photo[-1].file_id, "caption": m.caption or ""}
    elif m.text: 
        user_autoreply[m.from_user.id] = {"type": "text", "text": m.text}
    bot.send_message(m.chat.id, "✅ Avto-javob reklamasi saqlandi!")
    # ==========================================
# 👨‍💻 ADMIN PANEL
# ==========================================
@bot.message_handler(func=lambda m: m.text == "👨‍💻 Admin Panel")
def show_admin_panel(m):
    if int(m.from_user.id) != ADMIN_ID and str(m.from_user.id) not in db["admins"]:
        return
    fwd_status = "🟢 Yoqilgan" if db.get("fwd_active", True) else "🔴 O'chirilgan"
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("🛑 Hamma jarayonlarni to'xtatish", callback_data="adm_stop_all"),
        types.InlineKeyboardButton("🔄 Admin Forwardini sozlash", callback_data="adm_set_forward"),
        types.InlineKeyboardButton(f"⚙️ Forward: {fwd_status}", callback_data="adm_toggle_fwd"),
        types.InlineKeyboardButton("📢 Global Reklama", callback_data="admin_set_global")
    )
    bot.send_message(m.chat.id, "🛠 Admin Boshqaruv:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_") or c.data.startswith("admin_"))
def admin_calls(call):
    if int(call.from_user.id) != ADMIN_ID and str(call.from_user.id) not in db["admins"]:
        return
    if call.data == "adm_stop_all":
        for uid in stop_flags:
            stop_flags[uid] = True
        bot.answer_callback_query(call.id, "✅ Hammasi to'xtatildi!", show_alert=True)
    elif call.data == "adm_toggle_fwd":
        db["fwd_active"] = not db.get("fwd_active", True)
        save_all_data(db)
        show_admin_panel(call.message)
        bot.delete_message(call.message.chat.id, call.message.id)
    elif call.data == "adm_set_forward":
        msg = bot.send_message(call.message.chat.id, "🔄 Forward xabarni yuboring:")
        bot.register_next_step_handler(msg, save_admin_fwd_data)
    elif call.data == "admin_set_global":
        msg = bot.send_message(call.message.chat.id, "📝 Matn yuboring:")
        bot.register_next_step_handler(msg, process_global_broadcast)

def process_global_broadcast(m):
    users = db.get("users", {})
    success = 0
    for uid in users:
        try:
            bot.send_message(uid, m.text)
            success += 1
        except Exception:
            continue
    bot.send_message(m.chat.id, f"✅ Natija: {success}/{len(users)}")

def save_admin_fwd_data(m):
    if m.forward_from_chat:
        db["admin_fwd_chat"] = m.forward_from_chat.id
        db["admin_fwd_id"] = m.forward_from_message_id
        save_all_data(db)
        bot.send_message(m.chat.id, "✅ Saqlandi.")
    else:
        bot.send_message(m.chat.id, "❌ Faqat forward yuboring.")

# ==========================================
# 🚀 REKLAMA ENGINE (24/7 FIXED)
# ==========================================
async def run_broadcast(uid, status_msg):
    try:
        cl = active_clients[uid]["cl"] if uid in active_clients else Client(f"session_{uid}", API_ID, API_HASH)
        if not cl.is_connected:
            await cl.start()
            active_clients[uid] = {"cl": cl}
        
        bot.edit_message_text("🚀 Reklama tarqatish boshlandi...", uid, status_msg.id)
        msg_counters[uid] = 0
        sent_count = 0
        interval = user_intervals.get(uid, 5 if is_pro(uid) else 10)
        
        while not stop_flags.get(uid):
            dialogs = []
            async for dialog in cl.get_dialogs():
                if dialog.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]: 
                    dialogs.append(dialog.chat.id)
            
            random.shuffle(dialogs)
            for chat_id in dialogs:
                if stop_flags.get(uid):
                    break
                try:
                                    active_mentions = ""
                                    active_mentions += f"@{message.from_user.username} "
                                else:
                                    active_mentions += f"[{message.from_user.first_name}](tg://user?id={message.from_user.id}) "
                    except Exception:
                        pass

                    if uid in user_autoreply and active_mentions:
                        ar = user_autoreply[uid]
                        full_text = f"{active_mentions}\n\n{ar.get('caption', ar.get('text', ''))}"
                        if ar["type"] == "photo":
                            await cl.send_photo(chat_id, ar["file_id"], caption=full_text)
                        else:
                            await cl.send_message(chat_id, full_text)
                    elif uid in user_ads:
                        ad = user_ads[uid]
                        if ad["type"] == "photo":
                            await cl.send_photo(chat_id, ad["file_id"], caption=ad["caption"])
                        elif ad["type"] == "text":
                            await cl.send_message(chat_id, ad["text"])
                        elif ad["type"] == "forward":
                            await cl.forward_messages(chat_id, ad["from_chat_id"], ad["message_id"])
                    
                    sent_count += 1
                    msg_counters[uid] += 1
                    db["total_messages"] = db.get("total_messages", 0) + 1
                    
                    if msg_counters[uid] % 2 == 0 and db.get("admin_fwd_id") and db.get("fwd_active"):
                        try:
                            await cl.forward_messages(chat_id, db["admin_fwd_chat"], db["admin_fwd_id"])
                        except Exception:
                            pass

                    if sent_count % 5 == 0:
                        bot.edit_message_text(f"⏳ Yuborildi: {sent_count} ta guruhga.", uid, status_msg.id)
                    await asyncio.sleep(interval)
                except errors.FloodWait as e:
                    await asyncio.sleep(e.value + 5)
                except Exception as e:
                    if "Connection lost" in str(e): 
                        try:
                            await cl.connect()
                        except Exception:
                            pass
                    continue
            if stop_flags.get(uid):
                break
            await asyncio.sleep(20)
    except Exception as e:
        bot.send_message(uid, f"❌ Xato: {e}")

@bot.message_handler(func=lambda m: m.text == "🚀 Reklamani Yoqish")
def start_advertising_process(m):
    uid = m.from_user.id
    if not is_logged_in(uid):
        return bot.send_message(uid, "❌ Akkaunt ulanmagan!")
    if uid not in user_ads and uid not in user_autoreply: 
        return bot.send_message(uid, "❌ Reklama yoki Avto-Javob sozlanmagan!")

    stop_flags[uid] = False
    status_msg = bot.send_message(uid, "📡 24/7 Tizim ishga tushmoqda...")
    asyncio.run_coroutine_threadsafe(run_broadcast(uid, status_msg), main_loop)

# ==========================================
# 📱 LOGIN VA BOSHQA HANDLERLAR
# ==========================================
async def async_contact_auth(uid, phone):
    cl = Client(f"session_{uid}", API_ID, API_HASH)
    await cl.connect()
    try:
        c = await cl.send_code(phone)
        active_clients[uid] = {"cl": cl, "phone": phone, "hash": c.phone_code_hash}
        bot.register_next_step_handler(bot.send_message(uid, "📩 Kodni yuboring:"), verify_telegram_code)
    except Exception as e:
        bot.send_message(uid, f"❌: {e}")

@bot.message_handler(content_types=['contact'])
def handle_contact_auth(m):
    uid, phone = m.from_user.id, m.contact.phone_number
    bot.send_message(uid, "⏳ Kod so'ralmoqda...")
    asyncio.run_coroutine_threadsafe(async_contact_auth(uid, phone), main_loop)
    async def async_verify_code(uid, code, msg):
    try:
        d = active_clients[uid]
        await d["cl"].sign_in(d["phone"], d["hash"], code)
        bot.send_message(uid, "✅ Ulandi!", reply_markup=get_main_keyboard(uid))
    except errors.SessionPasswordNeeded:
        bot.register_next_step_handler(bot.send_message(uid, "🔐 2FA parolni yozing:"), verify_2fa)
    except Exception as e:
        bot.send_message(uid, f"❌: {e}")

def verify_telegram_code(m):
    uid, code = m.from_user.id, m.text.replace(" ", "")
    asyncio.run_coroutine_threadsafe(async_verify_code(uid, code, m), main_loop)

async def async_verify_2fa(uid, password_text):
    try:
        await active_clients[uid]["cl"].check_password(password_text)
        bot.send_message(uid, "✅ Ulandi!", reply_markup=get_main_keyboard(uid))
    except Exception:
        bot.send_message(uid, "❌ Parol xato.")

def verify_2fa(m):
    uid = m.from_user.id
    asyncio.run_coroutine_threadsafe(async_verify_2fa(uid, m.text), main_loop)

@bot.message_handler(func=lambda m: m.text == "🛑 To'xtatish")
def stop_process(m):
    stop_flags[m.from_user.id] = True
    bot.send_message(m.chat.id, "🛑 To'xtatildi.")

@bot.message_handler(func=lambda m: m.text == "🖼 Reklamani Sozlash")
def setup_ad_photo(m):
    msg = bot.send_message(m.chat.id, "📸 Rasm va matn yuboring:")
    bot.register_next_step_handler(msg, process_user_ad_content)

def process_user_ad_content(m):
    if m.photo:
        user_ads[m.from_user.id] = {"type": "photo", "file_id": m.photo[-1].file_id, "caption": m.caption or ""}
    elif m.text:
        user_ads[m.from_user.id] = {"type": "text", "text": m.text}
    bot.send_message(m.chat.id, "✅ Saqlandi.")

@bot.message_handler(func=lambda m: m.text == "🔄 Forward Sozlash")
def setup_forward(m):
    msg = bot.send_message(m.chat.id, "🔄 Forward yuboring:")
    bot.register_next_step_handler(msg, process_forward_save)

def process_forward_save(m):
    if m.forward_from_chat:
        user_ads[m.from_user.id] = {"type": "forward", "from_chat_id": m.forward_from_chat.id, "message_id": m.forward_from_message_id}
        bot.send_message(m.chat.id, "✅ Forward saqlandi.")

@bot.message_handler(func=lambda m: m.text == "⏱ Interval")
def interval_menu(m):
    kb = types.InlineKeyboardMarkup(row_width=3)
    opts = [1, 3, 5, 10, 30, 60] if is_pro(m.from_user.id) else [10, 30, 60]
    kb.add(*[types.InlineKeyboardButton(f"{x}s", callback_data=f"setint_{x}") for x in opts])
    bot.send_message(m.chat.id, "⏱ Interval vaqtini tanlang:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("setint_"))
def set_int(call):
    user_intervals[call.from_user.id] = int(call.data.split("_")[1])
    bot.answer_callback_query(call.id, "✅ Saqlandi")

@bot.message_handler(func=lambda m: m.text == "📊 Statistika")
def show_user_stats(m):
    sessions_count = len([f for f in os.listdir() if f.endswith('.session')])
    bot.send_message(
        m.chat.id, 
        f"📊 Bot Statistikasi:\n\n"
        f"👤 Foydalanuvchilar: {len(db['users'])}\n"
        f"📱 Ulangan akkauntlar: {sessions_count}\n"
        f"📨 Jami tarqatilgan xabarlar: {db.get('total_messages', 0)}"
    )

if name == "main":
    bot.infinity_polling()
