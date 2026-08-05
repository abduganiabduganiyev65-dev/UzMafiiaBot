import asyncio
import logging
import sqlite3
import time
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

# --- ASOSIY SOZLAMALAR ---
BOT_TOKEN = "8902585083:AAE0reQEDoaolOyhySA1kwi0K27SA9PZxWU"
ADMIN_ID = 8661312143
CARD_NUMBER = "9860 1466 4986 4312"
CARD_NAME = "N.X"
BOT_USERNAME = "@AutoXabarchiNewBot"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- MA'LUMOTLAR BAZASI ---
def init_db():
    conn = sqlite3.connect("autoxabar.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            is_vip INTEGER DEFAULT 0,
            interval_sec REAL DEFAULT 300.0,
            auto_status INTEGER DEFAULT 0,
            msg_text TEXT DEFAULT 'Salom! Bu avto-xabar.',
            groups TEXT DEFAULT '',
            autoreply_status INTEGER DEFAULT 0,
            autoreply_text TEXT DEFAULT 'Salom! Hozir bandman, tez orada javob beraman.',
            total_sent INTEGER DEFAULT 0,
            last_sent_time REAL DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_user(user_id):
    conn = sqlite3.connect("autoxabar.db")
    cursor = conn.cursor()
    cursor.execute("SELECT is_vip, interval_sec, auto_status, msg_text, groups, autoreply_status, autoreply_text, total_sent FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    if not res:
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        res = (0, 300.0, 0, 'Salom! Bu avto-xabar.', '', 0, 'Salom! Hozir bandman, tez orada javob beraman.', 0)
    conn.close()
    return {
        "is_vip": res[0],
        "interval": res[1],
        "status": res[2],
        "text": res[3],
        "groups": [g.strip() for g in res[4].split(",") if g.strip()],
        "autoreply_status": res[5],
        "autoreply_text": res[6],
        "total_sent": res[7]
    }

def update_user(user_id, **kwargs):
    conn = sqlite3.connect("autoxabar.db")
    cursor = conn.cursor()
    for key, val in kwargs.items():
        cursor.execute(f"UPDATE users SET {key} = ? WHERE user_id = ?", (val, user_id))
    conn.commit()
    conn.close()

# --- FSM HOLATLAR ---
class Form(StatesGroup):
    waiting_for_text = State()
    waiting_for_interval = State()
    waiting_for_groups = State()
    waiting_for_receipt = State()
    waiting_for_autoreply = State()

# --- TUGMALAR ---
def main_keyboard():
    kb = [
        [KeyboardButton(text="⚡️ Boshqaruv paneli")],
        [KeyboardButton(text="👤 Profillar"), KeyboardButton(text="👑 Pro tarif")],
        [KeyboardButton(text="👤 Kabinet"), KeyboardButton(text="⚙️ Sozlamalar")],
        [KeyboardButton(text="🗓 Kalendar"), KeyboardButton(text="🔧 Foydali funksiyalar")],
        [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="❓ Yordam")],
        [KeyboardButton(text="📖 Qo'llanma")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def control_panel_inline(user_id):
    u = get_user(user_id)
    status_btn = "⏸ To'xtatish" if u["status"] else "▶️ Ishga tushirish"
    kb = [
        [InlineKeyboardButton(text=f"🔮 Autohabar: {status_btn}", callback_data="toggle_auto"),
         InlineKeyboardButton(text="💬 Habar matni", callback_data="set_text")],
        [InlineKeyboardButton(text="⏱ Interval", callback_data="set_interval"),
         InlineKeyboardButton(text="👥 Guruhlarni sozlash", callback_data="set_groups")],
        [InlineKeyboardButton(text="🔄 Autoreply", callback_data="set_autoreply")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)
    # --- START XABARI ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    u = get_user(message.from_user.id)
    vip_str = "💎 Pro (VIP)" if u["is_vip"] else "💙 Bepul"
    status_str = "🟢 Yoqilgan" if u["status"] else "❌ O'chiq"
    
    text = (
        f"🤖 Avtorassylka / Auto-Broadcaster Botiga Xush Kelibsiz!\n\n"
        f"🌌 Auto Habar: {status_str}\n"
        f"⭐️ Sizning Tarifingiz: {vip_str}\n"
        f"⏱ Interval: {u['interval']} soniya\n"
        f"👥 Ulangan guruhlar: {len(u['groups'])} ta\n\n"
        f"👇 *Kerakli tugmani pastdan tanlang:*"
    )
    await message.answer(text, reply_markup=main_keyboard(), parse_mode="Markdown")

# --- BOSHQARUV PANEL ---
@dp.message(F.text == "⚡️ Boshqaruv paneli")
async def control_panel_msg(message: types.Message):
    u = get_user(message.from_user.id)
    vip_str = "💎 Pro (VIP)" if u["is_vip"] else "💙 Bepul"
    status_str = "🟢 Yoqilgan" if u["status"] else "❌ O'chiq"
    
    text = (
        f"⚙️ Boshqaruv Paneli\n\n"
        f"📡 Ulangan status: Active\n"
        f"🌌 Auto Habar: {status_str}\n"
        f"⭐️ Sizning Tarifingiz: {vip_str}\n"
        f"⏱ Interval: {u['interval']} soniya\n"
        f"💬 Joriy matn: {u['text']}\n"
        f"👥 Guruhlar soni: {len(u['groups'])} ta"
    )
    await message.answer(text, reply_markup=control_panel_inline(message.from_user.id), parse_mode="Markdown")

# --- TOGGLE AUTO SEND ---
@dp.callback_query(F.data == "toggle_auto")
async def toggle_auto_send(call: types.CallbackQuery):
    u = get_user(call.from_user.id)
    if not u["groups"]:
        await call.answer("⚠️ Avval guruhlarni kiriting!", show_alert=True)
        return
    
    new_status = 0 if u["status"] else 1
    update_user(call.from_user.id, auto_status=new_status)
    
    st_text = "yoqildi 🟢" if new_status else "o'chirildi ❌"
    await call.answer(f"Autohabar yuborish {st_text}", show_alert=True)
    await call.message.edit_reply_markup(reply_markup=control_panel_inline(call.from_user.id))

# --- SET TEXT ---
@dp.callback_query(F.data == "set_text")
async def ask_text(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("📝 Guruhlarga yuboriladigan yangi xabar matnini kiriting:")
    await state.set_state(Form.waiting_for_text)
    await call.answer()

@dp.message(Form.waiting_for_text)
async def save_text(message: types.Message, state: FSMContext):
    update_user(message.from_user.id, msg_text=message.text)
    await message.answer("✅ Xabar matni saqlandi!")
    await state.clear()

# --- SET INTERVAL ---
@dp.callback_query(F.data == "set_interval")
async def ask_interval(call: types.CallbackQuery, state: FSMContext):
    u = get_user(call.from_user.id)
    info = "💎 VIP tarif: minimal 0.1s\n💙 Bepul tarif: min 0.5s - max 300s (5 minut)" if u["is_vip"] else "💙 Bepul tarifdasiz (Min: 0.5s, Max: 300s).\n💎 PRO VIP olsangiz 0.1s interval ochiladi!"
    await call.message.answer(f"⏱ Yangi intervalni soniyalarda kiriting:\n\n{info}")
    await state.set_state(Form.waiting_for_interval)
    await call.answer()

@dp.message(Form.waiting_for_interval)
async def save_interval(message: types.Message, state: FSMContext):
    u = get_user(message.from_user.id)
    try:
        val = float(message.text)
        min_limit = 0.1 if u["is_vip"] else 0.5
        if val < min_limit:
            await message.answer(f"❌ Siz uchun minimal interval: {min_limit} soniya!")
            return
        if not u["is_vip"] and val > 300:
            await message.answer("❌ Bepul tarifda maksimal interval 300 soniya (5 minut)!")
            return
        update_user(message.from_user.id, interval_sec=val)
        await message.answer(f"✅ Interval {val} soniyaga o'zgartirildi.")
        await state.clear()
    except ValueError:
        await message.answer("⚠️ Faqat raqam kiriting (masalan: 10 yoki 0.5).")
        # --- SET GROUPS ---
@dp.callback_query(F.data == "set_groups")
async def ask_groups(call: types.CallbackQuery, state: FSMContext):
    u = get_user(call.from_user.id)
    current_groups = "\n".join(u["groups"]) if u["groups"] else "Hozircha guruhlar yo'q."
    await call.message.answer(
        f"👥 Joriy guruhlar:\n{current_groups}\n\n"
        f"➕ Yangi guruh ID yoki linklarini vergul bilan ajratib kiriting:\n"
        f"*(Masalan: @guruh1, -100123456789, @guruh2)*\n\n"
        f"⚠️ Muhim: Bot ushbu guruhlarda a'zo bo'lishi va xabar yozish huquqiga ega bo'lishi kerak!",
        parse_mode="Markdown"
    )
    await state.set_state(Form.waiting_for_groups)
    await call.answer()

@dp.message(Form.waiting_for_groups)
async def save_groups(message: types.Message, state: FSMContext):
    update_user(message.from_user.id, groups=message.text)
    await message.answer("✅ Guruhlar ro'yxati yangilandi!")
    await state.clear()

# --- AUTOREPLY SETTINGS ---
@dp.callback_query(F.data == "set_autoreply")
async def autoreply_menu(call: types.CallbackQuery, state: FSMContext):
    u = get_user(call.from_user.id)
    st = "🟢 Yoqilgan" if u["autoreply_status"] else "❌ O'chiq"
    await call.message.answer(f"🔄 Autoreply sozlamalari\nStatus: {st}\nJoriy javob matni: {u['autoreply_text']}\n\nYangi Avto-javob matnini kiriting:")
    await state.set_state(Form.waiting_for_autoreply)
    await call.answer()

@dp.message(Form.waiting_for_autoreply)
async def save_autoreply(message: types.Message, state: FSMContext):
    update_user(message.from_user.id, autoreply_text=message.text, autoreply_status=1)
    await message.answer("✅ Autoreply matni saqlandi va yoqildi!")
    await state.clear()

# --- PRO TARIF (VIP SOTIB OLISH) ---
@dp.message(F.text == "👑 Pro tarif")
async def pro_tariff_msg(message: types.Message):
    u = get_user(message.from_user.id)
    vip_status = "✅ Siz allaqachon VIP foydalanuvchisiz!" if u["is_vip"] else "❌ Bepul tarifdasiz"
    
    text = (
        f"👑 PRO TARIF (VIP STATUS)\n\n"
        f"Sizning statusingiz: {vip_status}\n\n"
        f"🚀 VIP Avzalliklari:\n"
        f"• ⚡️ 0.1 soniya minimal interval\n"
        f"• 🔕 Xabar ostidagi {BOT_USERNAME} reklamasi yoʻqotiladi!\n"
        f"• ♾ Cheksiz guruhlarga avto-yuborish\n"
        f"• 📈 Yuqori tezlik va prioriteti bor server\n\n"
        f"💳 To'lov uchun karta: {CARD_NUMBER}\n"
        f"👤 Egasining ismi: {CARD_NAME}\n"
        f"💵 Narxi: 35,000 so'm / oyiga\n\n"
        f"To'lovni amalga oshirgach, chek rasmini yuborish uchun pastdagi tugmani bosing:"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Chekni yuborish", callback_data="send_receipt")]
    ])
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data == "send_receipt")
async def ask_receipt(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("📸 Iltimos, to'lov chekining rasmini (skrinshotini) yuboring:")
    await state.set_state(Form.waiting_for_receipt)
    await call.answer()

@dp.message(Form.waiting_for_receipt, F.photo)
async def receive_receipt(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    user_id = message.from_user.id
    username = f"@{message.from_user.username}" if message.from_user.username else f"ID: {user_id}"
    
    # Adminga yuborish
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ VIP Berish", callback_data=f"grant_vip:{user_id}"),
         InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_vip:{user_id}")]
    ])
    
    await bot.send_photo(
        chat_id=ADMIN_ID,
        photo=photo_id,
        caption=f"💳 Yangi to'lov cheki keldi!\nFoydalanuvchi: {username}\nID: {user_id}",
        reply_markup=admin_kb,
        parse_mode="Markdown"
    )
    
    await message.answer("✅ Chek admin tekshiruviga yuborildi! VIP status tasdiqlangach sizga xabar beriladi.")
    await state.clear()
    # --- ADMIN VERIFICATION HANDLER ---
@dp.callback_query(F.data.startswith("grant_vip:"))
async def grant_vip_callback(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return
    target_user_id = int(call.data.split(":")[1])
    update_user(target_user_id, is_vip=1)
    
    await call.message.edit_caption(caption=call.message.caption + "\n\n✅ VIP STATUS BERILDI!")
    try:
        await bot.send_message(target_user_id, "🎉 Tabriklaymiz! Sizga VIP Status berildi.\nEndi xabarlaringiz tagida reklama chiqmaydi va 0.1s interval qo'yishingiz mumkin!")
    except Exception:
        pass
    await call.answer("VIP berildi!")

@dp.callback_query(F.data.startswith("reject_vip:"))
async def reject_vip_callback(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return
    target_user_id = int(call.data.split(":")[1])
    await call.message.edit_caption(caption=call.message.caption + "\n\n❌ TO'LOV RAD ETILDI.")
    try:
        await bot.send_message(target_user_id, "❌ Siz yuborgan to'lov cheki admin tomonidan rad etildi.")
    except Exception:
        pass
    await call.answer("Rad etildi!")

# --- BOSHQA MENYU TUGMALARI ---
@dp.message(F.text == "👤 Profillar")
@dp.message(F.text == "👤 Kabinet")
async def profile_msg(message: types.Message):
    u = get_user(message.from_user.id)
    vip_str = "💎 Pro (VIP)" if u["is_vip"] else "💙 Bepul"
    text = (
        f"👤 Foydalanuvchi Kabineti\n\n"
        f"🆔 ID: {message.from_user.id}\n"
        f"👤 Ism: {message.from_user.full_name}\n"
        f"⭐️ Tarif: {vip_str}\n"
        f"📊 Jami yuborilgan xabarlar: {u['total_sent']} ta\n"
        f"⏱ Interval: {u['interval']}s"
    )
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "⚙️ Sozlamalar")
async def settings_msg(message: types.Message):
    await control_panel_msg(message)

@dp.message(F.text == "🗓 Kalendar")
async def calendar_msg(message: types.Message):
    await message.answer("🗓 Kalendar Rejalashtirgich:\nAvto-rasilka 24/7 rejimida uzluksiz ishlaydi. Alohida vaqt jadvalini belgilash VIP foydalanuvchilar uchun avtomatik faol.")

@dp.message(F.text == "🔧 Foydali funksiyalar")
async def tools_msg(message: types.Message):
    await message.answer("🔧 Foydali funksiyalar:\n• Avto-javob beruvchi (Autoreply)\n• Multi-guruh yuborish\n• Anti-Flood Wait himoyasi")

@dp.message(F.text == "📊 Statistika")
async def stats_msg(message: types.Message):
    u = get_user(message.from_user.id)
    await message.answer(f"📊 Statistika:\nSizning jami yuborgan xabarlaringiz: {u['total_sent']} ta\nUlangan guruhlar: {len(u['groups'])} ta")

@dp.message(F.text == "❓ Yordam")
@dp.message(F.text == "📖 Qo'llanma")
async def help_msg(message: types.Message):
    text = (
        f"📖 Botdan foydalanish qo'llanmasi:\n\n"
        f"1. Botni xabar yubormoqchi bo'lgan guruhlaringizga qo'shing va adminga aylantiring (yoki yozish huquqini bering).\n"
        f"2. ⚡️ Boshqaruv paneli -> 👥 Guruhlarni sozlash bo'limiga kirib guruh linki yoki ID sini kiriting.\n"
        f"3. 💬 Habar matni tugmasi orqali reklamangizni kiriting.\n"
        f"4. 🔮 Autohabar yuborish tugmasini bosib botni ishga tushiring.\n\n"
        f"👨‍💻 Admin: @id{ADMIN_ID}"
    )
    await message.answer(text, parse_mode="Markdown")

# --- AVTO XABAR YUBORISH SYSTEM (BACKGROUND ENGINE) ---
async def auto_broadcaster_loop():
    while True:
        await asyncio.sleep(1)
        conn = sqlite3.connect("autoxabar.db")
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, is_vip, interval_sec, msg_text, groups, total_sent, last_sent_time FROM users WHERE auto_status = 1")
        active_users = cursor.fetchall()
        conn.close()

        now = time.time()
        for u_id, is_vip, interval, msg_text, groups_str, total_sent, last_sent in active_users:
            if now - last_sent >= interval:
                groups = [g.strip() for g in groups_str.split(",") if g.strip()]
                if not groups:
                    continue
                
                # --- REKLAMA SUFFIX (VIP uchun yo'qotiladi) ---
                if is_vip:
                    final_text = msg_text
                else:
                    final_text = f"{msg_text}\n\n📢 {BOT_USERNAME} orqali yuborildi"
                
                sent_count = 0
                for group in groups:
                    try:
                        await bot.send_message(chat_id=group, text=final_text)
                        sent_count += 1
                        await asyncio.sleep(0.05)
                    except Exception as e:
                        logging.error(f"Guruhga yuborishda xatolik ({group}): {e}")
                
                update_user(u_id, last_sent_time=now, total_sent=total_sent + sent_count)

# --- BOTNI ISHGA TUSHIRISH ---
async def main():
    asyncio.create_task(auto_broadcaster_loop())
    await dp.start_polling(bot)

if name == "main":
    asyncio.run(main())
