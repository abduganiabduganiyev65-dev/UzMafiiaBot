import os
import time
import random
import threading
from flask import Flask
import telebot
from telebot import types

# -------------------------------------------------------------
# RENDER UCHUN VEB-SERVER
# -------------------------------------------------------------
web_app = Flask(name)

@web_app.route('/')
def health_check():
    return "UzMafia Bot 24/7 rejimida muvaffaqiyatli ishlamoqda!", 200

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_web_server, daemon=True).start()

# -------------------------------------------------------------
# BOT CONFIGURATION
# -------------------------------------------------------------
TOKEN = os.getenv("BOT_TOKEN", "8244204287:AAGQrSjCnGAH-YGyi51dff2VTwbNytwE_vI")
bot = telebot.TeleBot(TOKEN)

# -------------------------------------------------------------
# MA'LUMOTLAR BAZASI
# -------------------------------------------------------------
users_db = {}
games_db = {}

def get_user(user_id, name="O'yinchi"):
    if user_id not in users_db:
        users_db[user_id] = {
            "name": name,
            "coins": 500,
            "games": 0,
            "wins": 0,
            "last_daily": 0
        }
    else:
        users_db[user_id]["name"] = name
    return users_db[user_id]

class GameInstance:
    def init(self, chat_id):
        self.chat_id = chat_id
        self.state = "JOINING"
        self.players = {}
        self.night_actions = {"kill": None, "heal": None, "check": None}
        self.votes = {}

# -------------------------------------------------------------
# BUYRUQLAR (COMMANDS)
# -------------------------------------------------------------
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user = get_user(message.from_user.id, message.from_user.first_name)
    text = (
        f"<b>Salom, {user['name']}! 👋</b>\n\n"
        f"🎭 <b>UzMafia Bot</b>ga xush kelibsiz! Bot guruhlarda professional Mafia o'yinini o'tkazish uchun mo'ljallangan.\n\n"
        f"<b>Asosiy buyruqlar:</b>\n"
        f"💰 /profile - Tangalar va balansingizni ko'rish\n"
        f"🎁 /daily - Har kunlik bepul coinlarni olish\n"
        f"🏆 /top - Eng kuchli va boy o'yinchilar reytingi\n"
        f"🎮 /newgame - Guruhda yangi o'yin boshlash\n"
        f"ℹ️ /roles - O'yindagi rollar haqida ma'lumot\n\n"
        f"<i>Botni guruhga qo'shing va adminga aylantiring!</i>"
    )
    bot.reply_to(message, text, parse_mode="HTML")

@bot.message_handler(commands=['profile'])
def show_profile(message):
    user = get_user(message.from_user.id, message.from_user.first_name)
    text = (
        f"👤 <b>Foydalanuvchi:</b> {user['name']}\n"
        f"💰 <b>Tangalar (Coins):</b> {user['coins']} 🪙\n"
        f"🎮 <b>Jami o'yinlar:</b> {user['games']}\n"
        f"🏆 <b>G'alabalar:</b> {user['wins']}\n"
    )
    bot.reply_to(message, text, parse_mode="HTML")

@bot.message_handler(commands=['daily'])
def daily_bonus(message):
    user = get_user(message.from_user.id, message.from_user.first_name)
    now = time.time()
    if now - user.get('last_daily', 0) >= 86400:
        reward = random.randint(150, 350)
        user['coins'] += reward
        user['last_daily'] = now
        bot.reply_to(message, f"🎁 Bugungi kunlik bonusingiz: <b>+{reward} 🪙</b> tanga berildi!", parse_mode="HTML")
    else:
        remaining = int(86400 - (now - user['last_daily']))
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        bot.reply_to(message, f"⏳ Siz bugungi bonusni olgansiz! Keyingi bonus: {hours} soat {minutes} daqiqadan so'ng.", parse_mode="HTML")

@bot.message_handler(commands=['top'])
def show_leaderboard(message):
    sorted_users = sorted(users_db.items(), key=lambda x: x[1]['coins'], reverse=True)[:10]
    if not sorted_users:
        bot.reply_to(message, "Hozircha o'yinchilar yo'q.")
        return
    
    text = "🏆 <b>Eng boy o'yinchilar TOP-10:</b>\n\n"
    for idx, (uid, data) in enumerate(sorted_users, 1):
        text += f"{idx}. {data['name']} — <b>{data['coins']} 🪙</b> ({data['wins']} g'alaba)\n"
    bot.reply_to(message, text, parse_mode="HTML")

@bot.message_handler(commands=['roles'])
def show_roles(message):
    text = (
        "🎭 <b>O'yindagi rollar va ularning vazifalari:</b>\n\n"
        "🔴 <b>Mafiya (Mafia)</b> — Tunda tinch aholini o'ldirish uchun nishon tanlaydi.\n"
        "🕵️ <b>Komissar (Detective)</b> — Tunda shubhali o'yinchining rolini tekshiradi.\n"
        "👨‍⚕️ <b>Shifokor (Doctor)</b> — Tunda biror kishining hayotini saqlab qoladi.\n"
        "👨‍🌾 <b>Tinch fuqaro (Villager)</b> — Kunduzi muhokama va ovoz berishda qatnashadi."
    )
    bot.reply_to(message, text, parse_mode="HTML")

# -------------------------------------------------------------
# MAFIA GAME LOGIC
# -------------------------------------------------------------
@bot.message_handler(commands=['newgame'])
def new_game(message):
    if message.chat.type in ['private']:
        bot.reply_to(message, "⚠️ O'yinni faqat guruhlarda boshlash mumkin!")
        return

    chat_id = message.chat.id
    if chat_id in games_db and games_db[chat_id].state != "ENDED":
        bot.reply_to(message, "⚠️ Bu guruhda allaqachon o'yin ketmoqda!")
        return

    game = GameInstance(chat_id)
    games_db[chat_id] = game

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("➕ O'yinga qo'shilish", callback_data=f"join_{chat_id}"))
    markup.add(types.InlineKeyboardButton("🚀 O'yinni boshlash", callback_data=f"startgame_{chat_id}"))

    bot.send_message(
        chat_id,
        "🎮 <b>Yangi Mafia o'yini e'lon qilindi!</b>\n\n"
        "O'yinda qatnashish uchun pastdagi <b>'➕ O'yinga qo'shilish'</b> tugmasini bosing! (Kamida 4 kishi)",
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith(('join_', 'startgame_')))
def handle_game_registration(call):
    action, chat_id_str = call.data.split('_', 1)
    chat_id = int(chat_id_str)

    if chat_id not in games_db:
        bot.answer_callback_query(call.id, "O'yin topilmadi yoki tugatilgan.", show_alert=True)
        return

    game = games_db[chat_id]

    if action == "join":
        if game.state != "JOINING":
            bot.answer_callback_query(call.id, "O'yin allaqachon boshlangan!", show_alert=True)
            return
        
        user_id = call.from_user.id
        if user_id in game.players:
            bot.answer_callback_query(call.id, "Siz allaqachon ro'yxatdan o'tgansiz!", show_alert=True)
            return

        get_user(user_id, call.from_user.first_name)
        game.players[user_id] = {
            "name": call.from_user.first_name,
            "role": "Villager",
            "alive": True
        }
        bot.answer_callback_query(call.id, "Siz o'yinga qo'shildingiz! 🎉")
        
        player_names = "\n".join([f"• {p['name']}" for p in game.players.values()])
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("➕ O'yinga qo'shilish", callback_data=f"join_{chat_id}"))
        markup.add(types.InlineKeyboardButton("🚀 O'yinni boshlash", callback_data=f"startgame_{chat_id}"))
        
        bot.edit_message_text(
            f"🎮 <b>Yangi Mafia o'yini e'lon qilindi!</b>\n\n"
            f"<b>Qatnashchilar ({len(game.players)} ta):</b>\n{player_names}",
            chat_id=chat_id,
            message_id=call.message.message_id,
            parse_mode="HTML",
            reply_markup=markup
        )

    elif action == "startgame":
        if game.state != "JOINING":
            bot.answer_callback_query(call.id, "O'yin allaqachon boshlangan!", show_alert=True)
            return
        
        if len(game.players) < 4:
            bot.answer_callback_query(call.id, "O'yinni boshlash uchun kamida 4 ta o'yinchi kerak!", show_alert=True)
            return

        bot.answer_callback_query(call.id, "O'yin boshlanmoqda!")
        distribute_roles_and_start_night(game)

def distribute_roles_and_start_night(game):
    game.state = "NIGHT"
    player_ids = list(game.players.keys())
    random.shuffle(player_ids)

    roles_pool = ["Mafia", "Doctor", "Detective"]
    while len(roles_pool) < len(player_ids):
        roles_pool.append("Villager")
    
    random.shuffle(roles_pool)

    for i, uid in enumerate(player_ids):
        role = roles_pool[i]
        game.players[uid]["role"] = role
        try:
            role_titles = {
                "Mafia": "🔴 <b>Mafiya</b>! Tunda o'ldiradigan nishoningizni tanlang.",
                "Doctor": "👨‍⚕️ <b>Shifokor</b>! Tunda kimni davolashni tanlang.",
                "Detective": "🕵️ <b>Komissar</b>! Tunda kimni tekshirishni tanlang.",
                "Villager": "👨‍🌾 <b>Tinch fuqaro</b>! Siz tunda dam olasiz."
            }
            bot.send_message(uid, f"🎭 <b>Sizning rolingiz:</b> {role_titles[role]}", parse_mode="HTML")
        except Exception:
            pass

    bot.send_message(
        game.chat_id,
        "🌃 <b>TUN TUSHDI!</b>\n\n"
        "Shahar uyquga ketdi... Mafiya, Shifokor va Komissar o'z faoliyatini boshlamoqda.\n"
        "Botdan shaxsiy xabar kelgan o'yinchilar 40 soniya ichida tanlov qiling!",
        parse_mode="HTML"
    )

    send_night_action_buttons(game)
    threading.Timer(40, process_night_results, args=[game]).start()

def send_night_action_buttons(game):
    alive_players = [uid for uid, p in game.players.items() if p["alive"]]

    for uid, p in game.players.items():
        if not p["alive"]:
            continue
        
        role = p["role"]
        if role in ["Mafia", "Doctor", "Detective"]:
            markup = types.InlineKeyboardMarkup()
            for target_id in alive_players:
                if target_id == uid and role == "Mafia":
                    continue
                t_name = game.players[target_id]["name"]
                markup.add(types.InlineKeyboardButton(f"🎯 {t_name}", callback_data=f"night_{role}_{game.chat_id}_{target_id}"))
            
            try:
                bot.send_message(uid, f"🌙 <b>{role} harakati:</b> Nishoningizni tanlang:", reply_markup=markup, parse_mode="HTML")
            except Exception:
                pass

@bot.callback_query_handler(func=lambda call: call.data.startswith('night_'))
def handle_night_action(call):
    parts = call.data.split('_')
    role = parts[1]
    chat_id = int(parts[2])
    target_id = int(parts[3])

    if chat_id not in games_db:
        bot.answer_callback_query(call.id, "O'yin topilmadi.")
        return

    game = games_db[chat_id]
    if game.state != "NIGHT":
        bot.answer_callback_query(call.id, "Tun vaqti tugagan.")
        return

    if role == "Mafia":
        game.night_actions["kill"] = target_id
        bot.answer_callback_query(call.id, "O'ldirish uchun nishon tanlandi! 🔴")
    elif role == "Doctor":
        game.night_actions["heal"] = target_id
        bot.answer_callback_query(call.id, "Davolash uchun nishon tanlandi! 👨‍⚕️")
    elif role == "Detective":
        game.night_actions["check"] = target_id
        target_role = game.players[target_id]["role"]
        is_mafia = "Ha (Mafiya)" if target_role == "Mafia" else "Yo'q (Tinch)"
        bot.answer_callback_query(call.id, f"Tekshiruv natijasi: {is_mafia}", show_alert=True)

    bot.edit_message_text("✅ Tanlovingiz qabul qilindi!", chat_id=call.message.chat.id, message_id=call.message.message_id)
    def process_night_results(game):
    if game.state != "NIGHT":
        return
    
    game.state = "DAY"
    killed_id = game.night_actions.get("kill")
    healed_id = game.night_actions.get("heal")
    
    result_text = "☀️ <b>KUN BOTDI, SHAHAR UYG'ONDI!</b>\n\n"

    if killed_id and killed_id != healed_id:
        game.players[killed_id]["alive"] = False
        victim_name = game.players[killed_id]["name"]
        result_text += f"☠️ Afsuski, tunda Mafiya tomonidan <b>{victim_name}</b> o'ldirildi! Uning roli: {game.players[killed_id]['role']}\n\n"
    elif killed_id and killed_id == healed_id:
        result_text += "🛡 Tunda Mafiya hujum qildi, lekin Shifokor o'z vaqtida kelib o'yinchining hayotini saqlab qoldi! Hech kim o'lmadi.\n\n"
    else:
        result_text += "🕊 Tunda hech qanday qotillik yuz bermadi. Shahar tinch!\n\n"

    if check_game_over(game):
        return

    result_text += "💬 <b>Muhokama va Ovoz berish vaqti! (45 soniya)</b>\nKim mafiya deb o'ylasangiz, o'sha o'yinchiga ovoz bering."
    
    markup = types.InlineKeyboardMarkup()
    alive_players = [uid for uid, p in game.players.items() if p["alive"]]
    for target_id in alive_players:
        t_name = game.players[target_id]["name"]
        markup.add(types.InlineKeyboardButton(f"🗳 {t_name}", callback_data=f"vote_{game.chat_id}_{target_id}"))

    bot.send_message(game.chat_id, result_text, parse_mode="HTML", reply_markup=markup)
    threading.Timer(45, process_vote_results, args=[game]).start()

@bot.callback_query_handler(func=lambda call: call.data.startswith('vote_'))
def handle_vote(call):
    parts = call.data.split('_')
    chat_id = int(parts[1])
    target_id = int(parts[2])
    voter_id = call.from_user.id

    if chat_id not in games_db:
        return

    game = games_db[chat_id]
    if game.state != "DAY":
        bot.answer_callback_query(call.id, "Ovoz berish vaqti emas.")
        return

    if voter_id not in game.players or not game.players[voter_id]["alive"]:
        bot.answer_callback_query(call.id, "Faqat tirik o'yinchilar ovoz bera oladi!", show_alert=True)
        return

    game.votes[voter_id] = target_id
    bot.answer_callback_query(call.id, f"Ovozingiz {game.players[target_id]['name']} uchun qabul qilindi!")

def process_vote_results(game):
    if game.state != "DAY":
        return

    if not game.votes:
        bot.send_message(game.chat_id, "🗳 Hech kim ovoz bermadi. Sud hech kimni sud qilmadi.")
    else:
        vote_counts = {}
        for target in game.votes.values():
            vote_counts[target] = vote_counts.get(target, 0) + 1
        
        max_votes = max(vote_counts.values())
        top_targets = [t for t, count in vote_counts.items() if count == max_votes]

        if len(top_targets) > 1:
            bot.send_message(game.chat_id, "⚖️ Ovozlari teng bo'ldi. Bugun hech kim o'yindan chiqarilmadi.")
        else:
            executed_id = top_targets[0]
            game.players[executed_id]["alive"] = False
            ex_name = game.players[executed_id]["name"]
            ex_role = game.players[executed_id]["role"]
            bot.send_message(
                game.chat_id,
                f"⚖️ Shahar qaroriga ko'ra <b>{ex_name}</b> osib o'ldirildi!\n"
                f"Uning roli: <b>{ex_role}</b> edi.",
                parse_mode="HTML"
            )

    game.votes = {}
    game.night_actions = {"kill": None, "heal": None, "check": None}

    if not check_game_over(game):
        threading.Timer(3, distribute_roles_and_start_night, args=[game]).start()

def check_game_over(game):
    alive_mafia = [uid for uid, p in game.players.items() if p["alive"] and p["role"] == "Mafia"]
    alive_others = [uid for uid, p in game.players.items() if p["alive"] and p["role"] != "Mafia"]

    if len(alive_mafia) == 0:
        game.state = "ENDED"
        reward_winners(game, win_role="Villager")
        bot.send_message(
            game.chat_id,
            "🎉 <b>TINCH AHOLI VA SHIFOKORLAR G'ALABA QOZONDI!</b>\n\n"
            "Barcha mafiyalar yo'q qilindi. Har bir g'olibga +200 🪙 berildi!",
            parse_mode="HTML"
        )
        return True

    elif len(alive_mafia) >= len(alive_others):
        game.state = "ENDED"
        reward_winners(game, win_role="Mafia")
        bot.send_message(
            game.chat_id,
            "🔴 <b>MAFIYA G'ALABA QOZONDI!</b>\n\n"
            "Mafiya shaharni to'liq o'z nazoratiga oldi. Mafiyaga +300 🪙 mukofot berildi!",
            parse_mode="HTML"
        )
        return True

    return False

def reward_winners(game, win_role):
    for uid, p in game.players.items():
        user = get_user(uid, p["name"])
        user["games"] += 1
        if (win_role == "Mafia" and p["role"] == "Mafia") or (win_role == "Villager" and p["role"] != "Mafia"):
            user["wins"] += 1
            user["coins"] += 300 if p["role"] == "Mafia" else 200

if name == 'main':
    print("UzMafia Bot muvaffaqiyatli ishga tushdi...")
    bot.infinity_polling(skip_pending=True)
