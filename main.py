import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

# --- SOZLAMALAR ---
TOKEN = "8902585083:AAE0reQEDoaolOyhySA1kwi0K27SA9PZxWU"
ADMIN_ID = 8661312143
ADMIN_USERNAME = "@vipcgm"
REQUIRED_CHANNEL = "@AutoXabarchiNew"
BOT_USERNAME = "@AutoXabarchiNewBot"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- BAZA (Xotirada saqlash uchun) ---
USERS_DB = {}

def get_user(user_id: int):
    if user_id not in USERS_DB:
        USERS_DB[user_id] = {
            "is_vip": False,
            "auto_active": False,
            "interval": 300,  # Bepul uchun standart 5 daqiqa (300 sekund)
            "text": "Xabar matni kiritilmagan",
            "photo": None,
            "mode": "normal",  # normal yoki autoreply
            "groups": [-1001234567890]  # Namuna guruh IDsi
        }
    return USERS_DB[user_id]

# --- MAJBURIY OBUNANI TEKSHIRISH ---
async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=user_id)
        if member.status in ["member", "administrator", "creator"]:
            return True
    except TelegramBadRequest:
        pass
    except Exception as e:
        logging.error(f"Obunani tekshirish xatosi: {e}")
    return False

# --- 24/7 AVTO-RASILKA FON JARAYONI ---
async def background_scheduler():
    while True:
        try:
            for user_id, u in USERS_DB.items():
                if u["auto_active"] and u["groups"]:
                    msg_text = u["text"]
                    if not u["is_vip"]:
                        msg_text += f"\n\n{BOT_USERNAME} orqali habar yuborildi"
                    
                    for group_id in u["groups"]:
                        try:
                            if u["photo"]:
                                await bot.send_photo(chat_id=group_id, photo=u["photo"], caption=msg_text)
                            else:
                                await bot.send_message(chat_id=group_id, text=msg_text)
                        except Exception as e:
                            logging.error(f"Guruhga xabar yuborishda xato ({group_id}): {e}")
                    
                    # Intervalni qo'llash
                    await asyncio.sleep(u["interval"])
            await asyncio.sleep(1)
        except Exception as e:
            logging.error(f"Scheduler xatosi: {e}")
            await asyncio.sleep(5)

# --- ASOSIY MENYU TUGMALARI (KLAVIATURA) ---
def get_main_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="👤 Profillar"), types.KeyboardButton(text="👑 Pro tarif"))
    builder.row(types.KeyboardButton(text="👤 Kabinet"), types.KeyboardButton(text="⚙️ Sozlamalar"))
    builder.row(types.KeyboardButton(text="🗓 Kalendar"), types.KeyboardButton(text="🔧 Foydali funksiyalar"))
    builder.row(types.KeyboardButton(text="📊 Statistika"), types.KeyboardButton(text="❓ Yordam"))
    builder.row(types.KeyboardButton(text="📖 Qo'llanma"))
    return builder.as_markup(resize_keyboard=True)

# --- BOSHQARUV PANELI (INLINE) ---
def get_control_panel_markup(u):
    builder = InlineKeyboardBuilder()
    auto_status = "🟢 Yoqiq" if u["auto_active"] else "❌ O'chiq"
    mode_str = "🔄 Autoreply" if u["mode"] == "autoreply" else "💬 Oddiy xabar"
    
    builder.button(text=f"📢 Autohabar yuborish: {auto_status}", callback_data="toggle_auto")
    builder.button(text="📝 Habar matni va rasmini o'zgartirish", callback_data="set_text")
    builder.button(text=f"⏱ Interval ({u['interval']} sek)", callback_data="set_interval")
    builder.button(text="👥 Guruhlarni sozlash", callback_data="manage_groups")
    builder.button(text=f"⚙️ Rejim: {mode_str}", callback_data="toggle_mode")
    builder.adjust(1)
    return builder.as_markup()
    # --- /START KOMANDASI ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    get_user(user_id)
    
    # Majburiy obunani tekshiramiz
    is_subscribed = await check_subscription(user_id)
    if not is_subscribed:
        sub_builder = InlineKeyboardBuilder()
        sub_builder.button(text="📢 Kanalga obuna bo'lish", url=f"https://t.me/{REQUIRED_CHANNEL.replace('@', '')}")
        sub_builder.button(text="✅ Obunani tekshirish", callback_data="check_sub")
        sub_builder.adjust(1)
        
        await message.answer(
            f"⚠️ Botdan foydalanish uchun avval quyidagi kanalimizga obuna bo'ling:\n\n{REQUIRED_CHANNEL}",
            reply_markup=sub_builder.as_markup()
        )
        return

    u = get_user(user_id)
    vip_str = "💎 Pro (VIP)" if u["is_vip"] else "💙 Bepul"
    auto_str = "🟢 Yoqiq" if u["auto_active"] else "❌ O'chiq"
    
    welcome_text = (
        f"🤖 Boshqaruv Paneli\n\n"
        f"👥 Ulangan: {len(u['groups'])} ta guruh\n"
        f"🚀 Auto Habar: {auto_str}\n"
        f"⭐️ Sizning Tarifingiz: {vip_str}\n"
        f"⏱ Interval: {u['interval']} sekund\n\n"
        f"👇 Kerakli tugmani pastdan tanlang:"
    )
    
    panel_builder = InlineKeyboardBuilder()
    panel_builder.button(text="🎛 Boshqaruv paneli", callback_data="open_panel")
    panel_builder.button(text="🔄 Autoreply", callback_data="open_autoreply")
    panel_builder.adjust(1)

    await message.answer(welcome_text, reply_markup=panel_builder.as_markup())
    await message.answer("👇 Asosiy menyu:", reply_markup=get_main_keyboard())

# --- OBUNANI QAYTA TEKSHIRISH CALLBACK ---
@dp.callback_query(F.data == "check_sub")
async def callback_check_sub(callback: types.CallbackQuery):
    if await check_subscription(callback.from_user.id):
        await callback.message.answer("✅ Obunangiz tasdiqlandi! Endi botdan to'liq foydalanishingiz mumkin.")
        await start_cmd(callback.message)
    else:
        await callback.answer("❌ Hali kanalga obuna bo'lmadingiz!", show_alert=True)

# --- MENYU TUGMALARI ISHLashi ---
@dp.message(F.text.in_({"👤 Profillar", "👤 Kabinet"}))
async def profile_msg(message: types.Message):
    u = get_user(message.from_user.id)
    vip_str = "💎 Pro (VIP)" if u["is_vip"] else "💙 Bepul"
    text = (
        f"👤 Shaxsiy Kabinet\n\n"
        f"🆔 ID: {message.from_user.id}\n"
        f"⭐️ Tarif: {vip_str}\n"
        f"👥 Ulangan guruhlar: {len(u['groups'])} ta\n"
        f"🔄 Holat: {'Faol 🟢' if u['auto_active'] else 'To\'xtatilgan 🔴'}"
    )
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "👑 Pro tarif")
async def pro_tarif_msg(message: types.Message):
    text = (
        f"💎 Pro (VIP) Tarif imkoniyatlari:\n\n"
        f"• Interval har 0.1 sekundda xabar yuboradi (Bepullarda 0.5s - 5 min).\n"
        f"• Xabarlar ostidagi reklama yozuvi (@AutoXabarchiNewBot orqali...) olib tashlanadi.\n"
        f"• Cheksiz guruhlar va ustuvor tezlik.\n\n"
        f"💳 Sotib olish uchun karta raqami:\n"
        f"9860 1466 4986 4312 (N.X)\n\n"
        f"To'lov qilgandan so'ng chekni adminchaga yuboring: {ADMIN_USERNAME}"
    )
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 VIP Sotib olish (Admin)", url=f"https://t.me/{ADMIN_USERNAME.replace('@', '')}")
    await message.answer(text, reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.message(F.text == "⚙️ Sozlamalar")
async def settings_msg(message: types.Message):
    u = get_user(message.from_user.id)
    await message.answer("⚙️ Boshqaruv Paneli Sozlamalari:", reply_markup=get_control_panel_markup(u), parse_mode="Markdown")

@dp.message(F.text == "🗓 Kalendar")
async def calendar_msg(message: types.Message):
    await message.answer("🗓 Kalendar & Vaqt:\n\nBot 24/7 uzluksiz rejimda ishlaydi. Belgilangan vaqt oralig'ida xabarlarni guruhlarga yuborib turadi.")
    @dp.message(F.text == "🔧 Foydali funksiyalar")
async def tools_msg(message: types.Message):
    await message.answer("🔧 Foydali funksiyalar:\n\n• Rasm + Matnli xabarlar\n• Avtomatik javob berish (Autoreply)\n• Tezkor interval sozlamasi")

@dp.message(F.text == "📊 Statistika")
async def stats_msg(message: types.Message):
    u = get_user(message.from_user.id)
    await message.answer(f"📊 Statistika:\n\n• Ulangan guruhlar: {len(u['groups'])}\n• Joriy interval: {u['interval']} sekund\n• Holat: Barqaror ishlamoqda 🚀")

@dp.message(F.text.in_({"❓ Yordam", "📖 Qo'llanma"}))
async def help_msg(message: types.Message):
    text = (
        f"📖 Qo'llanma va Yordam:\n\n"
        f"1. Botni guruhlaringizga qo'shib Admin qiling.\n"
        f"2. Boshqaruv paneli orqali xabar matni yoki rasmini kiriting.\n"
        f"3. Autohabarni yoqing va bot o'zi avtomatik tarqatishni boshlaydi.\n\n"
        f"👨‍💻 Admin bilan bog'lanish: {ADMIN_USERNAME}"
    )
    await message.answer(text, parse_mode="Markdown")

# --- INLINE CALLBACKLAR (BOSHQARUV PANELI) ---
@dp.callback_query(F.data == "open_panel")
async def cb_open_panel(callback: types.CallbackQuery):
    u = get_user(callback.from_user.id)
    await callback.message.answer("⚙️ Boshqaruv Paneli:", reply_markup=get_control_panel_markup(u), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "open_autoreply")
async def cb_open_autoreply(callback: types.CallbackQuery):
    u = get_user(callback.from_user.id)
    u["mode"] = "autoreply"
    await callback.message.answer("🔄 Autoreply rejimi yoqildi! Guruhlardagi savollarga avtomatik javob berish rejimiga o'tdingiz.")
    await callback.answer()

@dp.callback_query(F.data == "toggle_auto")
async def cb_toggle_auto(callback: types.CallbackQuery):
    u = get_user(callback.from_user.id)
    u["auto_active"] = not u["auto_active"]
    status = "yoqildi 🟢" if u["auto_active"] else "o'chirildi ❌"
    await callback.message.edit_reply_markup(reply_markup=get_control_panel_markup(u))
    await callback.answer(f"Auto habar {status}")

@dp.callback_query(F.data == "toggle_mode")
async def cb_toggle_mode(callback: types.CallbackQuery):
    u = get_user(callback.from_user.id)
    u["mode"] = "autoreply" if u["mode"] == "normal" else "normal"
    await callback.message.edit_reply_markup(reply_markup=get_control_panel_markup(u))
    await callback.answer(f"Rejim o'zgartirildi: {u['mode']}")

@dp.callback_query(F.data == "set_text")
async def cb_set_text(callback: types.CallbackQuery):
    await callback.message.answer("📝 Iltimos, guruhlarga yuboriladigan matn yoki rasm + matnni yuboring (Bot uni saqlab oladi):")
    await callback.answer()

@dp.callback_query(F.data == "set_interval")
async def cb_set_interval(callback: types.CallbackQuery):
    u = get_user(callback.from_user.id)
    if u["is_vip"]:
        u["interval"] = 0.1
        await callback.message.answer("⚡️ VIP imkoniyati yoqildi! Interval 0.1 sekundga o'rnatildi.")
    else:
        u["interval"] = 30
        await callback.message.answer("⏱ Bepul tarif uchun interval 30 sekundga o'rnatildi (Cheklov: 0.5 sekunddan 5 minutgacha). Pro tarifga o'tsangiz 0.1 sekund qilsa bo'ladi.")
    await callback.message.edit_reply_markup(reply_markup=get_control_panel_markup(u))
    await callback.answer()

@dp.callback_query(F.data == "manage_groups")
async def cb_manage_groups(callback: types.CallbackQuery):
    u = get_user(callback.from_user.id)
    await callback.message.answer(f"👥 Hozir ulangan guruhlar soni: {len(u['groups'])} ta.\n\nGuruh qo'shish uchun botni o'sha guruhga admin qiling va guruh havolasini yoki ID sini yuboring.")
    await callback.answer()

# --- FOYDALANUVCHIDAN MATN YOKI RASM QABUL QILISH ---
@dp.message(F.photo | F.text)
async def save_user_content(message: types.Message):
    if message.text and message.text.startswith("/"):
        return  # Komandalarga aralashmasin
    
    u = get_user(message.from_user.id)
    if message.photo:
        u["photo"] = message.photo[-1].file_id
        u["text"] = message.caption or ""
        await message.answer("✅ Rasm va matn muvaffaqiyatli saqlandi! Endi boshqaruv panelidan Autohabarni yoqishingiz mumkin.")
    elif message.text:
        u["photo"] = None
        u["text"] = message.text
        await message.answer("✅ Xabar matni muvaffaqiyatli saqlandi! Endi boshqaruv panelidan Autohabarni yoqishingiz mumkin.")

# --- BOTNI ISHGA TUSHIRISH ---
async def main():
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    print("Bot muvaffaqiyatli ishga tushdi va ishlamoqda...")
    asyncio.create_task(background_scheduler())
    await dp.start_polling(bot)

if name == "main":
    asyncio.run(main())
