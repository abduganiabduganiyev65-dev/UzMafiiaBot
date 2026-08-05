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
ADMIN_USERNAME = "@vipcgm"
CHANNEL_USERNAME = "@AutoXabarchiNew"
CHANNEL_URL = "https://t.me/AutoXabarchiNew"
BOT_USERNAME = "@AutoXabarchiNewBot"
CARD_NUMBER = "9860 1466 4986 4312"
CARD_NAME = "N.X"

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
            msg_photo TEXT DEFAULT NULL,
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
    cursor.execute("SELECT is_vip, interval_sec, auto_status, msg_text, msg_photo, groups, autoreply_status, autoreply_text, total_sent FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    if not res:
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        res = (0, 300.0, 0, 'Salom! Bu avto-xabar.', None, '', 0, 'Salom! Hozir bandman, tez orada javob beraman.', 0)
    conn.close()
    return {
        "is_vip": res[0],
        "interval": res[1],
        "status": res[2],
        "text": res[3],
        "photo": res[4],
        "groups": [g.strip() for g in res[5].split(",") if g.strip()],
        "autoreply_status": res[6],
        "autoreply_text": res[7],
        "total_sent": res[8]
    }

def update_user(user_id, **kwargs):
    conn = sqlite3.connect("autoxabar.db")
    cursor = conn.cursor()
    for key, val in kwargs.items():
        cursor.execute(f"UPDATE users SET {key} = ? WHERE user_id = ?", (val, user_id))
    conn.commit()
    conn.close()

# --- MAJBURIY OBUNANI TEKSHIRISH ---
async def check_sub(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if member.status in ["member", "administrator", "creator"]:
            return True
    except Exception:
        pass
    return False

def sub_keyboard():
    kb = [
        [InlineKeyboardButton(text="📢 Kanalga obuna bo'lish", url=CHANNEL_URL)],
        [InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_subscription")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- FSM HOLATLAR ---
class Form(StatesGroup):
    waiting_for_text = State()
    waiting_for_interval = State()
    waiting_for_groups = State()
    waiting_for_receipt = State()
    waiting_for_autoreply = State()

# --- ASOSIY TUGMALAR ---
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

# --- START & OBUNA TEKSHIRUV ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    if not await check_sub(message.from_user.id):
        await message.answer(
            f"⚠️ Botdan foydalanish uchun avval kanalimizga obuna bo'ling!\n\nKanal: {CHANNEL_URL}",
            reply_markup=sub_keyboard(),
            parse_mode="Markdown"
        )
        return

    u = get_user(message.from_user.id)
    vip_str = "💎 Pro (VIP)" if u["is_vip"] else "💙 Bepul"
    status_str = "🟢 Yoqilgan" if u["status"] else "❌ O'chiq"
    
    text = (
        f"🤖 Avtorassylka Botiga Xush Kelibsiz!\n\n"
        f"🌌 Auto Habar: {status_str}\n"
        f"⭐️ Sizning Tarifingiz: {vip_str}\n"
        f"⏱ Interval: {u['interval']} soniya\n"
        f"👥 Ulangan guruhlar: {len(u['groups'])} ta\n\n"
        f"👇 *Kerakli tugmani pastdan tanlang:*"
    )
    await message.answer(text, reply_markup=main_keyboard(), parse_mode="Markdown")

@dp.callback_query(F.data == "check_subscription")
async def check_sub_cb(call: types.CallbackQuery):
    if await check_sub(call.from_user.id):
        await call.message.delete()
        await call.message.answer("✅ Obuna tasdiqlandi! Endi botdan to'liq foydalanishingiz mumkin /start")
    else:
        await call.answer("❌ Siz hali kanalga obuna bo'lmadingiz!", show_alert=True)

# --- BOSHQARUV PANEL ---
@dp.message(F.text == "⚡️ Boshqaruv paneli")
async def control_panel_msg(message: types.Message):
    if not await check_sub(message.from_user.id):
        await message.answer(f"⚠️ Avval kanalimizga obuna bo'ling: {CHANNEL_URL}", reply_markup=sub_keyboard())
        return
    
    u = get_user(message.from_user.id)
    vip_str = "💎 Pro (VIP)" if u["is_vip"] else "💙 Bepul"
    status_str = "🟢 Yoqilgan" if u["status"] else "❌ O'chiq"
    
    text = (
        f"⚙️ Boshqaruv Paneli\n\n"
        f"📡 Ulangan status: Active\n"
        f"🌌 Auto Habar: {status_str}\n"
        f"⭐️ Sizning Tarifingiz: {vip_str}\n"
        f"⏱ Interval: {u['interval']} soniya\n"
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

# --- SET TEXT & PHOTO ---
@dp.callback_query(F.data == "set_text")
async def ask_text(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("📝 Guruhlarga yuboriladigan xabarni yuboring:\n*(Matn yoki Rasm + matn ko'rinishida yuborishingiz mumkin)*")
    await state.set_state(Form.waiting_for_text)
    await call.answer()

@dp.message(Form.waiting_for_text, F.photo)
async def save_photo_text(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    caption = message.caption if message.caption else ""
    update_user(message.from_user.id, msg_text=caption, msg_photo=photo_id)
    await message.answer("✅ Rasm va matn muvaffaqiyatli saqlandi!")
    await state.clear()

@dp.message(Form.waiting_for_text, F.text)
async def save_only_text(message: types.Message, state: FSMContext):
    update_user(message.from_user.id, msg_text=message.text, msg_photo=None)
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
        f"*(Masalan: -100123456789, @guruhname)*\n\n"
        f"⚠️ Bot guruhlarda admin bo'lishi shart!",
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
    await call.message.answer(f"🔄 Autoreply sozlamalari\nStatus: {st}\nJoriy javob: {u['autoreply_text']}\n\nYangi Avto-javob matnini kiriting:")
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
        f"• 🔕 Xabar ostidagi {BOT_USERNAME} reklamasi olib tashlanadi!\n"
        f"• ♾ Cheksiz guruhlarga avto-yuborish\n\n"
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
    
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ VIP Berish", callback_data=f"grant_vip:{user_id}"),
         InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_vip:{user_id}")]
    ])
    
    await bot.send_photo(
        chat_id=ADMIN_ID,
        photo=photo_id,
        caption=f"💳 Yangi to'lov cheki!\nFoydalanuvchi: {username}\nID: {user_id}",
        reply_markup=admin_kb,
        parse_mode="Markdown"
    )
    
    await message.answer("✅ Chek adminga yuborildi! Tasdiqlangach xabar keladi.")
    await state.clear()

@dp.callback_query(F.data.startswith("grant_vip:"))
async def grant_vip_callback(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return
    target_user_id = int(call.data.split(":")[1])
    update_user(target_user_id, is_vip=1)
    await call.message.edit_caption(caption=call.message.caption + "\n\n✅ VIP STATUS BERILDI!")
    try:
        await bot.send_message(target_user_id, "🎉 Tabriklaymiz! Sizga VIP Status berildi.")
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
        await bot.send_message(target_user_id, "❌ To'lov chekingiz rad etildi.")
    except Exception:
        pass
    await call.answer("Rad etildi!")

# --- BOSHQA MENYULAR ---
@dp.message(F.text.in_({"👤 Profillar", "👤 Kabinet"}))
async def profile_msg(message: types.Message):
    u = get_user(message.from_user.id)
    vip_str = "💎 Pro (VIP)" if u["is_vip"] else "💙 Bepul"
    text = (
        f"👤 Kabinet\n\n"
        f"🆔 ID: {message.from_user.id}\n"
        f"⭐️ Tarif: {vip_str}\n"
        f"📊 Jami yuborilgan: {u['total_sent']} ta"
    )
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "⚙️ Sozlamalar")
async def settings_msg(message: types.Message):
    await control_panel_msg(message)

@dp.message(F.text == "🗓 Kalendar")
async def calendar_msg(message: types.Message):
    await message.answer("🗓 Kalendar: Avto-rasilka 24/7 rejimida uzluksiz ishlaydi.")
    @dp.message(F.text == "🔧 Foydali funksiyalar")
async def tools_msg(message: types.Message):
    await message.answer("🔧 Funksiyalar: Autoreply va Multi-guruh yuborish faol.")

@dp.message(F.text == "📊 Statistika")
async def stats_msg(message: types.Message):
    u = get_user(message.from_user.id)
    await message.answer(f"📊 Statistika:\nYuborilganlar: {u['total_sent']} ta\nGuruhlar: {len(u['groups'])} ta")

@dp.message(F.text.in_({"❓ Yordam", "📖 Qo'llanma"}))
async def help_msg(message: types.Message):
    text = (
        f"📖 Qo'llanma:\n"
        f"1. Guruhlarga botni admin qiling.\n"
        f"2. Boshqaruv panelidan guruh va xabar matnini kiriting.\n"
        f"3. Autohabarni yoqing.\n\n"
        f"👨‍💻 Admin: {ADMIN_USERNAME}"
    )
    await message.answer(text, parse_mode="Markdown")

# --- AVTO XABAR YUBORISH LOOP ---
async def auto_broadcaster_loop():
    while True:
        await asyncio.sleep(1)
        conn = sqlite3.connect("autoxabar.db")
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, is_vip, interval_sec, msg_text, msg_photo, groups, total_sent, last_sent_time FROM users WHERE auto_status = 1")
        active_users = cursor.fetchall()
        conn.close()

        now = time.time()
        for u_id, is_vip, interval, msg_text, msg_photo, groups_str, total_sent, last_sent in active_users:
            if now - last_sent >= interval:
                groups = [g.strip() for g in groups_str.split(",") if g.strip()]
                if not groups:
                    continue
                
                # Reklama imzosi
                if is_vip:
                    final_text = msg_text
                else:
                    final_text = f"{msg_text}\n\n📢 {BOT_USERNAME} orqali yuborildi" if msg_text else f"📢 {BOT_USERNAME} orqali yuborildi"
                
                sent_count = 0
                for group in groups:
                    try:
                        if msg_photo:
                            await bot.send_photo(chat_id=group, photo=msg_photo, caption=final_text)
                        else:
                            await bot.send_message(chat_id=group, text=final_text)
                        sent_count += 1
                        await asyncio.sleep(0.05)
                    except Exception as e:
                        logging.error(f"Xatolik ({group}): {e}")
                
                update_user(u_id, last_sent_time=now, total_sent=total_sent + sent_count)

async def main():
    asyncio.create_task(auto_broadcaster_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
