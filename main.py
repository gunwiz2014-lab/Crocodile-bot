import os, random, asyncio
from datetime import date, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, BotCommandScopeAllGroupChats, BotCommandScopeAllPrivateChats
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ChatMemberHandler
from data import *

BOT_TOKEN = os.getenv("BOT_TOKEN", "ВСТАВЬТЕ_ТОКЕН_СЮДА")
BOT_USERNAME = os.getenv("BOT_USERNAME", "Vhfbju_bot")

# ─── ХРАНИЛИЩЕ ────────────────────────────────────────────────────────────────
games={}; wheel_games={}; speed_games={}; trivia_games={}
hangman_games={}; number_games={}; blackjack_games={}
duel_games={}; roulette_games={}; dice_games={}; uno_games={}
players={}; group_players={}; tournaments={}
bot_running = {"active": True}  # кнопка стоп


def get_player(uid, name):
    if uid not in players:
        players[uid] = {
            "name":name,"total_score":0,"speedrun_access":False,"vip":False,
            "streak":0,"protection":False,"double":False,"extra_life":False,
            "time_bonus":False,"double_daily":False,"score_boost":False,
            "multiplier":False,"nick_color":"","crown_until":None,
            "shield_until":None,"frozen_until":None,"mirror":False,
            "achievements":set(),"games_played":set(),"wins":0,
            "duel_wins":0,"last_daily":None,"daily_streak":0,
            "inventory":{},"shop_purchases":0,
        }
    players[uid]["name"] = name
    return players[uid]


def add_score(uid, name, amount):
    p = get_player(uid, name)
    if p.get("score_boost") and amount > 0:
        amount = int(amount * 1.5); p["score_boost"] = False
    if p.get("multiplier") and amount > 0:
        amount = int(amount * 3); p["multiplier"] = False
    p["total_score"] = max(0, p["total_score"] + amount)
    check_achievements(uid, name)


def check_achievements(uid, name):
    p = get_player(uid, name); new = []
    checks = [
        ("first_win", p["wins"] >= 1),
        ("rich", p["total_score"] >= 1000),
        ("mega_rich", p["total_score"] >= 5000),
        ("legend", p["total_score"] >= 10000),
        ("collector", len(p["games_played"]) >= 5),
        ("all_games", len(p["games_played"]) >= 12),
        ("winner10", p["wins"] >= 10),
        ("winner50", p["wins"] >= 50),
        ("winner100", p["wins"] >= 100),
        ("duelist", p.get("duel_wins", 0) >= 5),
        ("shopaholic", p.get("shop_purchases", 0) >= 10),
    ]
    for key, cond in checks:
        if cond and key not in p["achievements"]:
            p["achievements"].add(key); new.append(key)
    return new


def get_title(score):
    t = TITLES[0][1]
    for threshold, title in TITLES:
        if score >= threshold: t = title
    return t


def get_nick(uid, name):
    p = players.get(uid, {})
    color = p.get("nick_color", "")
    today = date.today().isoformat()
    crown = "💎 " if p.get("crown_until") and today <= p["crown_until"] else ""
    vip = " 👑" if p.get("vip") else ""
    return f"{crown}{color}{name}{vip}"


def is_frozen(uid):
    p = players.get(uid, {})
    if p.get("frozen_until"):
        return date.today().isoformat() <= p["frozen_until"]
    return False


def global_scores_text():
    if not players: return "Пока никто не набрал очков."
    sp = sorted(players.values(), key=lambda x: x["total_score"], reverse=True)
    medals = ["🥇","🥈","🥉"]; lines = []
    for i, p in enumerate(sp[:10]):
        medal = medals[i] if i < 3 else f"{i+1}."
        title = get_title(p["total_score"])
        color = p.get("nick_color","")
        vip = " 👑" if p.get("vip") else ""
        crown = "💎 " if p.get("crown_until") and date.today().isoformat() <= p["crown_until"] else ""
        lines.append(f"{medal} {crown}{color}{p['name']}{vip} {title} — {p['total_score']} оч.")
    return "\n".join(lines)


def display_word(word, guessed):
    return " ".join(c if c in guessed or c == " " else "\\_" for c in word)


def shop_price(key):
    icon, name, desc, price = SHOP_ITEMS[key]
    if key in SALE_ITEMS:
        return int(price * SALE_DISCOUNT)
    return price


def spin_drum(): return random.choice(DRUM)
def spin_slots(): return [random.choice(SLOT_SYMBOLS) for _ in range(3)]
def check_slots(s):
    if s[0]==s[1]==s[2]:
        prizes = {"💎":2000,"7️⃣":777,"⭐":500,"🔔":300,"🍋":200,"🍒":150,"🃏":400,"🎯":350,"🌈":1000,"💰":600}
        return prizes.get(s[0], 200)
    if len(set(s)) < 3: return 75
    return 0
def card_value(hand):
    v = sum(CARD_VALS[c] for c in hand); a = hand.count("A")
    while v > 21 and a: v -= 10; a -= 1
    return v
def deal_card(): return random.choice(CARDS)
def hand_str(h): return " ".join(h)+f" (={card_value(h)})"
def is_group(chat): return chat.type in ("group","supergroup")


# ─── УНО ──────────────────────────────────────────────────────────────────────
def make_uno_deck():
    deck = []
    for color in UNO_COLORS:
        for val in UNO_VALUES:
            deck.append(f"{color}{val}")
            if val != "0": deck.append(f"{color}{val}")
    for special in UNO_SPECIAL:
        deck.extend([special]*4)
    random.shuffle(deck)
    return deck

def uno_card_matches(card, top):
    if card in UNO_SPECIAL: return True
    if top in UNO_SPECIAL: return True
    card_color = card[0] if card else ""
    top_color = top[0] if top else ""
    card_val = card[1:] if card else ""
    top_val = top[1:] if top else ""
    return card_color == top_color or card_val == top_val


# ─── КЛАВИАТУРЫ ───────────────────────────────────────────────────────────────
def make_main_keyboard(group=False, admin=False):
    rows = [
        [InlineKeyboardButton("🐊 Крокодил",callback_data="menu_game"),
         InlineKeyboardButton("🎡 Поле чудес",callback_data="menu_wheel")],
        [InlineKeyboardButton("⚡ Спидран",callback_data="menu_speedrun"),
         InlineKeyboardButton("🧠 Викторина",callback_data="menu_trivia")],
        [InlineKeyboardButton("📝 Виселица",callback_data="menu_hangman"),
         InlineKeyboardButton("🔢 Угадай число",callback_data="menu_number")],
        [InlineKeyboardButton("🃏 Блэкджек",callback_data="menu_blackjack"),
         InlineKeyboardButton("🎰 Слоты",callback_data="menu_slots")],
        [InlineKeyboardButton("❓ Правда/Действие",callback_data="menu_tod"),
         InlineKeyboardButton("⚔️ Дуэль",callback_data="menu_duel")],
        [InlineKeyboardButton("🎯 Рулетка",callback_data="menu_roulette"),
         InlineKeyboardButton("🎲 Кубик",callback_data="menu_dice")],
        [InlineKeyboardButton("🎴 УНО",callback_data="menu_uno"),
         InlineKeyboardButton("♠️ Покер",callback_data="menu_poker")],
        [InlineKeyboardButton("🏆 Турнир",callback_data="menu_tournament"),
         InlineKeyboardButton("🃏 Карты (21)",callback_data="menu_blackjack")],
        [InlineKeyboardButton("🛒 Магазин 🔥СКИДКИ",callback_data="menu_shop"),
         InlineKeyboardButton("📊 Счёт",callback_data="menu_scores")],
        [InlineKeyboardButton("🏆 Достижения",callback_data="menu_achievements"),
         InlineKeyboardButton("🎁 Бонус",callback_data="menu_daily")],
        [InlineKeyboardButton("👤 Профиль",callback_data="menu_profile"),
         InlineKeyboardButton("🎒 Инвентарь",callback_data="menu_inventory")],
    ]
    if group:
        rows.append([InlineKeyboardButton("✋ Присоединиться",callback_data="menu_join")])
    else:
        rows.insert(0,[InlineKeyboardButton("➕ Добавить в группу",url=f"https://t.me/{BOT_USERNAME}?startgroup=true")])
    if admin:
        rows.append([InlineKeyboardButton("🛑 СТОП БОТ",callback_data="admin_stop")])
    return InlineKeyboardMarkup(rows)

def make_croc_kb(): return InlineKeyboardMarkup([[InlineKeyboardButton("⏭ Пропустить",callback_data="croc_skip"),InlineKeyboardButton("🛑 Стоп",callback_data="croc_stop")]])
def make_wheel_kb(): return InlineKeyboardMarkup([[InlineKeyboardButton("🎡 Крутить барабан",callback_data="wheel_spin"),InlineKeyboardButton("🛑 Стоп",callback_data="wheel_stop")]])
def make_bj_kb(): return InlineKeyboardMarkup([[InlineKeyboardButton("🃏 Ещё",callback_data="bj_hit"),InlineKeyboardButton("✋ Хватит",callback_data="bj_stand")]])
def make_duel_kb(cid): return InlineKeyboardMarkup([[InlineKeyboardButton("⚔️ Принять!",callback_data=f"duel_accept_{cid}"),InlineKeyboardButton("❌ Отказать",callback_data="duel_decline")]])
def make_roulette_kb(): return InlineKeyboardMarkup([[InlineKeyboardButton("🔴 Красное",callback_data="rou_red"),InlineKeyboardButton("⚫ Чёрное",callback_data="rou_black"),InlineKeyboardButton("🟢 Зеро",callback_data="rou_zero")]])
def make_dice_kb(): return InlineKeyboardMarkup([[InlineKeyboardButton("🎲 Бросить!",callback_data="dice_roll")]])
def make_trivia_kb(): return InlineKeyboardMarkup([[InlineKeyboardButton("🟢 Лёгкий +50",callback_data="trivia_easy"),InlineKeyboardButton("🟡 Средний +150",callback_data="trivia_medium"),InlineKeyboardButton("🔴 Сложный +300",callback_data="trivia_hard")]])
def make_uno_action_kb(chat_id):
    game = uno_games.get(chat_id, {})
    rows = [[InlineKeyboardButton("🃏 Взять карту",callback_data="uno_draw"),InlineKeyboardButton("🃏 Показать карты",callback_data="uno_show")]]
    return InlineKeyboardMarkup(rows)

def make_shop_keyboard(p):
    rows = []
    # Акционные предметы сначала
    rows.append([InlineKeyboardButton("🔥 ═══ СКИДКИ 20% ═══ 🔥",callback_data="shop_info")])
    for key in SALE_ITEMS:
        if key in SHOP_ITEMS:
            icon,name,_,orig = SHOP_ITEMS[key]
            price = int(orig * SALE_DISCOUNT)
            rows.append([InlineKeyboardButton(f"{icon} {name} 🔥{price} оч (было {orig})",callback_data=f"shop_{key}")])
    rows.append([InlineKeyboardButton("── Все предметы ──",callback_data="shop_info")])
    for key,(icon,name,desc,price) in SHOP_ITEMS.items():
        if key in SALE_ITEMS: continue
        owned = ""
        if key=="vip" and p.get("vip"): owned=" ✅"
        if key=="speedrun" and p.get("speedrun_access"): owned=" ✅"
        actual_price = shop_price(key)
        rows.append([InlineKeyboardButton(f"{icon} {name}{owned} — {actual_price} оч.",callback_data=f"shop_{key}")])
    rows.append([InlineKeyboardButton("🔙 Назад",callback_data="menu_back")])
    return InlineKeyboardMarkup(rows)


async def setup_commands(app):
    cmds_both = [
        BotCommand("start","🎮 Главное меню"),BotCommand("help","❓ Все игры и правила"),
        BotCommand("profile","👤 Мой профиль"),BotCommand("achievements","🏆 Достижения"),
        BotCommand("inventory","🎒 Инвентарь"),BotCommand("daily","🎁 Ежедневный бонус"),
        BotCommand("scores","📊 Таблица очков"),BotCommand("shop","🛒 Магазин со скидками"),
        BotCommand("game","🐊 Крокодил"),BotCommand("wheel","🎡 Поле чудес"),
        BotCommand("speedrun","⚡ Спидран"),BotCommand("trivia","🧠 Викторина"),
        BotCommand("hangman","📝 Виселица"),BotCommand("number","🔢 Угадай число"),
        BotCommand("blackjack","🃏 Блэкджек"),BotCommand("slots","🎰 Слоты"),
        BotCommand("tod","❓ Правда или Действие"),BotCommand("roulette","🎯 Рулетка"),
        BotCommand("dice","🎲 Кубик удачи"),BotCommand("uno","🎴 УНО"),
        BotCommand("poker","♠️ Покер"),BotCommand("tournament","🏆 Турнир"),
        BotCommand("duel","⚔️ Дуэль (ответь на сообщение)"),
        BotCommand("stopbot","🛑 Остановить бота (админ)"),
    ]
    group_extra = [BotCommand("join","✋ Присоединиться к игре")]
    await app.bot.set_my_commands(cmds_both + group_extra, scope=BotCommandScopeAllGroupChats())
    await app.bot.set_my_commands(cmds_both, scope=BotCommandScopeAllPrivateChats())


async def greet_new_group(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    result = update.my_chat_member
    if not result: return
    old = result.old_chat_member.status; new = result.new_chat_member.status
    if old in ("left","kicked") and new in ("member","administrator"):
        chat = update.effective_chat
        await ctx.bot.send_message(chat_id=chat.id,
            text=f"👋 Привет, *{chat.title}*!\n\n🎮 *Игровой бот* — 12 игр!\n\n"
                 f"🐊 Крокодил | 🎡 Поле чудес | ⚡ Спидран\n"
                 f"🧠 Викторина (3 уровня!) | 📝 Виселица | 🔢 Число\n"
                 f"🃏 Блэкджек | 🎰 Слоты | ❓ Правда/Действие\n"
                 f"⚔️ Дуэль | 🎯 Рулетка | 🎲 Кубик | 🎴 УНО\n\n"
                 f"🛒 Магазин с 30+ предметами и *СКИДКАМИ*!\n"
                 f"🏆 25 достижений | 👑 Титулы | 🎁 Ежедневные бонусы\n\n"
                 f"✋ Нажмите *Присоединиться*!",
            parse_mode="Markdown", reply_markup=make_main_keyboard(group=True))


# ─── ОСНОВНЫЕ КОМАНДЫ ─────────────────────────────────────────────────────────

ADMIN_IDS = set()  # добавь свой user_id сюда для доступа к стопу

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user; chat = update.effective_chat
    p = get_player(user.id, user.first_name); g = is_group(chat)
    title = get_title(p["total_score"])
    is_admin = user.id in ADMIN_IDS or not ADMIN_IDS  # если список пуст — все админы
    await update.message.reply_text(
        f"👋 Привет, *{get_nick(user.id, user.first_name)}*!\n\n"
        f"🏅 {title} | 💰 {p['total_score']} оч | 🏆 {p['wins']} побед\n\n"
        f"🎮 *12 игр* | 🛒 *30+ предметов* | 🏆 *25 достижений*\n\n"
        f"{'✋ Присоединись! 👇' if g else '➕ Добавь в группу! 👇'}",
        parse_mode="Markdown", reply_markup=make_main_keyboard(group=g, admin=is_admin))


async def cmd_stopbot(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if ADMIN_IDS and user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Нет доступа."); return
    bot_running["active"] = False
    await update.message.reply_text("🛑 *Бот остановлен!*\n\nВсе активные игры завершены.", parse_mode="Markdown")
    # Отменяем все таймеры
    for g in [games, wheel_games, speed_games, trivia_games, hangman_games, number_games]:
        for chat_id, game in g.items():
            if game.get("active"): game["active"] = False
            if game.get("timer_task"): game["timer_task"].cancel()


async def cmd_profile(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user; p = get_player(user.id, user.first_name)
    title = get_title(p["total_score"])
    achs = [f"{ACHIEVEMENTS[a][0]}" for a in p["achievements"] if a in ACHIEVEMENTS]
    inv = {k:v for k,v in p.get("inventory",{}).items() if v>0}
    inv_text = ", ".join([f"{SHOP_ITEMS[k][0]}x{v}" for k,v in inv.items() if k in SHOP_ITEMS]) or "пусто"
    shields = []
    if p.get("shield_until") and date.today().isoformat() <= p["shield_until"]: shields.append("🛡")
    if p.get("crown_until") and date.today().isoformat() <= p["crown_until"]: shields.append("💎")
    await update.message.reply_text(
        f"👤 *{get_nick(user.id, user.first_name)}*\n\n"
        f"🏅 Титул: {title}\n💰 Очки: *{p['total_score']}*\n"
        f"🏆 Победы: {p['wins']} | ⚔️ Дуэли: {p.get('duel_wins',0)}\n"
        f"🎮 Игр: {len(p['games_played'])} | 🛒 Покупок: {p.get('shop_purchases',0)}\n"
        f"👑 VIP: {'Да' if p['vip'] else 'Нет'} | ⚡ Спидран: {'Да' if p['speedrun_access'] else 'Нет'}\n"
        f"{'🛡 '.join(shields) if shields else ''}\n\n"
        f"🏆 Достижения ({len(p['achievements'])}): {' '.join(achs) if achs else 'Нет'}\n\n"
        f"🎒 Инвентарь: {inv_text}", parse_mode="Markdown")


async def cmd_achievements(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user; p = get_player(user.id, user.first_name)
    unlocked = sum(1 for k in ACHIEVEMENTS if k in p["achievements"])
    lines = [f"{'✅' if k in p['achievements'] else '🔒'} {v[0]} *{v[1]}* — {v[2]}" for k,v in ACHIEVEMENTS.items()]
    await update.message.reply_text(f"🏆 *Достижения {user.first_name}* ({unlocked}/{len(ACHIEVEMENTS)})\n\n"+"\n".join(lines), parse_mode="Markdown")


async def cmd_inventory(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user; p = get_player(user.id, user.first_name)
    inv = {k:v for k,v in p.get("inventory",{}).items() if v>0}
    if not inv: await update.message.reply_text("🎒 *Инвентарь пуст*\n\nКупи предметы в /shop!", parse_mode="Markdown"); return
    lines = [f"{SHOP_ITEMS[k][0]} *{SHOP_ITEMS[k][1]}* x{v} — {SHOP_ITEMS[k][2]}" for k,v in inv.items() if k in SHOP_ITEMS]
    await update.message.reply_text(f"🎒 *Инвентарь {user.first_name}*\n\n"+"\n".join(lines), parse_mode="Markdown")


async def cmd_daily(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user; p = get_player(user.id, user.first_name)
    today = date.today().isoformat()
    if p.get("last_daily") == today:
        await update.message.reply_text("🎁 Уже получил сегодня!\nПриходи завтра 😊", parse_mode="Markdown"); return
    bonus = random.randint(50, 300)
    if p.get("double_daily"): bonus *= 2; p["double_daily"] = False
    p["last_daily"] = today; p["daily_streak"] = p.get("daily_streak",0)+1
    streak = p["daily_streak"]
    if streak >= 7 and "daily7" not in p["achievements"]: p["achievements"].add("daily7")
    if streak >= 30 and "daily30" not in p["achievements"]: p["achievements"].add("daily30")
    streak_bonus = bonus // 2 if streak >= 3 else 0
    total_bonus = bonus + streak_bonus
    add_score(user.id, user.first_name, total_bonus)
    streak_msg = f"\n🔥 Серия {streak} дней! +{streak_bonus} бонус!" if streak > 1 else ""
    await update.message.reply_text(
        f"🎁 *Ежедневный бонус!*\n\n+*{total_bonus}* очков!{streak_msg}\n\n💰 Всего: {p['total_score']}", parse_mode="Markdown")


async def cmd_scores(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"📊 *Таблица очков*\n\n{global_scores_text()}", parse_mode="Markdown")


async def cmd_shop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user; p = get_player(user.id, user.first_name)
    sale_items = ", ".join([f"{SHOP_ITEMS[k][0]}{SHOP_ITEMS[k][1]}" for k in SALE_ITEMS if k in SHOP_ITEMS])
    await update.message.reply_text(
        f"🛒 *Магазин* — {len(SHOP_ITEMS)} предметов!\n\n"
        f"💰 Твои очки: *{p['total_score']}*\n\n"
        f"🔥 *СКИДКИ 20%:* {sale_items}\n\n"
        f"Выбери предмет:",
        parse_mode="Markdown", reply_markup=make_shop_keyboard(p))


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    g = is_group(update.effective_chat)
    await update.message.reply_text(
        "📖 *Все игры*\n\n"
        "🐊 /game — Крокодил (угадай слово)\n"
        "🎡 /wheel — Поле чудес (барабан)\n"
        "⚡ /speedrun — Спидран 30 сек\n"
        "🧠 /trivia — Викторина (3 уровня!)\n"
        "📝 /hangman — Виселица\n"
        "🔢 /number — Угадай число\n"
        "🃏 /blackjack — Блэкджек\n"
        "🎰 /slots — Слоты\n"
        "❓ /tod — Правда или Действие\n"
        "⚔️ /duel — Дуэль (ответь на сообщение)\n"
        "🎯 /roulette — Рулетка\n"
        "🎲 /dice — Кубик удачи\n"
        "🎴 /uno — УНО (мультиплеер!)\n"
        "♠️ /poker — Покер\n"
        "🏆 /tournament — Турнир\n\n"
        "🎁 /daily | 🏆 /achievements\n"
        "👤 /profile | 🎒 /inventory\n"
        "🛒 /shop 🔥СКИДКИ | 📊 /scores",
        parse_mode="Markdown", reply_markup=make_main_keyboard(group=g))


async def cmd_join(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id; user = update.effective_user
    get_player(user.id, user.first_name)
    if chat_id not in group_players: group_players[chat_id] = {}
    if user.id in group_players[chat_id]:
        await update.message.reply_text(f"✅ *{user.first_name}*, ты уже в игре!", parse_mode="Markdown"); return
    group_players[chat_id][user.id] = user.first_name
    names = ", ".join(group_players[chat_id].values())
    await update.message.reply_text(
        f"✋ *{user.first_name}* присоединился(ась)!\n👥 {names} ({len(group_players[chat_id])} чел.)",
        parse_mode="Markdown", reply_markup=make_main_keyboard(group=True))


# ══════════════════════════════════════════════════════════════════════════════
# ИГРЫ
# ══════════════════════════════════════════════════════════════════════════════

async def croc_timer(chat_id, ctx):
    await asyncio.sleep(ROUND_TIME_CROC)
    game = games.get(chat_id)
    if game and game.get("active"):
        game["active"] = False
        await ctx.bot.send_message(chat_id=chat_id, text=f"⏰ Время вышло!\nСлово: *{game['word'].upper()}*\n\n▶️ /game", parse_mode="Markdown")

async def start_croc(chat_id, user, ctx, reply):
    if not bot_running["active"]: await reply("🛑 Бот остановлен."); return
    p = get_player(user.id, user.first_name); p["games_played"].add("croc")
    if chat_id in games and games[chat_id].get("timer_task"): games[chat_id]["timer_task"].cancel()
    cat = random.choice(list(WORDS.keys())); word = random.choice(WORDS[cat])
    games[chat_id] = {"word":word.lower(),"category":cat,"explainer_id":user.id,"explainer_name":user.first_name,"active":True,"timer_task":None}
    try:
        await ctx.bot.send_message(chat_id=user.id, text=f"🐊 Твоё слово: *{word.upper()}*\nКатегория: {cat}", parse_mode="Markdown")
        dm = f"✉️ Слово отправлено {user.first_name} в личку."
    except: dm = f"⚠️ {user.first_name}, напиши /start боту в личку!"
    await reply(f"🐊 *Крокодил!*\nОбъясняет: *{user.first_name}*\nКатегория: {cat}\n\n{dm}\n\n⏱ {ROUND_TIME_CROC} сек!", parse_mode="Markdown", reply_markup=make_croc_kb())
    task = asyncio.create_task(croc_timer(chat_id, ctx)); games[chat_id]["timer_task"] = task

async def cmd_game(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await start_croc(update.effective_chat.id, update.effective_user, ctx, update.message.reply_text)


async def wheel_timer(chat_id, ctx):
    await asyncio.sleep(ROUND_TIME_WHEEL)
    game = wheel_games.get(chat_id)
    if game and game.get("active"):
        game["active"] = False
        await ctx.bot.send_message(chat_id=chat_id, text=f"⏰ Время вышло!\nСлово: *{game['word'].upper()}*\n\n🎡 /wheel", parse_mode="Markdown")

async def start_wheel(chat_id, user, ctx, reply):
    if not bot_running["active"]: await reply("🛑 Бот остановлен."); return
    p = get_player(user.id, user.first_name); p["games_played"].add("wheel")
    if chat_id in wheel_games and wheel_games[chat_id].get("timer_task"): wheel_games[chat_id]["timer_task"].cancel()
    cat = random.choice(list(WORDS.keys())); word = random.choice(WORDS[cat]).lower()
    wheel_games[chat_id] = {"word":word,"category":cat,"guessed":set(),"wrong_letters":set(),"active":True,"round_scores":{},"drum_value":None,"timer_task":None,"sabotage_target":None}
    shown = display_word(word, set())
    await reply(f"🎡 *Поле чудес!*\nКатегория: {cat}\n\nСлово: `{shown}`\n\nБарабан → буква!\n❌ Буква:-100 | ❌ Слово:-150 | ✅ Слово:+500\n⏱ 5 мин!", parse_mode="Markdown", reply_markup=make_wheel_kb())
    task = asyncio.create_task(wheel_timer(chat_id, ctx)); wheel_games[chat_id]["timer_task"] = task

async def cmd_wheel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await start_wheel(update.effective_chat.id, update.effective_user, ctx, update.message.reply_text)


async def speedrun_timer(chat_id, ctx):
    await asyncio.sleep(SPEEDRUN_TIME)
    game = speed_games.get(chat_id)
    if game and game.get("active"):
        game["active"] = False; bonus = game["count"]*50
        add_score(game["player_id"], game["player_name"], bonus)
        await ctx.bot.send_message(chat_id=chat_id, text=f"⏰ *Спидран!*\n*{game['player_name']}* угадал(а) {game['count']} слов!\n+{bonus} оч\n\n📊 /scores", parse_mode="Markdown")

async def start_speedrun(chat_id, user, ctx, reply):
    p = get_player(user.id, user.first_name); p["games_played"].add("speedrun")
    if not p["speedrun_access"]: await reply("⚡ Купи в /shop за 750 оч!", parse_mode="Markdown"); return
    if chat_id in speed_games and speed_games[chat_id].get("active"): await reply("⚡ Спидран уже идёт!"); return
    word = random.choice(SPEEDRUN_WORDS)
    speed_games[chat_id] = {"word":word,"active":True,"player_id":user.id,"player_name":user.first_name,"count":0,"timer_task":None}
    await reply(f"⚡ *СПИДРАН!* {user.first_name}\n30 сек!\n\nПервое: `{'_ '*len(word)}`\nБукв: {len(word)}", parse_mode="Markdown")
    task = asyncio.create_task(speedrun_timer(chat_id, ctx)); speed_games[chat_id]["timer_task"] = task

async def cmd_speedrun(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await start_speedrun(update.effective_chat.id, update.effective_user, ctx, update.message.reply_text)


async def trivia_timer(chat_id, ctx):
    await asyncio.sleep(TRIVIA_TIME)
    game = trivia_games.get(chat_id)
    if game and game.get("active"):
        game["active"] = False
        await ctx.bot.send_message(chat_id=chat_id, text=f"⏰ Время вышло!\nОтвет: *{game['answer'].upper()}*\n\n🧠 /trivia", parse_mode="Markdown")

async def start_trivia_by_level(chat_id, user, ctx, reply, level):
    get_player(user.id, user.first_name)["games_played"].add("trivia")
    if chat_id in trivia_games and trivia_games[chat_id].get("timer_task"): trivia_games[chat_id]["timer_task"].cancel()
    if level == "easy": pool, pts, label = TRIVIA_EASY, 50, "🟢 Лёгкий"
    elif level == "hard": pool, pts, label = TRIVIA_HARD, 300, "🔴 Сложный"
    else: pool, pts, label = TRIVIA_MEDIUM, 150, "🟡 Средний"
    q = random.choice(pool)
    trivia_games[chat_id] = {"question":q["q"],"answer":q["a"],"pts":pts,"active":True,"timer_task":None}
    await reply(f"🧠 *Викторина!* {label}\n\n❓ {q['q']}\n\n⏱ {TRIVIA_TIME} сек | +{pts} очков", parse_mode="Markdown")
    task = asyncio.create_task(trivia_timer(chat_id, ctx)); trivia_games[chat_id]["timer_task"] = task

async def cmd_trivia(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🧠 *Викторина!*\n\nВыберите уровень сложности:", parse_mode="Markdown", reply_markup=make_trivia_kb())


async def hangman_timer(chat_id, ctx):
    await asyncio.sleep(HANGMAN_TIME)
    game = hangman_games.get(chat_id)
    if game and game.get("active"):
        game["active"] = False
        await ctx.bot.send_message(chat_id=chat_id, text=f"⏰ Время вышло!\nСлово: *{game['word'].upper()}*\n\n📝 /hangman", parse_mode="Markdown")

async def start_hangman(chat_id, user, ctx, reply):
    p = get_player(user.id, user.first_name); p["games_played"].add("hangman")
    if chat_id in hangman_games and hangman_games[chat_id].get("timer_task"): hangman_games[chat_id]["timer_task"].cancel()
    cat = random.choice(list(WORDS.keys())); word = random.choice(WORDS[cat]).lower()
    max_err = 7 if p.get("extra_life") else 6
    if p.get("extra_life"): p["extra_life"] = False
    hangman_games[chat_id] = {"word":word,"category":cat,"guessed":set(),"errors":0,"max_errors":max_err,"active":True,"timer_task":None}
    shown = display_word(word, set())
    await reply(f"📝 *Виселица!*\nКатегория: {cat}\n\n{HANGMAN_PICS[0]} Попыток: {max_err}\n\nСлово: `{shown}`\n\n+50 за букву, +200 за слово. ⏱ 2 мин!", parse_mode="Markdown")
    task = asyncio.create_task(hangman_timer(chat_id, ctx)); hangman_games[chat_id]["timer_task"] = task

async def cmd_hangman(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await start_hangman(update.effective_chat.id, update.effective_user, ctx, update.message.reply_text)


async def number_timer(chat_id, ctx):
    await asyncio.sleep(NUMBER_TIME)
    game = number_games.get(chat_id)
    if game and game.get("active"):
        game["active"] = False
        await ctx.bot.send_message(chat_id=chat_id, text=f"⏰ Время вышло!\nЧисло: *{game['number']}*\n\n🔢 /number", parse_mode="Markdown")

async def start_number(chat_id, user, ctx, reply):
    p = get_player(user.id, user.first_name); p["games_played"].add("number")
    extra = 30 if p.get("time_bonus") else 0
    if p.get("time_bonus"): p["time_bonus"] = False
    if chat_id in number_games and number_games[chat_id].get("timer_task"): number_games[chat_id]["timer_task"].cancel()
    number = random.randint(1, 100)
    number_games[chat_id] = {"number":number,"active":True,"attempts":{},"timer_task":None}
    await reply(f"🔢 *Угадай число!*\nОт *1 до 100*\n+100 оч | ⏱ {NUMBER_TIME+extra} сек!", parse_mode="Markdown")
    task = asyncio.create_task(number_timer(chat_id, ctx)); number_games[chat_id]["timer_task"] = task

async def cmd_number(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await start_number(update.effective_chat.id, update.effective_user, ctx, update.message.reply_text)


async def start_blackjack(chat_id, user, ctx, reply):
    p = get_player(user.id, user.first_name); p["games_played"].add("blackjack")
    if p["total_score"] < 50: await reply("🃏 Нужно 50 оч!", parse_mode="Markdown"); return
    hand = [deal_card(),deal_card()]; dealer = [deal_card(),deal_card()]
    blackjack_games[chat_id] = {"player_id":user.id,"player_name":user.first_name,"hand":hand,"dealer":dealer,"bet":50,"active":True}
    val = card_value(hand)
    await reply(f"🃏 *Блэкджек!*\n\nТвои: {hand_str(hand)}\nДилер: {dealer[0]} + ?\n\nСтавка: 50 оч\n{'🎉 БЛЭКДЖЕК!' if val==21 else 'Ещё или хватит?'}", parse_mode="Markdown", reply_markup=None if val==21 else make_bj_kb())
    if val == 21:
        p["total_score"] = max(0, p["total_score"]-50); add_score(user.id, user.first_name, 125); p["wins"] += 1
        p["achievements"].add("blackjack21"); blackjack_games[chat_id]["active"] = False
        await ctx.bot.send_message(chat_id=chat_id, text=f"🎉 *БЛЭКДЖЕК!* {user.first_name} +125 оч!\n🃏 /blackjack", parse_mode="Markdown")

async def cmd_blackjack(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await start_blackjack(update.effective_chat.id, update.effective_user, ctx, update.message.reply_text)


async def start_slots(chat_id, user, ctx, reply):
    p = get_player(user.id, user.first_name); p["games_played"].add("slots")
    if p["total_score"] < 100: await reply("🎰 Нужно 100 оч!", parse_mode="Markdown"); return
    p["total_score"] -= 100; symbols = spin_slots(); prize = check_slots(symbols)
    result = " | ".join(symbols)
    if prize > 0:
        add_score(user.id, user.first_name, prize); p["achievements"].add("lucky_slots")
        if prize >= 500: p["achievements"].add("mega_slots")
        msg = f"🎰 *{result}*\n\n🎉 ВЫИГРЫШ *+{prize}* оч!\nВсего: {p['total_score']}"
    else: msg = f"🎰 *{result}*\n\nНе повезло! -100 оч\nВсего: {p['total_score']}"
    await reply(msg, parse_mode="Markdown")

async def cmd_slots(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await start_slots(update.effective_chat.id, update.effective_user, ctx, update.message.reply_text)


async def start_tod(chat_id, user, ctx, reply):
    get_player(user.id, user.first_name)["games_played"].add("tod")
    choice = random.choice(["truth","dare"])
    if choice == "truth":
        await reply(f"❓ *Правда или Действие*\n\n*{user.first_name}* выбирает...\n\n🗣 *ПРАВДА:*\n{random.choice(TOD_TRUTHS)}", parse_mode="Markdown")
    else:
        await reply(f"❓ *Правда или Действие*\n\n*{user.first_name}* выбирает...\n\n🎯 *ДЕЙСТВИЕ:*\n{random.choice(TOD_DARES)}", parse_mode="Markdown")

async def cmd_tod(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await start_tod(update.effective_chat.id, update.effective_user, ctx, update.message.reply_text)


async def cmd_duel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id; user = update.effective_user
    p = get_player(user.id, user.first_name); p["games_played"].add("duel")
    if p["total_score"] < 100: await update.message.reply_text("⚔️ Нужно 100 оч!", parse_mode="Markdown"); return
    if update.message.reply_to_message:
        opp = update.message.reply_to_message.from_user
        if opp.id == user.id: await update.message.reply_text("Нельзя драться с собой 😄", parse_mode="Markdown"); return
        duel_games[chat_id] = {"challenger_id":user.id,"challenger_name":user.first_name,"opponent_id":opp.id,"opponent_name":opp.first_name,"active":True}
        await update.message.reply_text(f"⚔️ *{user.first_name}* вызывает *{opp.first_name}*!\nСтавка: 100 оч\n*{opp.first_name}*, принимаешь?", parse_mode="Markdown", reply_markup=make_duel_kb(user.id))
    else: await update.message.reply_text("⚔️ Ответь на сообщение игрока и напиши /duel", parse_mode="Markdown")


async def start_roulette(chat_id, user, ctx, reply):
    p = get_player(user.id, user.first_name); p["games_played"].add("roulette")
    if p["total_score"] < 100: await reply("🎯 Нужно 100 оч!", parse_mode="Markdown"); return
    roulette_games[chat_id] = {"player_id":user.id,"player_name":user.first_name,"active":True}
    await reply(f"🎯 *Рулетка!*\n\n*{user.first_name}* ставит 100 оч!\n\n🔴 Красное +100 | ⚫ Чёрное +100 | 🟢 Зеро +350\n\nВыберите:", parse_mode="Markdown", reply_markup=make_roulette_kb())

async def cmd_roulette(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await start_roulette(update.effective_chat.id, update.effective_user, ctx, update.message.reply_text)


async def start_dice(chat_id, user, ctx, reply):
    p = get_player(user.id, user.first_name); p["games_played"].add("dice")
    dice_games[chat_id] = {"player_id":user.id,"player_name":user.first_name,"active":True}
    await reply(f"🎲 *Кубик удачи!*\n\n*{user.first_name}*\n6 = +200 оч | 1 = -50 оч | Остальное = 0", parse_mode="Markdown", reply_markup=make_dice_kb())

async def cmd_dice(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await start_dice(update.effective_chat.id, update.effective_user, ctx, update.message.reply_text)


# ─── УНО ──────────────────────────────────────────────────────────────────────
async def uno_turn_timer(chat_id, ctx):
    await asyncio.sleep(UNO_TURN_TIME)
    game = uno_games.get(chat_id)
    if not game or not game.get("active"): return
    current_idx = game["current"]
    players_list = game["players"]
    if not players_list: return
    skipped_name = players_list[current_idx % len(players_list)][1]
    game["current"] = (current_idx + 1) % len(players_list)
    next_name = players_list[game["current"] % len(players_list)][1]
    await ctx.bot.send_message(chat_id=chat_id,
        text=f"⏰ *{skipped_name}* пропустил(а) ход!\n\nХодит: *{next_name}*\nВерхняя карта: {game['top_card']}\n\nНапишите карту или /uno_draw",
        parse_mode="Markdown")

async def start_uno(chat_id, user, ctx, reply):
    p = get_player(user.id, user.first_name); p["games_played"].add("uno")
    if chat_id in uno_games and uno_games[chat_id].get("active"):
        game = uno_games[chat_id]
        if user.id not in [pid for pid,_ in game["players"]]:
            game["players"].append((user.id, user.first_name))
            deck = make_uno_deck()
            game["hands"][user.id] = [deck.pop() for _ in range(7)]
            game["deck"].extend(deck)
            await reply(f"✋ *{user.first_name}* присоединяется к УНО!\n\nИгроков: {len(game['players'])}", parse_mode="Markdown")
        else: await reply("Ты уже в игре УНО!", parse_mode="Markdown")
        return
    deck = make_uno_deck()
    hand = [deck.pop() for _ in range(7)]
    top = deck.pop()
    uno_games[chat_id] = {
        "active":True,"players":[(user.id, user.first_name)],"current":0,
        "deck":deck,"hands":{user.id:hand},"top_card":top,
        "direction":1,"timer_task":None,"skip_next":False,"draw_next":0
    }
    try:
        await ctx.bot.send_message(chat_id=user.id, text=f"🎴 *Твои карты УНО:*\n\n{' '.join(hand)}", parse_mode="Markdown")
        hand_info = "Карты отправлены в личку."
    except: hand_info = "Напиши боту /start в личку чтобы видеть карты!"
    await reply(f"🎴 *УНО!*\n\n*{user.first_name}* создаёт игру!\n{hand_info}\n\nВерхняя карта: *{top}*\n\nПиши /uno чтобы присоединиться!\nКогда все готовы — пиши карту из своей руки.", parse_mode="Markdown")

async def cmd_uno(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await start_uno(update.effective_chat.id, update.effective_user, ctx, update.message.reply_text)


async def start_poker(chat_id, user, ctx, reply):
    p = get_player(user.id, user.first_name); p["games_played"].add("poker")
    if p["total_score"] < 100: await reply("♠️ Нужно 100 оч!", parse_mode="Markdown"); return
    hand = [deal_card(),deal_card(),deal_card(),deal_card(),deal_card()]
    ctx.chat_data["poker_hand"] = hand
    ctx.chat_data["poker_player"] = (user.id, user.first_name)
    await reply(f"♠️ *Покер!*\n\nТвои карты: {' '.join(hand)}\nСтавка: 100 оч\n\nПродолжить или сбросить?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Продолжить",callback_data="poker_continue"),InlineKeyboardButton("❌ Сбросить",callback_data="poker_fold")]]))

async def cmd_poker(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await start_poker(update.effective_chat.id, update.effective_user, ctx, update.message.reply_text)


async def cmd_tournament(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id; user = update.effective_user
    t = tournaments.get(chat_id)
    if t and t.get("active") and user.id in t["players"] and len(t["players"]) >= 2:
        players_list = list(t["players"].items()); random.shuffle(players_list)
        winner_id, winner_name = players_list[0]
        add_score(winner_id, winner_name, 500); tournaments[chat_id]["active"] = False
        names = "\n".join([f"{i+1}. {n}" for i,(uid,n) in enumerate(players_list)])
        await update.message.reply_text(f"🏆 *ТУРНИР ЗАВЕРШЁН!*\n\nУчастники:\n{names}\n\n🥇 Победитель: *{winner_name}*!\n+500 очков!", parse_mode="Markdown")
    else:
        get_player(user.id, user.first_name)["games_played"].add("tournament")
        if not t or not t.get("active"):
            tournaments[chat_id] = {"active":True,"players":{user.id:user.first_name}}
            await update.message.reply_text(f"🏆 *Турнир открыт!*\n\n*{user.first_name}* создаёт турнир!\n\nПиши /tournament чтобы записаться!\nМинимум 2 игрока.", parse_mode="Markdown")
        else:
            if user.id not in t["players"]:
                t["players"][user.id] = user.first_name
                names = ", ".join(t["players"].values())
                await update.message.reply_text(f"✋ *{user.first_name}* записался в турнир!\n\nУчастников: {len(t['players'])}: {names}\n\nЛюбой участник пишет /tournament ещё раз чтобы запустить!", parse_mode="Markdown")
            else: await update.message.reply_text("Ты уже в турнире! Напиши /tournament ещё раз чтобы запустить.", parse_mode="Markdown")


# ══════════════════════════════════════════════════════════════════════════════
# CALLBACK
# ══════════════════════════════════════════════════════════════════════════════
async def callback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    chat_id = update.effective_chat.id; user = update.effective_user
    data = query.data; p = get_player(user.id, user.first_name)
    g = is_group(update.effective_chat)

    async def reply(text, **kwargs):
        await ctx.bot.send_message(chat_id=chat_id, text=text, **kwargs)

    # ── Меню ──
    if data=="menu_game": await start_croc(chat_id,user,ctx,reply)
    elif data=="menu_wheel": await start_wheel(chat_id,user,ctx,reply)
    elif data=="menu_speedrun": await start_speedrun(chat_id,user,ctx,reply)
    elif data=="menu_trivia": await reply("🧠 *Викторина!*\n\nВыберите уровень:", parse_mode="Markdown", reply_markup=make_trivia_kb())
    elif data=="menu_hangman": await start_hangman(chat_id,user,ctx,reply)
    elif data=="menu_number": await start_number(chat_id,user,ctx,reply)
    elif data=="menu_blackjack": await start_blackjack(chat_id,user,ctx,reply)
    elif data=="menu_slots": await start_slots(chat_id,user,ctx,reply)
    elif data=="menu_tod": await start_tod(chat_id,user,ctx,reply)
    elif data=="menu_roulette": await start_roulette(chat_id,user,ctx,reply)
    elif data=="menu_dice": await start_dice(chat_id,user,ctx,reply)
    elif data=="menu_uno": await start_uno(chat_id,user,ctx,reply)
    elif data=="menu_poker": await start_poker(chat_id,user,ctx,reply)
    elif data=="menu_tournament":
        get_player(user.id,user.first_name)["games_played"].add("tournament")
        t = tournaments.get(chat_id)
        if not t or not t.get("active"):
            tournaments[chat_id]={"active":True,"players":{user.id:user.first_name}}
            await reply(f"🏆 *Турнир открыт!*\n*{user.first_name}* создаёт турнир!\n\nНажимайте кнопку Присоединиться и пишите /tournament!", parse_mode="Markdown")
        else:
            if user.id not in t["players"]: t["players"][user.id]=user.first_name
            names=", ".join(t["players"].values())
            await reply(f"🏆 Ты в турнире! Участников: {len(t['players'])}\n{names}", parse_mode="Markdown")
    elif data=="menu_duel": await reply("⚔️ Ответь на сообщение игрока и напиши /duel", parse_mode="Markdown")
    elif data=="menu_scores": await reply(f"📊 *Таблица очков*\n\n{global_scores_text()}", parse_mode="Markdown")
    elif data=="menu_shop": await reply(f"🛒 *Магазин* 🔥СКИДКИ!\n\nТвои очки: *{p['total_score']}*", parse_mode="Markdown", reply_markup=make_shop_keyboard(p))
    elif data=="menu_achievements":
        unlocked = sum(1 for k in ACHIEVEMENTS if k in p["achievements"])
        lines=[f"{'✅' if k in p['achievements'] else '🔒'} {v[0]} {v[1]}" for k,v in ACHIEVEMENTS.items()]
        await reply(f"🏆 *Достижения* ({unlocked}/{len(ACHIEVEMENTS)})\n\n"+"\n".join(lines), parse_mode="Markdown")
    elif data=="menu_profile":
        title=get_title(p["total_score"])
        await reply(f"👤 *{get_nick(user.id,user.first_name)}*\n\n🏅 {title}\n💰 {p['total_score']} оч | 🏆 {p['wins']} побед\n🎮 Игр: {len(p['games_played'])}", parse_mode="Markdown")
    elif data=="menu_inventory":
        inv={k:v for k,v in p.get("inventory",{}).items() if v>0}
        if not inv: await reply("🎒 Инвентарь пуст! Купи в /shop", parse_mode="Markdown")
        else:
            lines=[f"{SHOP_ITEMS[k][0]} *{SHOP_ITEMS[k][1]}* x{v}" for k,v in inv.items() if k in SHOP_ITEMS]
            await reply("🎒 *Инвентарь*\n\n"+"\n".join(lines), parse_mode="Markdown")
    elif data=="menu_daily":
        today=date.today().isoformat()
        if p.get("last_daily")==today: await query.answer("Уже получил сегодня!",show_alert=True); return
        bonus=random.randint(50,300)
        if p.get("double_daily"): bonus*=2; p["double_daily"]=False
        p["last_daily"]=today; add_score(user.id,user.first_name,bonus)
        await reply(f"🎁 *{user.first_name}* +*{bonus}* очков!\n💰 Всего: {p['total_score']}", parse_mode="Markdown")
    elif data=="menu_join":
        if chat_id not in group_players: group_players[chat_id]={}
        if user.id in group_players[chat_id]: await query.answer("Ты уже в игре!",show_alert=True); return
        group_players[chat_id][user.id]=user.first_name
        names=", ".join(group_players[chat_id].values())
        await reply(f"✋ *{user.first_name}* присоединился(ась)!\n👥 {names}", parse_mode="Markdown")
    elif data=="menu_back": await query.edit_message_reply_markup(reply_markup=make_main_keyboard(group=g))
    elif data=="shop_info": await query.answer("ℹ️ Информация о предметах", show_alert=False)

    # ── Стоп бот ──
    elif data=="admin_stop":
        if ADMIN_IDS and user.id not in ADMIN_IDS: await query.answer("Нет доступа!",show_alert=True); return
        bot_running["active"] = False
        await query.edit_message_text("🛑 *Бот остановлен администратором!*\n\nВсе игры завершены.", parse_mode="Markdown")

    # ── Викторина уровни ──
    elif data in ("trivia_easy","trivia_medium","trivia_hard"):
        level = data.split("_")[1]
        await start_trivia_by_level(chat_id, user, ctx, reply, level)

    # ── Крокодил ──
    elif data=="croc_skip":
        game=games.get(chat_id)
        if not game or not game.get("active"): return
        if user.id!=game["explainer_id"]: await query.answer("Только объясняющий!",show_alert=True); return
        if game["timer_task"]: game["timer_task"].cancel()
        old=game["word"]; cat=random.choice(list(WORDS.keys())); word=random.choice(WORDS[cat])
        game["word"]=word.lower(); game["category"]=cat
        try: await ctx.bot.send_message(chat_id=user.id, text=f"⏭ Новое: *{word.upper()}*", parse_mode="Markdown")
        except: pass
        await query.edit_message_text(f"⏭ Пропущено (было: *{old}*).\nКатегория: {cat}\n⏱ {ROUND_TIME_CROC} сек!", parse_mode="Markdown", reply_markup=make_croc_kb())
        task=asyncio.create_task(croc_timer(chat_id,ctx)); game["timer_task"]=task

    elif data=="croc_stop":
        game=games.get(chat_id)
        if not game or not game.get("active"): return
        if user.id!=game["explainer_id"]: await query.answer("Только объясняющий!",show_alert=True); return
        if game["timer_task"]: game["timer_task"].cancel()
        game["active"]=False
        await query.edit_message_text(f"🛑 Стоп.\nСлово: *{game['word'].upper()}*\n\n▶️ /game", parse_mode="Markdown")

    # ── Поле чудес ──
    elif data=="wheel_spin":
        game=wheel_games.get(chat_id)
        if not game or not game.get("active"): return
        result=spin_drum()
        if result=="БАНКРОТ":
            if p["protection"]: p["protection"]=False; game["drum_value"]=100; await reply(f"🛡 *{user.first_name}* защитился! Барабан: 100\nНазови букву:", parse_mode="Markdown")
            else: game["round_scores"][user.id]=0; game["drum_value"]=None; await reply(f"💸 *БАНКРОТ!* {user.first_name}!\n\nСлово: `{display_word(game['word'],game['guessed'])}`", parse_mode="Markdown", reply_markup=make_wheel_kb())
        elif result=="ПРИЗ":
            bonus=random.choice([300,500,700]); game["round_scores"][user.id]=game["round_scores"].get(user.id,0)+bonus; game["drum_value"]=None
            await reply(f"🎁 *ПРИЗ!* {user.first_name} +{bonus}!\n\nСлово: `{display_word(game['word'],game['guessed'])}`", parse_mode="Markdown", reply_markup=make_wheel_kb())
        elif result=="x2": game["drum_value"]="x2"; await reply(f"✨ *x2!* {user.first_name}\nНазови букву:", parse_mode="Markdown")
        elif result=="ДЖЕКПОТ":
            jackpot=random.randint(500,2000); game["round_scores"][user.id]=game["round_scores"].get(user.id,0)+jackpot; game["drum_value"]=None
            p["achievements"].add("jackpot"); await reply(f"💥 *ДЖЕКПОТ!* {user.first_name} +{jackpot}!!!\n\nСлово: `{display_word(game['word'],game['guessed'])}`", parse_mode="Markdown", reply_markup=make_wheel_kb())
        else: game["drum_value"]=result; await reply(f"🎡 *{user.first_name}* крутит: *{result}* оч!\nНазови букву:", parse_mode="Markdown")

    elif data=="wheel_stop":
        game=wheel_games.get(chat_id)
        if not game or not game.get("active"): return
        if game["timer_task"]: game["timer_task"].cancel()
        game["active"]=False
        await query.edit_message_text(f"🛑 Стоп.\nСлово: *{game['word'].upper()}*\n\n🎡 /wheel", parse_mode="Markdown")

    # ── Блэкджек ──
    elif data=="bj_hit":
        game=blackjack_games.get(chat_id)
        if not game or not game.get("active"): return
        if user.id!=game["player_id"]: await query.answer("Не твоя!",show_alert=True); return
        game["hand"].append(deal_card()); val=card_value(game["hand"])
        if val>21:
            game["active"]=False; p["total_score"]=max(0,p["total_score"]-50)
            await query.edit_message_text(f"🃏 {hand_str(game['hand'])}\n\n💥 *Перебор!* -50 оч\nВсего: {p['total_score']}\n\n🃏 /blackjack", parse_mode="Markdown")
        else: await query.edit_message_text(f"🃏 {hand_str(game['hand'])}\nДилер: {game['dealer'][0]} + ?\n\nЕщё или хватит?", parse_mode="Markdown", reply_markup=make_bj_kb())

    elif data=="bj_stand":
        game=blackjack_games.get(chat_id)
        if not game or not game.get("active"): return
        if user.id!=game["player_id"]: await query.answer("Не твоя!",show_alert=True); return
        game["active"]=False; dealer=game["dealer"]
        while card_value(dealer)<17: dealer.append(deal_card())
        pval=card_value(game["hand"]); dval=card_value(dealer)
        p["total_score"]=max(0,p["total_score"]-50)
        if dval>21 or pval>dval: add_score(user.id,user.first_name,100); p["wins"]+=1; result="🎉 *Победа!* +100 оч"
        elif pval==dval: add_score(user.id,user.first_name,50); result="🤝 *Ничья!* +50 оч"
        else: result="😔 *Дилер победил!* -50 оч"
        await query.edit_message_text(f"🃏 Ты: {hand_str(game['hand'])}\nДилер: {hand_str(dealer)}\n\n{result}\nВсего: {p['total_score']}\n\n🃏 /blackjack", parse_mode="Markdown")

    # ── Дуэль ──
    elif data.startswith("duel_accept_"):
        cid=int(data.split("_")[2]); game=duel_games.get(chat_id)
        if not game or not game.get("active"): return
        if user.id!=game["opponent_id"]: await query.answer("Не твоя!",show_alert=True); return
        game["active"]=False
        cp=get_player(cid,game["challenger_name"]); op=p
        if cp["total_score"]<100 or op["total_score"]<100: await query.edit_message_text("❌ Не хватает очков!"); return
        # Проверяем зеркало и щиты
        wname=random.choice([game["challenger_name"],game["opponent_name"]])
        lname=game["opponent_name"] if wname==game["challenger_name"] else game["challenger_name"]
        wid=cid if wname==game["challenger_name"] else user.id
        lid=user.id if wname==game["challenger_name"] else cid
        add_score(wid,wname,100); get_player(lid,lname)["total_score"]=max(0,get_player(lid,lname)["total_score"]-100)
        get_player(wid,wname)["wins"]+=1; get_player(wid,wname)["duel_wins"]=get_player(wid,wname).get("duel_wins",0)+1
        check_achievements(wid,wname)
        await query.edit_message_text(f"⚔️ *ДУЭЛЬ!*\n\n🎯 {game['challenger_name']} vs {game['opponent_name']}\n\n🏆 *{wname}* победил! +100\n😔 *{lname}* -100\n\n📊 {global_scores_text()}", parse_mode="Markdown")

    elif data=="duel_decline":
        if chat_id in duel_games: duel_games[chat_id]["active"]=False
        await query.edit_message_text("❌ Дуэль отклонена.", parse_mode="Markdown")

    # ── Рулетка ──
    elif data in ("rou_red","rou_black","rou_zero"):
        game=roulette_games.get(chat_id)
        if not game or not game.get("active"): return
        if user.id!=game["player_id"]: await query.answer("Не твоя!",show_alert=True); return
        if p["total_score"]<100: await query.answer("Недостаточно!",show_alert=True); return
        game["active"]=False; p["total_score"]=max(0,p["total_score"]-100)
        number=random.randint(0,36)
        if number==0: actual="🟢 Зеро"
        elif number%2==0: actual="⚫ Чёрное"
        else: actual="🔴 Красное"
        bet_map={"rou_red":"🔴 Красное","rou_black":"⚫ Чёрное","rou_zero":"🟢 Зеро"}
        bet=bet_map[data]
        if bet==actual:
            prize=350 if data=="rou_zero" else 100; add_score(user.id,user.first_name,prize); p["wins"]+=1; p["achievements"].add("roulette_win")
            await query.edit_message_text(f"🎯 Выпало: {actual} ({number})\nСтавка: {bet}\n\n🎉 *+{prize} очков!*\nВсего: {p['total_score']}", parse_mode="Markdown")
        else: await query.edit_message_text(f"🎯 Выпало: {actual} ({number})\nСтавка: {bet}\n\n😔 Не угадал! -100\nВсего: {p['total_score']}\n\n🎯 /roulette", parse_mode="Markdown")

    # ── Кубик ──
    elif data=="dice_roll":
        game=dice_games.get(chat_id)
        if not game or not game.get("active"): return
        if user.id!=game["player_id"]: await query.answer("Не твоя!",show_alert=True); return
        game["active"]=False; val=random.randint(1,6)
        faces=["","⚀","⚁","⚂","⚃","⚄","⚅"]
        if val==6: add_score(user.id,user.first_name,200); p["wins"]+=1; result="🎉 *ШЕСТЁРКА!* +200!"
        elif val==1: p["total_score"]=max(0,p["total_score"]-50); result="😔 *Единица!* -50!"
        else: result=f"🤷 *{val}* — ничего. Попробуй ещё!"
        await query.edit_message_text(f"🎲 {faces[val]} Выпало: *{val}*\n\n{result}\nВсего: {p['total_score']}\n\n🎲 /dice", parse_mode="Markdown")

    # ── Покер ──
    elif data=="poker_continue":
        hand=ctx.chat_data.get("poker_hand",[])
        if not hand: await query.edit_message_text("Ошибка! /poker заново."); return
        pid,pname=ctx.chat_data.get("poker_player",(user.id,user.first_name))
        pp=get_player(pid,pname); pp["total_score"]=max(0,pp["total_score"]-100)
        val=card_value(hand[:2]); dealer_hand=[deal_card(),deal_card(),deal_card(),deal_card(),deal_card()]; dval=card_value(dealer_hand[:2])
        if val>dval or val==21: add_score(pid,pname,200); pp["wins"]+=1; pp["achievements"].add("poker_win"); result="🎉 *Победа!* +200 оч"
        elif val==dval: add_score(pid,pname,100); result="🤝 *Ничья!* +100 оч"
        else: result="😔 *Дилер победил!* -100 оч"
        await query.edit_message_text(f"♠️ Ты: {' '.join(hand)}\nДилер: {' '.join(dealer_hand)}\n\n{result}\nВсего: {pp['total_score']}\n\n♠️ /poker", parse_mode="Markdown")

    elif data=="poker_fold":
        p["total_score"]=max(0,p["total_score"]-50)
        await query.edit_message_text(f"♠️ Сбросил карты. -50 оч\nВсего: {p['total_score']}\n\n♠️ /poker", parse_mode="Markdown")

    # ── УНО ──
    elif data=="uno_draw":
        game=uno_games.get(chat_id)
        if not game or not game.get("active"): return
        current_player_id = game["players"][game["current"] % len(game["players"])][0]
        if user.id != current_player_id: await query.answer("Сейчас не твой ход!",show_alert=True); return
        if not game["deck"]: game["deck"] = make_uno_deck()
        card = game["deck"].pop()
        game["hands"].setdefault(user.id,[]).append(card)
        try: await ctx.bot.send_message(chat_id=user.id, text=f"🃏 Взял карту: *{card}*\n\nТвои карты: {' '.join(game['hands'][user.id])}", parse_mode="Markdown")
        except: pass
        await reply(f"🃏 *{user.first_name}* берёт карту.\n\nВерхняя: {game['top_card']}", parse_mode="Markdown")

    elif data=="uno_show":
        game=uno_games.get(chat_id)
        if not game or not game.get("active"): return
        hand=game["hands"].get(user.id,[])
        try: await ctx.bot.send_message(chat_id=user.id, text=f"🃏 *Твои карты:*\n\n{' '.join(hand) if hand else 'Нет карт!'}", parse_mode="Markdown")
        except: await query.answer("Напиши /start боту в личку чтобы видеть карты!",show_alert=True)

    # ── Магазин ──
    elif data.startswith("shop_"):
        key=data[5:]
        if key=="info": await query.answer("ℹ️ Выбери предмет для покупки"); return
        if key not in SHOP_ITEMS: return
        icon,name,desc,orig_price=SHOP_ITEMS[key]
        price = shop_price(key)
        if p["total_score"]<price: await query.answer(f"Нужно {price} оч! У тебя {p['total_score']}",show_alert=True); return
        p["shop_purchases"] = p.get("shop_purchases",0) + 1
        check_achievements(user.id, user.first_name)

        if key=="vip":
            if p["vip"]: await query.answer("Уже есть!",show_alert=True); return
            p["total_score"]-=price; p["vip"]=True; p["achievements"].add("vip_buyer")
            await reply(f"👑 *{user.first_name}* получает VIP статус!", parse_mode="Markdown")
        elif key=="speedrun":
            if p["speedrun_access"]: await query.answer("Уже есть!",show_alert=True); return
            p["total_score"]-=price; p["speedrun_access"]=True; p["achievements"].add("speedrunner")
            await reply(f"⚡ *{user.first_name}* открыл Спидран!\n/speedrun", parse_mode="Markdown")
        elif key=="hint":
            game=wheel_games.get(chat_id)
            if not game or not game.get("active"): await query.answer("Нет активного Поля чудес!",show_alert=True); return
            hidden=[c for c in game["word"] if c not in game["guessed"] and c!=" "]
            if not hidden: await query.answer("Все буквы открыты!",show_alert=True); return
            letter=random.choice(hidden); game["guessed"].add(letter); p["total_score"]-=price
            await reply(f"💡 *{user.first_name}* открывает *{letter.upper()}* (-{price})\n\nСлово: `{display_word(game['word'],game['guessed'])}`", parse_mode="Markdown", reply_markup=make_wheel_kb())
        elif key=="protection": p["total_score"]-=price; p["protection"]=True; await query.answer("🛡 Защита!",show_alert=True)
        elif key=="double": p["total_score"]-=price; p["double"]=True; await query.answer("🎯 Удвоение!",show_alert=True)
        elif key=="sabotage":
            game=wheel_games.get(chat_id)
            if not game or not game.get("active"): await query.answer("Нет Поля чудес!",show_alert=True); return
            p["total_score"]-=price
            other=[uid for uid in game["round_scores"] if uid!=user.id]
            if other:
                target=random.choice(other); game["sabotage_target"]=target
                tname=players.get(target,{}).get("name","игрок")
                await reply(f"💣 *{user.first_name}* — диверсия против *{tname}*!", parse_mode="Markdown")
            else: await query.answer("Нет других игроков!",show_alert=True)
        elif key=="extra_life": p["total_score"]-=price; p["extra_life"]=True; await query.answer("❤️ Доп. жизнь!",show_alert=True)
        elif key=="time_bonus": p["total_score"]-=price; p["time_bonus"]=True; await query.answer("⏱ +30 сек!",show_alert=True)
        elif key=="double_daily": p["total_score"]-=price; p["double_daily"]=True; await query.answer("🎁 Следующий бонус x2!",show_alert=True)
        elif key=="score_boost": p["total_score"]-=price; p["score_boost"]=True; await query.answer("⚡ Бустер x1.5!",show_alert=True)
        elif key=="multiplier": p["total_score"]-=price; p["multiplier"]=True; await query.answer("✖️ x3 к победе!",show_alert=True)
        elif key=="lottery":
            p["total_score"]-=price; prize=random.randint(50,500); add_score(user.id,user.first_name,prize)
            await reply(f"🎟 *{user.first_name}* — лотерея!\n\n🎉 Выигрыш: *+{prize}* оч!\nВсего: {p['total_score']}", parse_mode="Markdown")
        elif key=="poison":
            victims=[uid for uid in players if uid!=user.id and players[uid]["total_score"]>0]
            if not victims: await query.answer("Нет игроков!",show_alert=True); return
            p["total_score"]-=price; target=random.choice(victims); tname=players[target]["name"]
            today=date.today().isoformat()
            if players[target].get("shield_until") and today<=players[target]["shield_until"]:
                if players[target].get("mirror"):
                    players[target]["mirror"]=False; p["total_score"]=max(0,p["total_score"]-200)
                    await reply(f"🪞 *Зеркало!* Яд отражён обратно на *{user.first_name}*!", parse_mode="Markdown")
                else: await reply(f"🧪 Яд отражён щитом *{tname}*!", parse_mode="Markdown")
            else:
                players[target]["total_score"]=max(0,players[target]["total_score"]-200)
                await reply(f"🧪 *{user.first_name}* использует яд на *{tname}*!\n*{tname}* теряет 200 оч!", parse_mode="Markdown")
        elif key=="skip_pass":
            p["total_score"]-=price; p.setdefault("inventory",{})["skip_pass"]=p.get("inventory",{}).get("skip_pass",0)+1
            await query.answer("⏩ Скип-пас в инвентаре!",show_alert=True)
        elif key=="fortune":
            p["total_score"]-=price
            hints=["🔥 Следующая буква есть в слове (угадай)!","💀 Одна из: А Е И О У — нет в слове!","⭐ В слове больше 5 букв!","🌙 Первая буква — согласная!","✨ В слове есть двойная буква!","🎯 Слово из категории животных или еды!"]
            await reply(f"🔮 *Фортуна говорит:*\n\n{random.choice(hints)}", parse_mode="Markdown")
        elif key=="crown":
            p["total_score"]-=price; p["crown_until"]=(date.today()+timedelta(days=1)).isoformat()
            await reply(f"💎 *{user.first_name}* получает корону на 24 часа!", parse_mode="Markdown")
        elif key in ("color_red","color_blue","color_green","color_purple","color_gold","color_rainbow"):
            colors={"color_red":"🔴","color_blue":"🔵","color_green":"🟢","color_purple":"🟣","color_gold":"🟡","color_rainbow":"🌈"}
            p["total_score"]-=price; p["nick_color"]=colors[key]
            await reply(f"{colors[key]} *{user.first_name}* меняет цвет ника!", parse_mode="Markdown")
        elif key=="shield":
            p["total_score"]-=price; p["shield_until"]=(date.today()+timedelta(days=1)).isoformat()
            await query.answer("🛡 Щит на 24 часа!",show_alert=True)
        elif key=="mystery_box":
            p["total_score"]-=price
            available=[k for k in SHOP_ITEMS if k not in ("mystery_box","vip","speedrun","vip_pack")]
            pk=random.choice(available); pi,pn,_,_=SHOP_ITEMS[pk]
            p.setdefault("inventory",{})[pk]=p.get("inventory",{}).get(pk,0)+1
            await reply(f"📦 *{user.first_name}* открывает тайный ящик!\n\n🎉 Выпало: {pi} *{pn}*!", parse_mode="Markdown")
        elif key=="booster_top":
            p["total_score"]-=price
            await reply(f"🚀 *{user.first_name}* врывается в топ!\n\n📊 {global_scores_text()}", parse_mode="Markdown")
        elif key=="steal":
            victims=[uid for uid in players if uid!=user.id and players[uid]["total_score"]>=50]
            if not victims: await query.answer("Нет богатых игроков!",show_alert=True); return
            p["total_score"]-=price; target=random.choice(victims); tname=players[target]["name"]
            today=date.today().isoformat()
            if players[target].get("shield_until") and today<=players[target]["shield_until"]:
                await reply(f"🛡 *{tname}* защищён щитом! Кража не удалась.", parse_mode="Markdown")
            else:
                stolen=random.randint(100,300); players[target]["total_score"]=max(0,players[target]["total_score"]-stolen)
                add_score(user.id,user.first_name,stolen)
                await reply(f"💰 *{user.first_name}* ограбил *{tname}*!\nУкрадено: {stolen} оч!", parse_mode="Markdown")
        elif key=="freeze":
            victims=[uid for uid in players if uid!=user.id]
            if not victims: await query.answer("Нет игроков!",show_alert=True); return
            p["total_score"]-=price; target=random.choice(victims); tname=players[target]["name"]
            players[target]["frozen_until"]=(date.today()+timedelta(days=1)).isoformat()
            await reply(f"❄️ *{user.first_name}* замораживает *{tname}* на 24 часа!", parse_mode="Markdown")
        elif key=="mirror": p["total_score"]-=price; p["mirror"]=True; await query.answer("🪞 Зеркало активировано!",show_alert=True)
        elif key=="sale_pack":
            if p["total_score"]<price: await query.answer(f"Нужно {price}!",show_alert=True); return
            p["total_score"]-=price; p["protection"]=True; p["double"]=True; p["extra_life"]=True
            await reply(f"🎉 *{user.first_name}* купил пакет скидок!\n\n🛡 Защита + 🎯 Удвоение + ❤️ Жизнь активированы!", parse_mode="Markdown")
        elif key=="starter_pack":
            if p["total_score"]<price: await query.answer(f"Нужно {price}!",show_alert=True); return
            p["total_score"]-=price
            for _ in range(3): p.setdefault("inventory",{})["lottery"]=p.get("inventory",{}).get("lottery",0)+1
            p["score_boost"]=True
            await reply(f"🎯 *{user.first_name}* купил стартовый пакет!\n\n🎟 Лотерея x3 + ⚡ Бустер активированы!", parse_mode="Markdown")
        elif key=="vip_pack":
            if p["total_score"]<price: await query.answer(f"Нужно {price}!",show_alert=True); return
            p["total_score"]-=price; p["vip"]=True; p["achievements"].add("vip_buyer")
            p["crown_until"]=(date.today()+timedelta(days=1)).isoformat(); p["nick_color"]="🌈"
            await reply(f"👑 *{user.first_name}* купил VIP Пакет!\n\n👑 VIP + 💎 Корона + 🌈 Радужный ник активированы!", parse_mode="Markdown")


# ══════════════════════════════════════════════════════════════════════════════
# MESSAGE ROUTER
# ══════════════════════════════════════════════════════════════════════════════
async def message_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not bot_running["active"]: return
    chat_id = update.effective_chat.id; user = update.effective_user
    p = get_player(user.id, user.first_name)
    text = (update.message.text or "").strip().lower()
    g = is_group(update.effective_chat)

    # Проверка заморозки
    if is_frozen(user.id):
        return

    # ── УНО ──
    if chat_id in uno_games and uno_games[chat_id].get("active"):
        game = uno_games[chat_id]
        if not game["players"]: return
        current_player_id = game["players"][game["current"] % len(game["players"])][0]
        if user.id != current_player_id: return
        hand = game["hands"].get(user.id, [])
        # Проверяем можно ли сыграть карту
        raw_text = (update.message.text or "").strip()
        if raw_text in hand:
            card = raw_text; top = game["top_card"]
            if uno_card_matches(card, top):
                hand.remove(card); game["top_card"] = card
                if not hand:
                    game["active"] = False; add_score(user.id, user.first_name, 300); p["wins"] += 1
                    p["achievements"].add("uno_win")
                    await update.message.reply_text(f"🎴 *УНО! {user.first_name} выиграл(а)!*\n\n+300 очков!\n\n📊 {global_scores_text()}", parse_mode="Markdown", reply_markup=make_main_keyboard(group=g))
                else:
                    # Спец карты
                    skip_next = "⛔" in card
                    draw_next = 2 if "➕2" in card else (4 if "➕4" in card else 0)
                    next_idx = (game["current"] + game["direction"]) % len(game["players"])
                    if skip_next: next_idx = (next_idx + game["direction"]) % len(game["players"])
                    if "🔄" in card: game["direction"] *= -1
                    if draw_next > 0:
                        next_player_id = game["players"][next_idx][0]
                        for _ in range(draw_next):
                            if game["deck"]: game["hands"].setdefault(next_player_id,[]).append(game["deck"].pop())
                    game["current"] = next_idx
                    next_name = game["players"][game["current"] % len(game["players"])][1]
                    await update.message.reply_text(f"🎴 *{user.first_name}* играет *{card}*!\n\nВерхняя: {game['top_card']}\n\nХодит: *{next_name}*\nКарт у {user.first_name}: {len(hand)}", parse_mode="Markdown", reply_markup=make_uno_action_kb(chat_id))
            else:
                await update.message.reply_text(f"❌ Карта *{raw_text}* не подходит!\nВерхняя: {game['top_card']}", parse_mode="Markdown")
        return

    # ── Спидран ──
    if chat_id in speed_games and speed_games[chat_id].get("active"):
        game=speed_games[chat_id]
        if user.id!=game["player_id"]: return
        if text==game["word"]:
            game["count"]+=1; nw=random.choice(SPEEDRUN_WORDS); game["word"]=nw
            await update.message.reply_text(f"✅ Верно! Угадано: {game['count']}\n\nСледующее: `{'_ '*len(nw)}`\nБукв: {len(nw)}", parse_mode="Markdown")
        return

    # ── Угадай число ──
    if chat_id in number_games and number_games[chat_id].get("active"):
        game=number_games[chat_id]
        if text.isdigit():
            guess=int(text); number=game["number"]
            game["attempts"][user.id]=game["attempts"].get(user.id,0)+1; att=game["attempts"][user.id]
            if guess==number:
                if game["timer_task"]: game["timer_task"].cancel()
                game["active"]=False; add_score(user.id,user.first_name,100); p["wins"]+=1
                new_achs=check_achievements(user.id,user.first_name)
                await update.message.reply_text(f"🎉 *{user.first_name}* угадал(а) *{number}*! За {att} попыток! +100\n\n📊 {global_scores_text()}\n\n🔢 /number", parse_mode="Markdown", reply_markup=make_main_keyboard(group=g))
            elif guess<number: await update.message.reply_text(f"📈 Больше! (попытка {att})", parse_mode="Markdown")
            else: await update.message.reply_text(f"📉 Меньше! (попытка {att})", parse_mode="Markdown")
        return

    # ── Викторина ──
    if chat_id in trivia_games and trivia_games[chat_id].get("active"):
        game=trivia_games[chat_id]
        if text==game["answer"]:
            if game["timer_task"]: game["timer_task"].cancel()
            game["active"]=False; pts=game.get("pts",150); add_score(user.id,user.first_name,pts); p["wins"]+=1
            if pts>=300: p["achievements"].add("trivia_hard")
            await update.message.reply_text(f"🎉 *{user.first_name}* правильно! +{pts}\n\n📊 {global_scores_text()}\n\n🧠 /trivia", parse_mode="Markdown", reply_markup=make_main_keyboard(group=g))
        return

    # ── Виселица ──
    if chat_id in hangman_games and hangman_games[chat_id].get("active"):
        game=hangman_games[chat_id]; word=game["word"]; guessed=game["guessed"]; max_err=game.get("max_errors",6)
        if len(text)>1:
            if text==word:
                if game["timer_task"]: game["timer_task"].cancel()
                game["active"]=False; add_score(user.id,user.first_name,200); p["wins"]+=1
                await update.message.reply_text(f"🎉 *{user.first_name}* угадал(а) *{word.upper()}*! +200\n\n📊 {global_scores_text()}\n\n📝 /hangman", parse_mode="Markdown", reply_markup=make_main_keyboard(group=g))
            else: await update.message.reply_text(f"❌ Неверно!", parse_mode="Markdown")
            return
        if len(text)==1 and text.isalpha():
            if text in guessed: await update.message.reply_text(f"Буква *{text.upper()}* уже была!", parse_mode="Markdown"); return
            guessed.add(text); errors=sum(1 for c in guessed if c not in word); game["errors"]=errors
            pic=HANGMAN_PICS[min(errors,5)]; shown=display_word(word,guessed); wrong=[c.upper() for c in guessed if c not in word]
            if text in word:
                add_score(user.id,user.first_name,50)
                if set(c for c in word if c!=" ")<=guessed:
                    if game["timer_task"]: game["timer_task"].cancel()
                    game["active"]=False; add_score(user.id,user.first_name,200); p["wins"]+=1
                    await update.message.reply_text(f"🎉 *{user.first_name}* открыл(а) все! +250\nСлово: *{word.upper()}*\n\n📊 {global_scores_text()}\n\n📝 /hangman", parse_mode="Markdown", reply_markup=make_main_keyboard(group=g))
                else: await update.message.reply_text(f"✅ Буква *{text.upper()}* есть! +50\n\n{pic} Ошибок: {errors}/{max_err}\nСлово: `{shown}`\nНеверные: {' '.join(wrong) if wrong else '—'}", parse_mode="Markdown")
            else:
                if errors>=max_err:
                    if game["timer_task"]: game["timer_task"].cancel()
                    game["active"]=False
                    await update.message.reply_text(f"💀 *{user.first_name}* проиграл(а)!\nСлово: *{word.upper()}*\n\n📝 /hangman", parse_mode="Markdown", reply_markup=make_main_keyboard(group=g))
                else: await update.message.reply_text(f"❌ Буквы *{text.upper()}* нет!\n\n{pic} Ошибок: {errors}/{max_err}\nСлово: `{shown}`\nНеверные: {' '.join(wrong)}", parse_mode="Markdown")
        return

    # ── Поле чудес ──
    if chat_id in wheel_games and wheel_games[chat_id].get("active"):
        game=wheel_games[chat_id]; word=game["word"]; guessed=game["guessed"]
        if game.get("sabotage_target")==user.id:
            game["sabotage_target"]=None; await update.message.reply_text(f"💣 *{user.first_name}* пропускает ход!", parse_mode="Markdown"); return
        if len(text)>1:
            if text==word:
                if game["timer_task"]: game["timer_task"].cancel()
                game["active"]=False; bonus=500
                game["round_scores"][user.id]=game["round_scores"].get(user.id,0)+bonus
                rs=max(0,game["round_scores"].get(user.id,0)); add_score(user.id,user.first_name,rs); p["wins"]+=1
                await update.message.reply_text(f"🎉 *{user.first_name}* угадал(а) *{word.upper()}*!\n+{bonus} бонус! За раунд: +{rs}\n\n📊 {global_scores_text()}\n\n🎡 /wheel", parse_mode="Markdown", reply_markup=make_main_keyboard(group=g))
            else:
                game["round_scores"][user.id]=game["round_scores"].get(user.id,0)-150; p["streak"]=0
                await update.message.reply_text(f"❌ *{user.first_name}*, неверно! -150\nСлово: `{display_word(word,guessed)}`", parse_mode="Markdown")
            return
        if len(text)==1 and text.isalpha():
            if text in guessed or text in game.get("wrong_letters",set()):
                await update.message.reply_text(f"Буква *{text.upper()}* уже была!", parse_mode="Markdown"); return
            if game.get("drum_value") is None:
                await update.message.reply_text("Сначала крутите барабан! 🎡", parse_mode="Markdown"); return
            drum_val=game["drum_value"]; game["drum_value"]=None
            if text in word:
                count=word.count(text); guessed.add(text)
                if drum_val=="x2": points=200*count; dm=" 🎯x2!"
                else:
                    points=drum_val*count if isinstance(drum_val,int) else 0
                    if p["double"]: points*=2; p["double"]=False; dm=" 🎯x2!"
                    else: dm=""
                game["round_scores"][user.id]=game["round_scores"].get(user.id,0)+points
                p["streak"]=p.get("streak",0)+1; sm=""
                if p["streak"]>=3:
                    game["round_scores"][user.id]+=100; sm=f"\n🔥 Серия {p['streak']}! +100"; p["streak"]=0; p["achievements"].add("streak3")
                if p["streak"]>=7: p["achievements"].add("streak7")
                shown=display_word(word,guessed)
                if set(c for c in word if c!=" ")<=guessed:
                    if game["timer_task"]: game["timer_task"].cancel()
                    game["active"]=False; rs=max(0,game["round_scores"].get(user.id,0))
                    add_score(user.id,user.first_name,rs); p["wins"]+=1
                    await update.message.reply_text(f"✅ *{user.first_name}* +{points}{dm}{sm}\n\n🎉 Слово: *{word.upper()}*! За раунд: +{rs}\n\n📊 {global_scores_text()}\n\n🎡 /wheel", parse_mode="Markdown", reply_markup=make_main_keyboard(group=g))
                else: await update.message.reply_text(f"✅ *{user.first_name}* открыл(а) *{text.upper()}* ({count}шт) +{points}{dm}{sm}\n\nСлово: `{shown}`", parse_mode="Markdown", reply_markup=make_wheel_kb())
            else:
                game.setdefault("wrong_letters",set()).add(text); p["streak"]=0
                game["round_scores"][user.id]=game["round_scores"].get(user.id,0)-100
                await update.message.reply_text(f"❌ *{user.first_name}*, *{text.upper()}* нет! -100\nСлово: `{display_word(word,guessed)}`", parse_mode="Markdown", reply_markup=make_wheel_kb())
        return

    # ── Крокодил ──
    game=games.get(chat_id)
    if not game or not game.get("active"): return
    if user.id==game["explainer_id"]: return
    if text==game["word"]:
        if game["timer_task"]: game["timer_task"].cancel()
        game["active"]=False; add_score(user.id,user.first_name,1); add_score(game["explainer_id"],game["explainer_name"],1)
        p["wins"]+=1; new_achs=check_achievements(user.id,user.first_name)
        ach_text=""
        if new_achs: ach_text="\n\n🏆 "+", ".join([f"{ACHIEVEMENTS[a][0]} {ACHIEVEMENTS[a][1]}" for a in new_achs if a in ACHIEVEMENTS])
        await update.message.reply_text(
            f"🎉 *{user.first_name}* угадал(а) *{game['word'].upper()}*!\n\n"
            f"🏅 +1: {user.first_name}\n🏅 +1: {game['explainer_name']}{ach_text}\n\n"
            f"📊 {global_scores_text()}\n\n▶️ /game",
            parse_mode="Markdown", reply_markup=make_main_keyboard(group=g))


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(ChatMemberHandler(greet_new_group, ChatMemberHandler.MY_CHAT_MEMBER))
    for cmd, func in [
        ("start",cmd_start),("help",cmd_help),("scores",cmd_scores),
        ("profile",cmd_profile),("achievements",cmd_achievements),
        ("inventory",cmd_inventory),("daily",cmd_daily),
        ("game",cmd_game),("wheel",cmd_wheel),("speedrun",cmd_speedrun),
        ("trivia",cmd_trivia),("hangman",cmd_hangman),("number",cmd_number),
        ("blackjack",cmd_blackjack),("slots",cmd_slots),("tod",cmd_tod),
        ("duel",cmd_duel),("roulette",cmd_roulette),("dice",cmd_dice),
        ("uno",cmd_uno),("poker",cmd_poker),("tournament",cmd_tournament),
        ("shop",cmd_shop),("join",cmd_join),("stopbot",cmd_stopbot),
    ]:
        app.add_handler(CommandHandler(cmd, func))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    async def post_init(application):
        await setup_commands(application)
    app.post_init = post_init

    print("🎮 Мега-бот запущен! 12 игр, 30+ предметов, 25 достижений!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
