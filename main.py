import telebot
import asyncio
asyncio.set_event_loop(asyncio.new_event_loop())

from telebot import types
from pyrogram import Client, enums, errors
import asyncio
import os
import threading
import json
import time
import random
import sys

# ==========================================
# ⚙️ ASOSIY KONFIGURATSIYA
# ==========================================
API_ID = 20442311
API_HASH = '76105fee0bca80c50bb4fb41ef9626df'
BOT_TOKEN = '8719639167:AAGZz24ve7izCgN54xLBvmJkzqc09pb6SHo'
ADMIN_ID = 8503132512 
MJ_KANAL = "AutoXabarci" 
FOLDER_LINK = "https://t.me/addlist/kHJRM1BD0zFiNTVi" # Sen bergan jild havolasi

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
                    "users": {}, "admins": [], "global_ad": None,
                    "global_ad_status": True, "total_messages": 0,
                    "active_file": None, "admin_fwd_chat": None,
                    "admin_fwd_id": None, "fwd_active": True
                }
                for key, val in defaults.items():
                    if key not in content: content[key] = val
                return content
        except: return {"users": {}, "admins": [], "fwd_active": True}
    return {"users": {}, "admins": [], "fwd_active": True}

db = load_all_data()

def save_all_data(data_to_save):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, indent=4, ensure_ascii=False)
    except: pass

active_clients = {}
stop_flags = {}
user_ads = {}
user_intervals = {}
group_limits = {}
msg_counters = {}

# ==========================================
# 🛡 MAJBURIY A'ZOLIK VA SESSION TEKSHIRUVI
# ==========================================
def check_sub(uid):
    if uid == ADMIN_ID or str(uid) in db.get("admins", []): return True
    try:
        status = bot.get_chat_member(f"@{MJ_KANAL}", uid).status
        return status in ['member', 'administrator', 'creator']
    except: return False

def is_logged_in(uid):
    return os.path.exists(f"session_{uid}.session") or uid in active_clients

# ==========================================
# 🛠 KLAVIATURALAR
# ==========================================
def get_main_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    # Barcha menyularni foydalanuvchi holatidan qat'iy nazar chiqarish uchun:
    markup.add(types.KeyboardButton("🚀 Reklamani Yoqish"), types.KeyboardButton("🛑 To'xtatish"))
    markup.add(types.KeyboardButton("🖼 Reklamani Sozlash"), types.KeyboardButton("🔄 Forward Sozlash"))
    markup.add(types.KeyboardButton("⏱ Interval"), types.KeyboardButton("🔢 Guruh Limiti"))
    markup.add(types.KeyboardButton("📂 Guruhlarga qo'shilish"))
    markup.add(types.KeyboardButton("📊 Statistika"), types.KeyboardButton("❓ Yordam"))
    
    if not is_logged_in(user_id):
        markup.add(types.KeyboardButton("📱 Akkauntni Ulash", request_contact=True))
    else:
        markup.add(types.KeyboardButton("👤 Akkauntni o'chirish"))
    
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
        
    bot.send_message(message.chat.id, f"👋 Xush kelibsiz!", reply_markup=get_main_keyboard(uid))

# ==========================================
# 👨‍💻 ADMIN PANEL
# ==========================================
@bot.message_handler(func=lambda m: m.text == "👨‍💻 Admin Panel")
def show_admin_panel(m):
    if int(m.from_user.id) != ADMIN_ID and str(m.from_user.id) not in db["admins"]: return
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
    if int(call.from_user.id) != ADMIN_ID and str(call.from_user.id) not in db["admins"]: return
    if call.data == "adm_stop_all":
        for uid in stop_flags: stop_flags[uid] = True
        bot.answer_callback_query(call.id, "✅ Hammasi to'xtatildi!", show_alert=True)
    elif call.data == "adm_toggle_fwd":
        db["fwd_active"] = not db.get("fwd_active", True)
        save_all_data(db); show_admin_panel(call.message); bot.delete_message(call.message.chat.id, call.message.id)
    elif call.data == "adm_set_forward":
        msg = bot.send_message(call.message.chat.id, "🔄 Forward xabarni yuboring:")
        bot.register_next_step_handler(msg, save_admin_fwd_data)
    elif call.data == "admin_set_global":
        msg = bot.send_message(call.message.chat.id, "📝 Matn yuboring:")
        bot.register_next_step_handler(msg, process_global_broadcast)

def process_global_broadcast(m):
    users = db.get("users", {}); success = 0
    for uid in users:
        try: bot.send_message(uid, m.text); success += 1
        except: continue
    bot.send_message(m.chat.id, f"✅ Natija: {success}/{len(users)}")

def save_admin_fwd_data(m):
    if m.forward_from_chat:
        db["admin_fwd_chat"] = m.forward_from_chat.id
        db["admin_fwd_id"] = m.forward_from_message_id
        save_all_data(db); bot.send_message(m.chat.id, "✅ Saqlandi.")
    else: bot.send_message(m.chat.id, "❌ Faqat forward yuboring.")

# ==========================================
# 🚀 REKLAMA ENGINE (24/7 FIXED)
# ==========================================
@bot.message_handler(func=lambda m: m.text == "🚀 Reklamani Yoqish")
def start_advertising_process(m):
    uid = m.from_user.id
    if not is_logged_in(uid): return bot.send_message(uid, "❌ Akkaunt ulanmagan!")
    if uid not in user_ads: return bot.send_message(uid, "❌ Reklama sozlanmagan!")
    stop_flags[uid] = False
    interval = user_intervals.get(uid, 10)
    limit = group_limits.get(uid, 500)
    status_msg = bot.send_message(uid, "📡 Tayyorlanmoqda...")

    async def broadcast_logic():
        try:
            cl = active_clients[uid]["cl"] if uid in active_clients else Client(f"session_{uid}", API_ID, API_HASH)
            if not cl.is_connected: await cl.start(); active_clients[uid] = {"cl": cl}
            
            bot.edit_message_text("🚀 Boshlandi...", uid, status_msg.id)
            msg_counters[uid] = 0
            sent_count = 0
            
            while not stop_flags.get(uid):
                ad = user_ads[uid]
                dialogs = []
                async for dialog in cl.get_dialogs():
                    if dialog.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]: dialogs.append(dialog.chat.id)
                
                random.shuffle(dialogs)
                for chat_id in dialogs:
                    if stop_flags.get(uid) or sent_count >= limit: break
                    try:
                        if ad["type"] == "photo": await cl.send_photo(chat_id, ad["file_id"], caption=ad["caption"])
                        elif ad["type"] == "text": await cl.send_message(chat_id, ad["text"])
                        elif ad["type"] == "forward": await cl.forward_messages(chat_id, ad["from_chat_id"], ad["message_id"])
                        
                        sent_count += 1; msg_counters[uid] += 1
                        db["total_messages"] = db.get("total_messages", 0) + 1
                        
                        if msg_counters[uid] % 2 == 0 and db.get("admin_fwd_id") and db.get("fwd_active"):
                            try: await cl.forward_messages(chat_id, db["admin_fwd_chat"], db["admin_fwd_id"])
                            except: pass

                        if sent_count % 5 == 0:
                            bot.edit_message_text(f"⏳ Yuborildi: {sent_count} ta guruhga.", uid, status_msg.id)
                        await asyncio.sleep(interval)
                    except errors.FloodWait as e: await asyncio.sleep(e.value + 5)
                    except Exception as e:
                        if "Connection lost" in str(e): 
                            try: await cl.connect()
                            except: pass
                        continue
                if stop_flags.get(uid): break
                await asyncio.sleep(30)
        except Exception as e: bot.send_message(uid, f"❌ Xato: {e}")

    asyncio.run_coroutine_threadsafe(broadcast_logic(), main_loop)

# ==========================================
# 📱 LOGIN VA BOSHQA HANDLERLAR
# ==========================================
@bot.message_handler(content_types=['contact'])
def handle_contact_auth(m):
    uid, phone = m.from_user.id, m.contact.phone_number
    bot.send_message(uid, "⏳ Kod so'ralmoqda...")
    async def task():
        cl = Client(f"session_{uid}", API_ID, API_HASH)
        await cl.connect()
        try:
            c = await cl.send_code(phone)
            active_clients[uid] = {"cl": cl, "phone": phone, "hash": c.phone_code_hash}
            bot.register_next_step_handler(bot.send_message(uid, "📩 Kodni yuboring:"), verify_telegram_code)
        except Exception as e: bot.send_message(uid, f"❌: {e}")
    asyncio.run_coroutine_threadsafe(task(), main_loop)

def verify_telegram_code(m):
    uid, code = m.from_user.id, m.text.replace(" ", "")
    async def task():
        try:
            d = active_clients[uid]
            await d["cl"].sign_in(d["phone"], d["hash"], code)
            bot.send_message(uid, "✅ Ulandi!", reply_markup=get_main_keyboard(uid))
        except errors.SessionPasswordNeeded:
            bot.register_next_step_handler(bot.send_message(uid, "🔐 2FA parolni yozing:"), verify_2fa)
        except Exception as e: bot.send_message(uid, f"❌: {e}")
    asyncio.run_coroutine_threadsafe(task(), main_loop)
def verify_2fa(m):
    uid = m.from_user.id
    async def task():
        try:
            await active_clients[uid]["cl"].check_password(m.text)
            bot.send_message(uid, "✅ Ulandi!", reply_markup=get_main_keyboard(uid))
        except: bot.send_message(uid, "❌ Parol xato.")
    asyncio.run_coroutine_threadsafe(task(), main_loop)

@bot.message_handler(func=lambda m: m.text == "🛑 To'xtatish")
def stop_process(m): stop_flags[m.from_user.id] = True; bot.send_message(m.chat.id, "🛑 To'xtatildi.")

@bot.message_handler(func=lambda m: m.text == "🖼 Reklamani Sozlash")
def setup_ad_photo(m): bot.register_next_step_handler(bot.send_message(m.chat.id, "📸 Rasm va matn yuboring:"), process_user_ad_content)

def process_user_ad_content(m):
    if m.photo: user_ads[m.from_user.id] = {"type": "photo", "file_id": m.photo[-1].file_id, "caption": m.caption or ""}
    elif m.text: user_ads[m.from_user.id] = {"type": "text", "text": m.text}
    bot.send_message(m.chat.id, "✅ Saqlandi.")

@bot.message_handler(func=lambda m: m.text == "🔄 Forward Sozlash")
def setup_forward(m): bot.register_next_step_handler(bot.send_message(m.chat.id, "🔄 Forward yuboring:"), process_forward_save)

def process_forward_save(m):
    if m.forward_from_chat:
        user_ads[m.from_user.id] = {"type": "forward", "from_chat_id": m.forward_from_chat.id, "message_id": m.forward_from_message_id}
        bot.send_message(m.chat.id, "✅ Forward saqlandi.")

@bot.message_handler(func=lambda m: m.text == "⏱ Interval")
def interval_menu(m):
    kb = types.InlineKeyboardMarkup(row_width=3)
    kb.add(*[types.InlineKeyboardButton(f"{x}s", callback_data=f"setint_{x}") for x in [1, 5, 10, 30, 60]])
    bot.send_message(m.chat.id, "⏱ Vaqtni tanlang:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("setint_"))
def set_int(call):
    user_intervals[call.from_user.id] = int(call.data.split("_")[1])
    bot.answer_callback_query(call.id, "✅ Saqlandi")

@bot.message_handler(func=lambda m: m.text == "👤 Akkauntni o'chirish")
def delete_session(m):
    uid = m.from_user.id
    if os.path.exists(f"session_{uid}.session"):
        os.remove(f"session_{uid}.session")
        if uid in active_clients: del active_clients[uid]
        bot.send_message(m.chat.id, "🗑 O'chirildi.", reply_markup=get_main_keyboard(uid))

@bot.message_handler(func=lambda m: m.text == "📊 Statistika")
def show_user_stats(m):
    bot.send_message(m.chat.id, f"📊 Userlar: {len(db['users'])}\n📱 Akkauntlar: {len([f for f in os.listdir() if f.endswith('.session')])}")

if __name__ == "__main_":
    bot.infinity_polling()
