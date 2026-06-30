import os, random, asyncio
from datetime import date, timedelta, datetime
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
bot_running = {"active": True}


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
            # Бар
            "bar_drinks":0,"bar_vip":False,"drunk_until":None,
            # Ферма
            "farm":{},"farm_last_collect":None,"farm_boost_until":None,
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
        ("duelist", p.get("duel_wins", 0) >= 5),
        ("shopaholic", p.get("shop_purchases", 0) >= 10),
        ("bartender", p.get("bar_drinks", 0) >= 10),
        ("farmer", len(p.get("farm", {})) >= 1),
        ("tycoon", "factory" in p.get("farm", {})),
        ("bar_rich", p["total_score"] >= 1000 and p.get("bar_drinks", 0) >= 5),
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
    drunk = " 🥴" if p.get("drunk_until") and datetime.now().isoformat() <= p["drunk_until"] else ""
    return f"{crown}{color}{name}{vip}{drunk}"


def is_frozen(uid):
    p = players.get(uid, {})
    return bool(p.get("frozen_until") and date.today().isoformat() <= p["frozen_until"])


def calc_farm_income(uid):
    p = players.get(uid, {})
    farm = p.get("farm", {})
    if not farm: return 0
    last = p.get("farm_last_collect")
    if not last: return 0
    try:
        last_dt = datetime.fromisoformat(last)
        hours = (datetime.now() - last_dt).total_seconds() / 3600
        hours = min(hours, 24)  # максимум за 24 часа
        total = 0
        for building, count in farm.items():
            if building in FARM_BUILDINGS:
                income_per_hour = FARM_BUILDINGS[building][3]
                total += income_per_hour * count * hours
        boost = 2 if p.get("farm_boost_until") and date.today().isoformat() <= p["farm_boost_until"] else 1
        return int(total * boost)
    except: return 0


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
    _, _, _, price = SHOP_ITEMS[key]
    return int(price * SALE_DISCOUNT) if key in SALE_ITEMS else price


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
def make_uno_deck():
    deck = []
    for color in UNO_COLORS:
        for val in UNO_VALUES:
            deck.append(f"{color}{val}")
            if val != "0": deck.append(f"{color}{val}")
    for s in UNO_SPECIAL: deck.extend([s]*4)
    random.shuffle(deck); return deck
def uno_card_matches(card, top):
    if card in UNO_SPECIAL or top in UNO_SPECIAL: return True
    return card[0] == top[0] or card[1:] == top[1:]


# ─── КЛАВИАТУРЫ ───────────────────────────────────────────────────────────────
def make_main_keyboard(group=False):
    rows = [
        [InlineKeyboardButton("🐊 Крокодил",callback_data="menu_game"),InlineKeyboardButton("🎡 Поле чудес",callback_data="menu_wheel")],
        [InlineKeyboardButton("⚡ Спидран",callback_data="menu_speedrun"),InlineKeyboardButton("🧠 Викторина",callback_data="menu_trivia")],
        [InlineKeyboardButton("📝 Виселица",callback_data="menu_hangman"),InlineKeyboardButton("🔢 Угадай число",callback_data="menu_number")],
        [InlineKeyboardButton("🃏 Блэкджек",callback_data="menu_blackjack"),InlineKeyboardButton("🎰 Слоты",callback_data="menu_slots")],
        [InlineKeyboardButton("❓ Правда/Действие",callback_data="menu_tod"),InlineKeyboardButton("⚔️ Дуэль",callback_data="menu_duel")],
        [InlineKeyboardButton("🎯 Рулетка",callback_data="menu_roulette"),InlineKeyboardButton("🎲 Кубик",callback_data="menu_dice")],
        [InlineKeyboardButton("🎴 УНО",callback_data="menu_uno"),InlineKeyboardButton("♠️ Покер",callback_data="menu_poker")],
        [InlineKeyboardButton("🏆 Турнир",callback_data="menu_tournament"),InlineKeyboardButton("🧮 Математика",callback_data="menu_math")],
        [InlineKeyboardButton("🍸 Бар",callback_data="menu_bar"),InlineKeyboardButton("🌾 Ферма",callback_data="menu_farm")],
        [InlineKeyboardButton("🛒 Магазин 🔥СКИДКИ",callback_data="menu_shop"),InlineKeyboardButton("📊 Счёт",callback_data="menu_scores")],
        [InlineKeyboardButton("🏆 Достижения",callback_data="menu_achievements"),InlineKeyboardButton("🎁 Бонус",callback_data="menu_daily")],
        [InlineKeyboardButton("👤 Профиль",callback_data="menu_profile"),InlineKeyboardButton("🎒 Инвентарь",callback_data="menu_inventory")],
        [InlineKeyboardButton("🛑 Стоп бот",callback_data="admin_stop")],
    ]
    if group:
        rows.append([InlineKeyboardButton("✋ Присоединиться",callback_data="menu_join")])
    else:
        rows.insert(0,[InlineKeyboardButton("➕ Добавить в группу",url=f"https://t.me/{BOT_USERNAME}?startgroup=true")])
    return InlineKeyboardMarkup(rows)

def make_croc_kb(): return InlineKeyboardMarkup([[InlineKeyboardButton("⏭ Пропустить",callback_data="croc_skip"),InlineKeyboardButton("🛑 Стоп",callback_data="croc_stop")]])
def make_wheel_kb(): return InlineKeyboardMarkup([[InlineKeyboardButton("🎡 Крутить барабан",callback_data="wheel_spin"),InlineKeyboardButton("🛑 Стоп",callback_data="wheel_stop")]])
def make_bj_kb(): return InlineKeyboardMarkup([[InlineKeyboardButton("🃏 Ещё",callback_data="bj_hit"),InlineKeyboardButton("✋ Хватит",callback_data="bj_stand")]])
def make_duel_kb(cid): return InlineKeyboardMarkup([[InlineKeyboardButton("⚔️ Принять!",callback_data=f"duel_accept_{cid}"),InlineKeyboardButton("❌ Отказать",callback_data="duel_decline")]])
def make_roulette_kb(): return InlineKeyboardMarkup([[InlineKeyboardButton("🔴 Красное",callback_data="rou_red"),InlineKeyboardButton("⚫ Чёрное",callback_data="rou_black"),InlineKeyboardButton("🟢 Зеро",callback_data="rou_zero")]])
def make_dice_kb(): return InlineKeyboardMarkup([[InlineKeyboardButton("🎲 Бросить!",callback_data="dice_roll")]])
def make_trivia_kb(): return InlineKeyboardMarkup([[InlineKeyboardButton("🟢 Лёгкий +50",callback_data="trivia_easy"),InlineKeyboardButton("🟡 Средний +150",callback_data="trivia_medium"),InlineKeyboardButton("🔴 Сложный +300",callback_data="trivia_hard")]])
def make_uno_kb(): return InlineKeyboardMarkup([[InlineKeyboardButton("🃏 Взять карту",callback_data="uno_draw"),InlineKeyboardButton("👁 Мои карты",callback_data="uno_show")]])

def make_bar_keyboard(p):
    rows = []
    for key,(icon,name,price,bonus,desc) in BAR_DRINKS.items():
        actual = price // 2 if p.get("bar_vip") else price
        rows.append([InlineKeyboardButton(f"{icon} {name} — {actual} оч ({bonus:+} оч)",callback_data=f"bar_{key}")])
    rows.append([InlineKeyboardButton("🔙 Назад",callback_data="menu_back")])
    return InlineKeyboardMarkup(rows)

def make_farm_keyboard(p):
    farm = p.get("farm", {})
    rows = []
    for key,(icon,name,price,income,desc) in FARM_BUILDINGS.items():
        count = farm.get(key, 0)
        boost = 2 if p.get("farm_boost_until") and date.today().isoformat() <= p["farm_boost_until"] else 1
        rows.append([InlineKeyboardButton(
            f"{icon} {name} x{count} — {price} оч ({income*boost} оч/ч)",
            callback_data=f"farm_buy_{key}")])
    income_ready = calc_farm_income(p.get("id", 0) if "id" in p else 0)
    rows.append([InlineKeyboardButton(f"💰 Собрать ({income_ready} оч)",callback_data="farm_collect")])
    rows.append([InlineKeyboardButton("🔙 Назад",callback_data="menu_back")])
    return InlineKeyboardMarkup(rows)

def make_shop_keyboard(p):
    rows = [InlineKeyboardButton("🔥 ═══ СКИДКИ 20% ═══ 🔥",callback_data="shop_info")]
    result = [[rows[0]]]
    for key in SALE_ITEMS:
        if key in SHOP_ITEMS:
            icon,name,_,orig = SHOP_ITEMS[key]
            price = int(orig * SALE_DISCOUNT)
            result.append([InlineKeyboardButton(f"{icon} {name} 🔥{price} оч (было {orig})",callback_data=f"shop_{key}")])
    result.append([InlineKeyboardButton("── Все предметы ──",callback_data="shop_info")])
    for key,(icon,name,desc,price) in SHOP_ITEMS.items():
        if key in SALE_ITEMS: continue
        owned = ""
        if key=="vip" and p.get("vip"): owned=" ✅"
        if key=="speedrun" and p.get("speedrun_access"): owned=" ✅"
        if key=="bar_vip" and p.get("bar_vip"): owned=" ✅"
        result.append([InlineKeyboardButton(f"{icon} {name}{owned} — {shop_price(key)} оч.",callback_data=f"shop_{key}")])
    result.append([InlineKeyboardButton("🔙 Назад",callback_data="menu_back")])
    return InlineKeyboardMarkup(result)


async def setup_commands(app):
    cmds = [
        BotCommand("start","🎮 Главное меню"),BotCommand("help","❓ Все игры"),
        BotCommand("profile","👤 Профиль"),BotCommand("achievements","🏆 Достижения"),
        BotCommand("inventory","🎒 Инвентарь"),BotCommand("daily","🎁 Бонус"),
        BotCommand("scores","📊 Счёт"),BotCommand("shop","🛒 Магазин"),
        BotCommand("bar","🍸 Бар"),BotCommand("farm","🌾 Ферма"),
        BotCommand("game","🐊 Крокодил"),BotCommand("wheel","🎡 Поле чудес"),
        BotCommand("speedrun","⚡ Спидран"),BotCommand("trivia","🧠 Викторина"),
        BotCommand("hangman","📝 Виселица"),BotCommand("number","🔢 Число"),
        BotCommand("blackjack","🃏 Блэкджек"),BotCommand("slots","🎰 Слоты"),
        BotCommand("tod","❓ Правда/Действие"),BotCommand("duel","⚔️ Дуэль"),
        BotCommand("roulette","🎯 Рулетка"),BotCommand("dice","🎲 Кубик"),
        BotCommand("uno","🎴 УНО"),BotCommand("poker","♠️ Покер"),
        BotCommand("tournament","🏆 Турнир"),BotCommand("math","🧮 Математика"),
        BotCommand("join","✋ Присоединиться"),BotCommand("stopbot","🛑 Стоп бот"),
    ]
    await app.bot.set_my_commands(cmds, scope=BotCommandScopeAllGroupChats())
    await app.bot.set_my_commands(cmds, scope=BotCommandScopeAllPrivateChats())


async def greet_new_group(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    result = update.my_chat_member
    if not result: return
    if result.old_chat_member.status in ("left","kicked") and result.new_chat_member.status in ("member","administrator"):
        chat = update.effective_chat
        await ctx.bot.send_message(chat_id=chat.id,
            text=f"👋 Привет, *{chat.title}*!\n\n🎮 *Мега Игровой Бот* — 15 игр!\n\n"
                 f"🐊 Крокодил | 🎡 Поле чудес | ⚡ Спидран\n"
                 f"🧠 Викторина (3 уровня!) | 📝 Виселица | 🔢 Число\n"
                 f"🃏 Блэкджек | 🎰 Слоты | ❓ Правда/Действие\n"
                 f"⚔️ Дуэль | 🎯 Рулетка | 🎲 Кубик | 🎴 УНО\n"
                 f"♠️ Покер | 🏆 Турнир | 🧮 Математика\n\n"
                 f"🍸 *БАР* — 12 напитков!\n"
                 f"🌾 *ФЕРМА* — тайкун, стройте бизнес!\n"
                 f"🛒 *Магазин* — 33 предмета со *скидками*!\n"
                 f"🏆 25 достижений | 12 титулов | 🎁 Ежедневные бонусы\n\n"
                 f"✋ Нажмите *Присоединиться*!",
            parse_mode="Markdown", reply_markup=make_main_keyboard(group=True))


# ─── КОМАНДЫ ──────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user; chat = update.effective_chat
    p = get_player(user.id, user.first_name); g = is_group(chat)
    title = get_title(p["total_score"])
    farm_income = calc_farm_income(user.id)
    farm_msg = f"\n🌾 Ферма готова: *+{farm_income} оч* (собери /farm)" if farm_income > 0 else ""
    await update.message.reply_text(
        f"👋 Привет, *{get_nick(user.id, user.first_name)}*!\n\n"
        f"🏅 {title} | 💰 {p['total_score']} оч | 🏆 {p['wins']} побед{farm_msg}\n\n"
        f"🎮 *15 игр* | 🍸 *Бар* | 🌾 *Ферма* | 🛒 *33 предмета*\n\n"
        f"{'✋ Присоединись! 👇' if g else '➕ Добавь в группу! 👇'}",
        parse_mode="Markdown", reply_markup=make_main_keyboard(group=g))


async def cmd_stopbot(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    bot_running["active"] = False
    await update.message.reply_text("🛑 *Бот остановлен!*\n\nЧтобы запустить снова — передеплой на Railway.", parse_mode="Markdown")
    for g in [games,wheel_games,speed_games,trivia_games,hangman_games,number_games]:
        for cid,game in g.items():
            if game.get("active"): game["active"]=False
            if game.get("timer_task"): game["timer_task"].cancel()


async def cmd_bar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user; p = get_player(user.id, user.first_name)
    vip_msg = " 🌟VIP скидка 50%!" if p.get("bar_vip") else ""
    await update.message.reply_text(
        f"🍸 *Добро пожаловать в Бар!*{vip_msg}\n\n"
        f"Выпивка дарит бонусные очки!\n"
        f"🍺 Выпито: {p.get('bar_drinks', 0)} напитков\n\n"
        f"Выбери напиток:",
        parse_mode="Markdown", reply_markup=make_bar_keyboard(p))


async def cmd_farm(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user; p = get_player(user.id, user.first_name)
    farm = p.get("farm", {})
    income_ready = calc_farm_income(user.id)
    boost = "🔥 x2 активен!" if p.get("farm_boost_until") and date.today().isoformat() <= p["farm_boost_until"] else ""
    buildings_text = ""
    total_per_hour = 0
    for key, count in farm.items():
        if key in FARM_BUILDINGS and count > 0:
            icon, name, _, income, _ = FARM_BUILDINGS[key]
            total_per_hour += income * count
            buildings_text += f"{icon} {name} x{count} (+{income*count} оч/ч)\n"
    if not buildings_text: buildings_text = "Нет зданий. Купи первое!"
    await update.message.reply_text(
        f"🌾 *Твоя Ферма* {boost}\n\n"
        f"💰 Очков: *{p['total_score']}*\n"
        f"📈 Доход: *{total_per_hour} оч/ч*\n"
        f"💵 Готово к сбору: *{income_ready} оч*\n\n"
        f"🏗 *Постройки:*\n{buildings_text}\n\n"
        f"Строй здания и зарабатывай пассивно!",
        parse_mode="Markdown", reply_markup=make_farm_keyboard(p))


async def cmd_profile(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user; p = get_player(user.id, user.first_name)
    title = get_title(p["total_score"])
    achs = [f"{ACHIEVEMENTS[a][0]}" for a in p["achievements"] if a in ACHIEVEMENTS]
    farm = p.get("farm",{}); total_per_hour = sum(FARM_BUILDINGS[k][3]*v for k,v in farm.items() if k in FARM_BUILDINGS)
    income_ready = calc_farm_income(user.id)
    await update.message.reply_text(
        f"👤 *{get_nick(user.id, user.first_name)}*\n\n"
        f"🏅 {title}\n💰 Очки: *{p['total_score']}*\n"
        f"🏆 Победы: {p['wins']} | ⚔️ Дуэли: {p.get('duel_wins',0)}\n"
        f"🎮 Игр: {len(p['games_played'])} | 🍸 Напитков: {p.get('bar_drinks',0)}\n"
        f"🌾 Ферма: {total_per_hour} оч/ч | Готово: {income_ready} оч\n"
        f"👑 VIP: {'Да' if p['vip'] else 'Нет'} | ⚡ Спидран: {'Да' if p['speedrun_access'] else 'Нет'}\n\n"
        f"🏆 Достижения ({len(p['achievements'])}): {' '.join(achs) if achs else 'Нет'}",
        parse_mode="Markdown")


async def cmd_achievements(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user; p = get_player(user.id, user.first_name)
    unlocked = sum(1 for k in ACHIEVEMENTS if k in p["achievements"])
    lines = [f"{'✅' if k in p['achievements'] else '🔒'} {v[0]} *{v[1]}* — {v[2]}" for k,v in ACHIEVEMENTS.items()]
    await update.message.reply_text(f"🏆 *Достижения* ({unlocked}/{len(ACHIEVEMENTS)})\n\n"+"\n".join(lines), parse_mode="Markdown")


async def cmd_inventory(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user; p = get_player(user.id, user.first_name)
    inv = {k:v for k,v in p.get("inventory",{}).items() if v>0}
    if not inv: await update.message.reply_text("🎒 *Инвентарь пуст*\n\nКупи в /shop!", parse_mode="Markdown"); return
    lines = [f"{SHOP_ITEMS[k][0]} *{SHOP_ITEMS[k][1]}* x{v} — {SHOP_ITEMS[k][2]}" for k,v in inv.items() if k in SHOP_ITEMS]
    await update.message.reply_text("🎒 *Инвентарь*\n\n"+"\n".join(lines), parse_mode="Markdown")


async def cmd_daily(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user; p = get_player(user.id, user.first_name)
    today = date.today().isoformat()
    if p.get("last_daily") == today:
        await update.message.reply_text("🎁 Уже получил сегодня!\nПриходи завтра 😊", parse_mode="Markdown"); return
    bonus = random.randint(50, 300)
    if p.get("double_daily"): bonus *= 2; p["double_daily"] = False
    p["last_daily"] = today; p["daily_streak"] = p.get("daily_streak",0)+1
    streak = p["daily_streak"]
    if streak >= 7: p["achievements"].add("daily7")
    streak_bonus = bonus//2 if streak >= 3 else 0
    total = bonus + streak_bonus
    add_score(user.id, user.first_name, total)
    streak_msg = f"\n🔥 Серия {streak} дней! +{streak_bonus} бонус!" if streak > 1 else ""
    await update.message.reply_text(f"🎁 *Ежедневный бонус!*\n\n+*{total}* очков!{streak_msg}\n\n💰 Всего: {p['total_score']}", parse_mode="Markdown")


async def cmd_scores(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"📊 *Таблица очков*\n\n{global_scores_text()}", parse_mode="Markdown")


async def cmd_shop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user; p = get_player(user.id, user.first_name)
    await update.message.reply_text(f"🛒 *Магазин* — {len(SHOP_ITEMS)} предметов!\n\n💰 Твои очки: *{p['total_score']}*\n🔥 *Скидки 20%* на популярные товары!\n\nВыбери:", parse_mode="Markdown", reply_markup=make_shop_keyboard(p))


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    g = is_group(update.effective_chat)
    await update.message.reply_text(
        "📖 *Все 15 игр + Бар + Ферма*\n\n"
        "🐊 /game — Крокодил\n🎡 /wheel — Поле чудес\n⚡ /speedrun — Спидран\n"
        "🧠 /trivia — Викторина (3 уровня!)\n📝 /hangman — Виселица\n"
        "🔢 /number — Угадай число\n🃏 /blackjack — Блэкджек\n"
        "🎰 /slots — Слоты\n❓ /tod — Правда/Действие\n"
        "⚔️ /duel — Дуэль\n🎯 /roulette — Рулетка\n"
        "🎲 /dice — Кубик\n🎴 /uno — УНО\n♠️ /poker — Покер\n"
        "🏆 /tournament — Турнир\n🧮 /math — Математика\n\n"
        "🍸 /bar — Бар с напитками\n"
        "🌾 /farm — Ферма тайкун\n\n"
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
    await update.message.reply_text(f"✋ *{user.first_name}* присоединился(ась)!\n👥 {names}", parse_mode="Markdown", reply_markup=make_main_keyboard(group=True))


# ══════════ ИГРЫ ══════════════════════════════════════════════════════════════

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
    p = get_player(user.id, user.first_name); p["games_played"].add("wheel")
    if chat_id in wheel_games and wheel_games[chat_id].get("timer_task"): wheel_games[chat_id]["timer_task"].cancel()
    cat = random.choice(list(WORDS.keys())); word = random.choice(WORDS[cat]).lower()
    wheel_games[chat_id] = {"word":word,"category":cat,"guessed":set(),"wrong_letters":set(),"active":True,"round_scores":{},"drum_value":None,"timer_task":None,"sabotage_target":None}
    shown = display_word(word, set())
    await reply(f"🎡 *Поле чудес!*\nКатегория: {cat}\n\nСлово: `{shown}`\n\nБарабан → буква!\n❌-100 | ❌ Слово:-150 | ✅ Слово:+500\n⏱ 5 мин!", parse_mode="Markdown", reply_markup=make_wheel_kb())
    task = asyncio.create_task(wheel_timer(chat_id, ctx)); wheel_games[chat_id]["timer_task"] = task

async def cmd_wheel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await start_wheel(update.effective_chat.id, update.effective_user, ctx, update.message.reply_text)


async def speedrun_timer(chat_id, ctx):
    await asyncio.sleep(SPEEDRUN_TIME)
    game = speed_games.get(chat_id)
    if game and game.get("active"):
        game["active"] = False; bonus = game["count"]*50
        add_score(game["player_id"], game["player_name"], bonus)
        await ctx.bot.send_message(chat_id=chat_id, text=f"⏰ *Спидран!*\n*{game['player_name']}* угадал(а) {game['count']} слов!\n+{bonus} оч", parse_mode="Markdown")

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
    if level=="easy": pool,label = TRIVIA_EASY,"🟢 Лёгкий"
    elif level=="hard": pool,label = TRIVIA_HARD,"🔴 Сложный"
    else: pool,label = TRIVIA_MEDIUM,"🟡 Средний"
    q = random.choice(pool)
    trivia_games[chat_id] = {"question":q["q"],"answer":q["a"],"pts":q["pts"],"active":True,"timer_task":None}
    await reply(f"🧠 *Викторина!* {label}\n\n❓ {q['q']}\n\n⏱ {TRIVIA_TIME} сек | +{q['pts']} очков", parse_mode="Markdown")
    task = asyncio.create_task(trivia_timer(chat_id, ctx)); trivia_games[chat_id]["timer_task"] = task

async def cmd_trivia(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🧠 *Викторина!*\n\nВыберите уровень:", parse_mode="Markdown", reply_markup=make_trivia_kb())


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
    if chat_id in number_games and number_games[chat_id].get("timer_task"): number_games[chat_id]["timer_task"].cancel()
    number = random.randint(1,100)
    number_games[chat_id] = {"number":number,"active":True,"attempts":{},"timer_task":None}
    await reply(f"🔢 *Угадай число!*\nОт *1 до 100*\n+100 оч | ⏱ {NUMBER_TIME} сек!", parse_mode="Markdown")
    task = asyncio.create_task(number_timer(chat_id, ctx)); number_games[chat_id]["timer_task"] = task

async def cmd_number(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await start_number(update.effective_chat.id, update.effective_user, ctx, update.message.reply_text)


async def start_blackjack(chat_id, user, ctx, reply):
    p = get_player(user.id, user.first_name); p["games_played"].add("blackjack")
    if p["total_score"] < 50: await reply("🃏 Нужно 50 оч!", parse_mode="Markdown"); return
    hand = [deal_card(),deal_card()]; dealer = [deal_card(),deal_card()]
    blackjack_games[chat_id] = {"player_id":user.id,"player_name":user.first_name,"hand":hand,"dealer":dealer,"active":True}
    val = card_value(hand)
    await reply(f"🃏 *Блэкджек!*\n\nТвои: {hand_str(hand)}\nДилер: {dealer[0]} + ?\n\nСтавка: 50 оч\n{'🎉 БЛЭКДЖЕК!' if val==21 else 'Ещё или хватит?'}", parse_mode="Markdown", reply_markup=None if val==21 else make_bj_kb())
    if val==21:
        p["total_score"]=max(0,p["total_score"]-50); add_score(user.id,user.first_name,125); p["wins"]+=1
        p["achievements"].add("blackjack21"); blackjack_games[chat_id]["active"]=False
        await ctx.bot.send_message(chat_id=chat_id, text=f"🎉 *БЛЭКДЖЕК!* {user.first_name} +125!\n🃏 /blackjack", parse_mode="Markdown")

async def cmd_blackjack(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await start_blackjack(update.effective_chat.id, update.effective_user, ctx, update.message.reply_text)


async def start_slots(chat_id, user, ctx, reply):
    p = get_player(user.id, user.first_name); p["games_played"].add("slots")
    if p["total_score"]<100: await reply("🎰 Нужно 100 оч!", parse_mode="Markdown"); return
    p["total_score"]-=100; symbols=spin_slots(); prize=check_slots(symbols)
    result=" | ".join(symbols)
    if prize>0:
        add_score(user.id,user.first_name,prize); p["achievements"].add("lucky_slots")
        if prize==777: p["achievements"].add("lucky7")
        msg=f"🎰 *{result}*\n\n🎉 ВЫИГРЫШ *+{prize}* оч!\nВсего: {p['total_score']}"
    else: msg=f"🎰 *{result}*\n\nНе повезло! -100\nВсего: {p['total_score']}"
    await reply(msg, parse_mode="Markdown")

async def cmd_slots(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await start_slots(update.effective_chat.id, update.effective_user, ctx, update.message.reply_text)


async def start_tod(chat_id, user, ctx, reply):
    get_player(user.id,user.first_name)["games_played"].add("tod")
    if random.choice(["truth","dare"])=="truth":
        await reply(f"❓ *Правда или Действие*\n\n*{user.first_name}*\n\n🗣 *ПРАВДА:*\n{random.choice(TOD_TRUTHS)}", parse_mode="Markdown")
    else:
        await reply(f"❓ *Правда или Действие*\n\n*{user.first_name}*\n\n🎯 *ДЕЙСТВИЕ:*\n{random.choice(TOD_DARES)}", parse_mode="Markdown")

async def cmd_tod(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await start_tod(update.effective_chat.id, update.effective_user, ctx, update.message.reply_text)


async def cmd_duel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id=update.effective_chat.id; user=update.effective_user
    p=get_player(user.id,user.first_name); p["games_played"].add("duel")
    if p["total_score"]<100: await update.message.reply_text("⚔️ Нужно 100 оч!", parse_mode="Markdown"); return
    if update.message.reply_to_message:
        opp=update.message.reply_to_message.from_user
        if opp.id==user.id: await update.message.reply_text("Нельзя с собой 😄", parse_mode="Markdown"); return
        duel_games[chat_id]={"challenger_id":user.id,"challenger_name":user.first_name,"opponent_id":opp.id,"opponent_name":opp.first_name,"active":True}
        await update.message.reply_text(f"⚔️ *{user.first_name}* вызывает *{opp.first_name}*!\nСтавка: 100 оч\n*{opp.first_name}*, принимаешь?", parse_mode="Markdown", reply_markup=make_duel_kb(user.id))
    else: await update.message.reply_text("⚔️ Ответь на сообщение игрока и напиши /duel", parse_mode="Markdown")


async def start_roulette(chat_id, user, ctx, reply):
    p=get_player(user.id,user.first_name); p["games_played"].add("roulette")
    if p["total_score"]<100: await reply("🎯 Нужно 100 оч!", parse_mode="Markdown"); return
    roulette_games[chat_id]={"player_id":user.id,"player_name":user.first_name,"active":True}
    await reply(f"🎯 *Рулетка!*\n\nСтавка 100 оч\n🔴+100 | ⚫+100 | 🟢+350\n\nВыбери:", parse_mode="Markdown", reply_markup=make_roulette_kb())

async def cmd_roulette(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await start_roulette(update.effective_chat.id, update.effective_user, ctx, update.message.reply_text)


async def start_dice(chat_id, user, ctx, reply):
    p=get_player(user.id,user.first_name); p["games_played"].add("dice")
    dice_games[chat_id]={"player_id":user.id,"player_name":user.first_name,"active":True}
    await reply(f"🎲 *Кубик удачи!*\n6=+200 | 1=-50 | Остальное=0", parse_mode="Markdown", reply_markup=make_dice_kb())

async def cmd_dice(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await start_dice(update.effective_chat.id, update.effective_user, ctx, update.message.reply_text)


async def start_uno(chat_id, user, ctx, reply):
    p=get_player(user.id,user.first_name); p["games_played"].add("uno")
    if chat_id in uno_games and uno_games[chat_id].get("active"):
        game=uno_games[chat_id]
        if user.id not in [pid for pid,_ in game["players"]]:
            game["players"].append((user.id,user.first_name)); deck=make_uno_deck()
            game["hands"][user.id]=[deck.pop() for _ in range(7)]; game["deck"].extend(deck)
            try: await ctx.bot.send_message(chat_id=user.id, text=f"🎴 Твои карты:\n{' '.join(game['hands'][user.id])}", parse_mode="Markdown")
            except: pass
            await reply(f"✋ *{user.first_name}* присоединяется к УНО!\nИгроков: {len(game['players'])}", parse_mode="Markdown")
        else: await reply("Ты уже в игре УНО!", parse_mode="Markdown"); return
        return
    deck=make_uno_deck(); hand=[deck.pop() for _ in range(7)]; top=deck.pop()
    uno_games[chat_id]={"active":True,"players":[(user.id,user.first_name)],"current":0,"deck":deck,"hands":{user.id:hand},"top_card":top,"direction":1,"timer_task":None}
    try: await ctx.bot.send_message(chat_id=user.id, text=f"🎴 Твои карты:\n{' '.join(hand)}\n\nВерхняя карта: {top}", parse_mode="Markdown")
    except: pass
    await reply(f"🎴 *УНО!* Создал *{user.first_name}*\nВерхняя карта: *{top}*\n\nПиши /uno чтобы присоединиться!\nПиши название карты из руки для хода.", parse_mode="Markdown")

async def cmd_uno(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await start_uno(update.effective_chat.id, update.effective_user, ctx, update.message.reply_text)


async def start_poker(chat_id, user, ctx, reply):
    p=get_player(user.id,user.first_name); p["games_played"].add("poker")
    if p["total_score"]<100: await reply("♠️ Нужно 100 оч!", parse_mode="Markdown"); return
    hand=[deal_card(),deal_card(),deal_card(),deal_card(),deal_card()]
    ctx.chat_data["poker_hand"]=hand; ctx.chat_data["poker_player"]=(user.id,user.first_name)
    await reply(f"♠️ *Покер!*\n\nТвои: {' '.join(hand)}\nСтавка: 100 оч\n\nПродолжить или сбросить?", parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Продолжить",callback_data="poker_continue"),InlineKeyboardButton("❌ Сбросить",callback_data="poker_fold")]]))

async def cmd_poker(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await start_poker(update.effective_chat.id, update.effective_user, ctx, update.message.reply_text)


async def cmd_math(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    get_player(update.effective_user.id, update.effective_user.first_name)["games_played"].add("math")
    a = random.randint(1, 50); b = random.randint(1, 50)
    ops = [("+", a+b), ("-", a-b), ("×", a*b)]
    op_str, answer = random.choice(ops)
    ctx.chat_data["math_answer"] = str(answer)
    ctx.chat_data["math_active"] = True
    await update.message.reply_text(f"🧮 *Математика!*\n\n❓ Сколько будет *{a} {op_str} {b}*?\n\n⏱ 15 секунд! +80 очков", parse_mode="Markdown")
    await asyncio.sleep(15)
    if ctx.chat_data.get("math_active"):
        ctx.chat_data["math_active"] = False
        await update.message.reply_text(f"⏰ Время! Ответ: *{answer}*\n\n🧮 /math", parse_mode="Markdown")

async def cmd_tournament(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id=update.effective_chat.id; user=update.effective_user
    get_player(user.id,user.first_name)["games_played"].add("tournament")
    t=tournaments.get(chat_id)
    if t and t.get("active") and len(t["players"])>=2:
        if user.id in t["players"]:
            pl=list(t["players"].items()); random.shuffle(pl)
            wid,wname=pl[0]; add_score(wid,wname,500); tournaments[chat_id]["active"]=False
            names="\n".join([f"{i+1}. {n}" for i,(uid,n) in enumerate(pl)])
            await update.message.reply_text(f"🏆 *ТУРНИР!*\n\nУчастники:\n{names}\n\n🥇 *{wname}* победил! +500 оч!", parse_mode="Markdown"); return
    if not t or not t.get("active"):
        tournaments[chat_id]={"active":True,"players":{user.id:user.first_name}}
        await update.message.reply_text(f"🏆 *Турнир открыт!* {user.first_name} создаёт!\n\nПиши /tournament чтобы записаться. Минимум 2 игрока.", parse_mode="Markdown")
    else:
        if user.id not in t["players"]: t["players"][user.id]=user.first_name
        names=", ".join(t["players"].values())
        await update.message.reply_text(f"✋ *{user.first_name}* в турнире!\nУчастников: {len(t['players'])}: {names}\n\nЕщё раз /tournament для старта!", parse_mode="Markdown")


# ══════════ CALLBACK ══════════════════════════════════════════════════════════

async def callback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query=update.callback_query; await query.answer()
    chat_id=update.effective_chat.id; user=update.effective_user
    data=query.data; p=get_player(user.id,user.first_name)
    g=is_group(update.effective_chat)

    async def reply(text, **kwargs):
        await ctx.bot.send_message(chat_id=chat_id, text=text, **kwargs)

    # ── Меню ──
    if data=="menu_game": await start_croc(chat_id,user,ctx,reply)
    elif data=="menu_wheel": await start_wheel(chat_id,user,ctx,reply)
    elif data=="menu_speedrun": await start_speedrun(chat_id,user,ctx,reply)
    elif data=="menu_trivia": await reply("🧠 Выберите уровень:", parse_mode="Markdown", reply_markup=make_trivia_kb())
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
        t=tournaments.get(chat_id)
        if not t or not t.get("active"):
            tournaments[chat_id]={"active":True,"players":{user.id:user.first_name}}
            await reply(f"🏆 Турнир открыт! *{user.first_name}* создаёт!\nПиши /tournament чтобы записаться.", parse_mode="Markdown")
        else:
            if user.id not in t["players"]: t["players"][user.id]=user.first_name
            await reply(f"✋ *{user.first_name}* в турнире! Участников: {len(t['players'])}", parse_mode="Markdown")
    elif data=="menu_math":
        a=random.randint(1,50); b=random.randint(1,50); ops=[("+",a+b),("-",a-b),("×",a*b)]; op_str,ans=random.choice(ops)
        ctx.chat_data["math_answer"]=str(ans); ctx.chat_data["math_active"]=True
        await reply(f"🧮 *Математика!*\n\n❓ Сколько будет *{a} {op_str} {b}*?\n\n⏱ 15 сек! +80 оч", parse_mode="Markdown")
    elif data=="menu_bar": await reply(f"🍸 *Добро пожаловать в Бар!*\n\n💰 {p['total_score']} оч\n🍺 Выпито: {p.get('bar_drinks',0)} напитков", parse_mode="Markdown", reply_markup=make_bar_keyboard(p))
    elif data=="menu_farm":
        income=calc_farm_income(user.id); farm=p.get("farm",{})
        total_per_h=sum(FARM_BUILDINGS[k][3]*v for k,v in farm.items() if k in FARM_BUILDINGS)
        await reply(f"🌾 *Ферма*\n\n💰 {p['total_score']} оч\n📈 Доход: {total_per_h} оч/ч\n💵 Готово: {income} оч\n\nСтрой здания:", parse_mode="Markdown", reply_markup=make_farm_keyboard(p))
    elif data=="menu_scores": await reply(f"📊 *Таблица*\n\n{global_scores_text()}", parse_mode="Markdown")
    elif data=="menu_shop": await reply(f"🛒 *Магазин*\n\n💰 {p['total_score']} оч", parse_mode="Markdown", reply_markup=make_shop_keyboard(p))
    elif data=="menu_achievements":
        unlocked=sum(1 for k in ACHIEVEMENTS if k in p["achievements"])
        lines=[f"{'✅' if k in p['achievements'] else '🔒'} {v[0]} {v[1]}" for k,v in ACHIEVEMENTS.items()]
        await reply(f"🏆 *Достижения* ({unlocked}/{len(ACHIEVEMENTS)})\n\n"+"\n".join(lines), parse_mode="Markdown")
    elif data=="menu_profile":
        title=get_title(p["total_score"])
        await reply(f"👤 *{get_nick(user.id,user.first_name)}*\n\n🏅 {title}\n💰 {p['total_score']} оч | 🏆 {p['wins']} побед", parse_mode="Markdown")
    elif data=="menu_inventory":
        inv={k:v for k,v in p.get("inventory",{}).items() if v>0}
        if not inv: await reply("🎒 Пусто! Купи в /shop", parse_mode="Markdown")
        else:
            lines=[f"{SHOP_ITEMS[k][0]} *{SHOP_ITEMS[k][1]}* x{v}" for k,v in inv.items() if k in SHOP_ITEMS]
            await reply("🎒 *Инвентарь*\n\n"+"\n".join(lines), parse_mode="Markdown")
    elif data=="menu_daily":
        today=date.today().isoformat()
        if p.get("last_daily")==today: await query.answer("Уже получил!",show_alert=True); return
        bonus=random.randint(50,300)
        if p.get("double_daily"): bonus*=2; p["double_daily"]=False
        p["last_daily"]=today; add_score(user.id,user.first_name,bonus)
        await reply(f"🎁 *{user.first_name}* +*{bonus}* оч!\n💰 Всего: {p['total_score']}", parse_mode="Markdown")
    elif data=="menu_join":
        if chat_id not in group_players: group_players[chat_id]={}
        if user.id in group_players[chat_id]: await query.answer("Уже в игре!",show_alert=True); return
        group_players[chat_id][user.id]=user.first_name
        await reply(f"✋ *{user.first_name}* присоединился!\n👥 {', '.join(group_players[chat_id].values())}", parse_mode="Markdown")
    elif data=="menu_back": await query.edit_message_reply_markup(reply_markup=make_main_keyboard(group=g))
    elif data=="shop_info": return

    # ── Стоп ──
    elif data=="admin_stop":
        bot_running["active"]=False
        await query.edit_message_text("🛑 *Бот остановлен!*", parse_mode="Markdown")

    # ── Викторина ──
    elif data in ("trivia_easy","trivia_medium","trivia_hard"):
        await start_trivia_by_level(chat_id, user, ctx, reply, data.split("_")[1])

    # ── Бар ──
    elif data.startswith("bar_"):
        key=data[4:]
        if key not in BAR_DRINKS: return
        icon,name,price,bonus,desc=BAR_DRINKS[key]
        actual_price = price//2 if p.get("bar_vip") else price
        if p["total_score"]<actual_price: await query.answer(f"Нужно {actual_price} оч!",show_alert=True); return
        p["total_score"]-=actual_price; add_score(user.id,user.first_name,bonus)
        p["bar_drinks"]=p.get("bar_drinks",0)+1
        check_achievements(user.id,user.first_name)
        # Энергетик — бустер
        if key=="energy": p["score_boost"]=True
        # Опьянение
        if key in ("tequila","whiskey","vodka"):
            p["drunk_until"]=(datetime.now()+timedelta(hours=1)).isoformat()
        drunk_msg = " 🥴 Немного пьян!" if p.get("drunk_until") else ""
        await reply(f"{icon} *{user.first_name}* пьёт *{name}*!\n\n{desc}{drunk_msg}\n\n💰 Осталось: {p['total_score']} оч\n🍺 Выпито всего: {p['bar_drinks']}", parse_mode="Markdown")

    # ── Ферма ──
    elif data.startswith("farm_buy_"):
        key=data[9:]
        if key not in FARM_BUILDINGS: return
        icon,name,price,income,desc=FARM_BUILDINGS[key]
        if p["total_score"]<price: await query.answer(f"Нужно {price} оч!",show_alert=True); return
        p["total_score"]-=price
        p.setdefault("farm",{})[key]=p.get("farm",{}).get(key,0)+1
        if p.get("farm_last_collect") is None: p["farm_last_collect"]=datetime.now().isoformat()
        check_achievements(user.id,user.first_name)
        count=p["farm"][key]
        await reply(f"{icon} *{user.first_name}* строит *{name}*!\n\nКоличество: {count}\nДоход: +{income*count} оч/ч\n\n💰 Осталось: {p['total_score']} оч", parse_mode="Markdown")

    elif data=="farm_collect":
        income=calc_farm_income(user.id)
        if income<=0: await query.answer("Нечего собирать! Подожди немного.",show_alert=True); return
        p["farm_last_collect"]=datetime.now().isoformat()
        add_score(user.id,user.first_name,income)
        await reply(f"💰 *{user.first_name}* собирает урожай!\n\n+*{income}* очков!\n💰 Всего: {p['total_score']}", parse_mode="Markdown")

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
        await query.edit_message_text(f"⏭ Пропущено (было: *{old}*).\nКатегория: {cat}", parse_mode="Markdown", reply_markup=make_croc_kb())
        task=asyncio.create_task(croc_timer(chat_id,ctx)); game["timer_task"]=task

    elif data=="croc_stop":
        game=games.get(chat_id)
        if not game or not game.get("active"): return
        if user.id!=game["explainer_id"]: await query.answer("Только объясняющий!",show_alert=True); return
        if game["timer_task"]: game["timer_task"].cancel()
        game["active"]=False
        await query.edit_message_text(f"🛑 Стоп.\nСлово: *{game['word'].upper()}*", parse_mode="Markdown")

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
            p["achievements"].add("jackpot")
            await reply(f"💥 *ДЖЕКПОТ!* {user.first_name} +{jackpot}!!!\n\nСлово: `{display_word(game['word'],game['guessed'])}`", parse_mode="Markdown", reply_markup=make_wheel_kb())
        else: game["drum_value"]=result; await reply(f"🎡 *{user.first_name}* крутит: *{result}* оч!\nНазови букву:", parse_mode="Markdown")

    elif data=="wheel_stop":
        game=wheel_games.get(chat_id)
        if not game or not game.get("active"): return
        if game["timer_task"]: game["timer_task"].cancel()
        game["active"]=False
        await query.edit_message_text(f"🛑 Стоп.\nСлово: *{game['word'].upper()}*", parse_mode="Markdown")

    # ── Блэкджек ──
    elif data=="bj_hit":
        game=blackjack_games.get(chat_id)
        if not game or not game.get("active"): return
        if user.id!=game["player_id"]: await query.answer("Не твоя!",show_alert=True); return
        game["hand"].append(deal_card()); val=card_value(game["hand"])
        if val>21:
            game["active"]=False; p["total_score"]=max(0,p["total_score"]-50)
            await query.edit_message_text(f"🃏 {hand_str(game['hand'])}\n\n💥 *Перебор!* -50\nВсего: {p['total_score']}\n\n🃏 /blackjack", parse_mode="Markdown")
        else: await query.edit_message_text(f"🃏 {hand_str(game['hand'])}\nДилер: {game['dealer'][0]} + ?\n\nЕщё или хватит?", parse_mode="Markdown", reply_markup=make_bj_kb())

    elif data=="bj_stand":
        game=blackjack_games.get(chat_id)
        if not game or not game.get("active"): return
        if user.id!=game["player_id"]: await query.answer("Не твоя!",show_alert=True); return
        game["active"]=False; dealer=game["dealer"]
        while card_value(dealer)<17: dealer.append(deal_card())
        pval=card_value(game["hand"]); dval=card_value(dealer)
        p["total_score"]=max(0,p["total_score"]-50)
        if dval>21 or pval>dval: add_score(user.id,user.first_name,100); p["wins"]+=1; result="🎉 *Победа!* +100"
        elif pval==dval: add_score(user.id,user.first_name,50); result="🤝 *Ничья!* +50"
        else: result="😔 *Дилер победил!* -50"
        await query.edit_message_text(f"🃏 Ты: {hand_str(game['hand'])}\nДилер: {hand_str(dealer)}\n\n{result}\nВсего: {p['total_score']}\n\n🃏 /blackjack", parse_mode="Markdown")

    # ── Дуэль ──
    elif data.startswith("duel_accept_"):
        cid=int(data.split("_")[2]); game=duel_games.get(chat_id)
        if not game or not game.get("active"): return
        if user.id!=game["opponent_id"]: await query.answer("Не твоя!",show_alert=True); return
        game["active"]=False
        cp=get_player(cid,game["challenger_name"]); op=p
        if cp["total_score"]<100 or op["total_score"]<100: await query.edit_message_text("❌ Не хватает очков!"); return
        wname=random.choice([game["challenger_name"],game["opponent_name"]])
        lname=game["opponent_name"] if wname==game["challenger_name"] else game["challenger_name"]
        wid=cid if wname==game["challenger_name"] else user.id
        lid=user.id if wname==game["challenger_name"] else cid
        add_score(wid,wname,100); get_player(lid,lname)["total_score"]=max(0,get_player(lid,lname)["total_score"]-100)
        get_player(wid,wname)["wins"]+=1; get_player(wid,wname)["duel_wins"]=get_player(wid,wname).get("duel_wins",0)+1
        await query.edit_message_text(f"⚔️ *ДУЭЛЬ!*\n\n🏆 *{wname}* победил! +100\n😔 *{lname}* -100\n\n📊 {global_scores_text()}", parse_mode="Markdown")

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
        n=random.randint(0,36)
        actual="🟢 Зеро" if n==0 else ("⚫ Чёрное" if n%2==0 else "🔴 Красное")
        bet={"rou_red":"🔴 Красное","rou_black":"⚫ Чёрное","rou_zero":"🟢 Зеро"}[data]
        if bet==actual:
            prize=350 if data=="rou_zero" else 100; add_score(user.id,user.first_name,prize); p["wins"]+=1
            await query.edit_message_text(f"🎯 Выпало: {actual} ({n})\nСтавка: {bet}\n\n🎉 *+{prize} оч!*\nВсего: {p['total_score']}", parse_mode="Markdown")
        else: await query.edit_message_text(f"🎯 Выпало: {actual} ({n})\nСтавка: {bet}\n\n😔 -100\nВсего: {p['total_score']}\n\n🎯 /roulette", parse_mode="Markdown")

    # ── Кубик ──
    elif data=="dice_roll":
        game=dice_games.get(chat_id)
        if not game or not game.get("active"): return
        if user.id!=game["player_id"]: await query.answer("Не твоя!",show_alert=True); return
        game["active"]=False; val=random.randint(1,6)
        faces=["","⚀","⚁","⚂","⚃","⚄","⚅"]
        if val==6: add_score(user.id,user.first_name,200); p["wins"]+=1; res="🎉 *ШЕСТЁРКА!* +200!"
        elif val==1: p["total_score"]=max(0,p["total_score"]-50); res="😔 *Единица!* -50!"
        else: res=f"🤷 *{val}* — ничего."
        await query.edit_message_text(f"🎲 {faces[val]} *{val}*\n\n{res}\nВсего: {p['total_score']}\n\n🎲 /dice", parse_mode="Markdown")

    # ── Покер ──
    elif data=="poker_continue":
        hand=ctx.chat_data.get("poker_hand",[])
        if not hand: await query.edit_message_text("Ошибка! /poker заново."); return
        pid,pname=ctx.chat_data.get("poker_player",(user.id,user.first_name))
        pp=get_player(pid,pname); pp["total_score"]=max(0,pp["total_score"]-100)
        val=card_value(hand[:2]); dh=[deal_card(),deal_card(),deal_card(),deal_card(),deal_card()]; dval=card_value(dh[:2])
        if val>dval or val==21: add_score(pid,pname,200); pp["wins"]+=1; pp["achievements"].add("poker_win"); res="🎉 *Победа!* +200"
        elif val==dval: add_score(pid,pname,100); res="🤝 *Ничья!* +100"
        else: res="😔 *Дилер победил!* -100"
        await query.edit_message_text(f"♠️ Ты: {' '.join(hand)}\nДилер: {' '.join(dh)}\n\n{res}\nВсего: {pp['total_score']}", parse_mode="Markdown")

    elif data=="poker_fold":
        p["total_score"]=max(0,p["total_score"]-50)
        await query.edit_message_text(f"♠️ Сбросил. -50\nВсего: {p['total_score']}\n\n♠️ /poker", parse_mode="Markdown")

    # ── УНО ──
    elif data=="uno_draw":
        game=uno_games.get(chat_id)
        if not game or not game.get("active"): return
        curr_id=game["players"][game["current"]%len(game["players"])][0]
        if user.id!=curr_id: await query.answer("Не твой ход!",show_alert=True); return
        if not game["deck"]: game["deck"]=make_uno_deck()
        card=game["deck"].pop(); game["hands"].setdefault(user.id,[]).append(card)
        try: await ctx.bot.send_message(chat_id=user.id, text=f"🃏 Взял: *{card}*\nТвои: {' '.join(game['hands'][user.id])}", parse_mode="Markdown")
        except: pass
        await reply(f"🃏 *{user.first_name}* берёт карту.\nВерхняя: {game['top_card']}", parse_mode="Markdown")

    elif data=="uno_show":
        game=uno_games.get(chat_id)
        if not game: return
        hand=game["hands"].get(user.id,[])
        try: await ctx.bot.send_message(chat_id=user.id, text=f"🃏 *Твои карты:*\n{' '.join(hand) if hand else 'Нет карт!'}", parse_mode="Markdown")
        except: await query.answer("Напиши /start боту в личку!",show_alert=True)

    # ── Магазин ──
    elif data.startswith("shop_"):
        key=data[5:]
        if key not in SHOP_ITEMS: return
        icon,name,desc,orig_price=SHOP_ITEMS[key]; price=shop_price(key)
        if p["total_score"]<price: await query.answer(f"Нужно {price} оч! У тебя {p['total_score']}",show_alert=True); return
        p["shop_purchases"]=p.get("shop_purchases",0)+1; check_achievements(user.id,user.first_name)

        if key=="vip":
            if p["vip"]: await query.answer("Уже есть!",show_alert=True); return
            p["total_score"]-=price; p["vip"]=True; p["achievements"].add("vip_buyer")
            await reply(f"👑 *{user.first_name}* получает VIP!", parse_mode="Markdown")
        elif key=="speedrun":
            if p["speedrun_access"]: await query.answer("Уже есть!",show_alert=True); return
            p["total_score"]-=price; p["speedrun_access"]=True; p["achievements"].add("speedrunner")
            await reply(f"⚡ *{user.first_name}* открыл Спидран!", parse_mode="Markdown")
        elif key=="bar_vip":
            if p.get("bar_vip"): await query.answer("Уже есть!",show_alert=True); return
            p["total_score"]-=price; p["bar_vip"]=True
            await reply(f"🍸 *{user.first_name}* — VIP в баре! Скидка 50% навсегда!", parse_mode="Markdown")
        elif key=="hint":
            game=wheel_games.get(chat_id)
            if not game or not game.get("active"): await query.answer("Нет Поля чудес!",show_alert=True); return
            hidden=[c for c in game["word"] if c not in game["guessed"] and c!=" "]
            if not hidden: await query.answer("Все открыты!",show_alert=True); return
            letter=random.choice(hidden); game["guessed"].add(letter); p["total_score"]-=price
            await reply(f"💡 *{user.first_name}* открывает *{letter.upper()}* (-{price})\n\n", parse_mode="Markdown")
def main():async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    chat_id = update.effective_chat.id; user = update.effective_user
    text = update.message.text.strip().lower()
    p = get_player(user.id, user.first_name)

    # Математика
    if ctx.chat_data.get("math_active") and text.lstrip("-").isdigit():
        if text == ctx.chat_data.get("math_answer"):
            ctx.chat_data["math_active"] = False
            add_score(user.id, user.first_name, 80)
            await update.message.reply_text(f"🎉 *Верно!* +80 оч!\n💰 Всего: {p['total_score']}", parse_mode="Markdown")
        return

    # Угадай число
    game = number_games.get(chat_id)
    if game and game.get("active") and text.lstrip("-").isdigit():
        guess = int(text)
        if guess == game["number"]:
            game["active"] = False
            if game.get("timer_task"): game["timer_task"].cancel()
            add_score(user.id, user.first_name, 100); p["wins"] += 1
            await update.message.reply_text(f"🎉 *{user.first_name}* угадал(а)! Число: {game['number']}\n+100 оч!\n\n🔢 /number", parse_mode="Markdown")
        elif guess < game["number"]:
            await update.message.reply_text("⬆️ Больше!")
        else:
            await update.message.reply_text("⬇️ Меньше!")
        return

    # Крокодил — угадывание слова (любой, кроме объясняющего)
    game = games.get(chat_id)
    if game and game.get("active") and user.id != game["explainer_id"]:
        if text == game["word"]:
            game["active"] = False
            if game.get("timer_task"): game["timer_task"].cancel()
            add_score(user.id, user.first_name, 150); p["wins"] += 1
            add_score(game["explainer_id"], game["explainer_name"], 50)
            await update.message.reply_text(f"🎉 *{user.first_name}* угадал(а)! Слово: *{game['word'].upper()}*\n+150 оч! (объясняющему +50)\n\n🐊 /game", parse_mode="Markdown")
            return

    # Поле чудес — буква или слово
    game = wheel_games.get(chat_id)
    if game and game.get("active") and game.get("drum_value") is not None:
        if len(text) == 1 and text.isalpha():
            letter = text
            if letter in game["word"]:
                mult = 2 if game["drum_value"] == "x2" else 1
                value = 100 if game["drum_value"] == "x2" else game["drum_value"]
                count = game["word"].count(letter)
                points = value * count * mult
                game["guessed"].add(letter)
                game["round_scores"][user.id] = game["round_scores"].get(user.id, 0) + points
                game["drum_value"] = None
                shown = display_word(game["word"], game["guessed"])
                if "_" not in shown.replace(" ", ""):
                    game["active"] = False
                    if game.get("timer_task"): game["timer_task"].cancel()
                    total = game["round_scores"].get(user.id, 0) + 500
                    add_score(user.id, user.first_name, total); p["wins"] += 1
                    await update.message.reply_text(f"🎉 *{user.first_name}* отгадал(а) слово целиком!\nСлово: *{game['word'].upper()}*\n+{total} оч!\n\n🎡 /wheel", parse_mode="Markdown")
                else:
                    await update.message.reply_text(f"✅ Буква *{letter.upper()}* есть! +{points} оч\nСлово: `{shown}`", parse_mode="Markdown", reply_markup=make_wheel_kb())
            else:
                game["wrong_letters"].add(letter); game["drum_value"] = None
                add_score(user.id, user.first_name, -100)
                await update.message.reply_text(f"❌ Буквы *{letter.upper()}* нет! -100 оч\nСлово: `{display_word(game['word'], game['guessed'])}`", parse_mode="Markdown", reply_markup=make_wheel_kb())
        elif len(text) > 1:
            if text == game["word"]:
                game["active"] = False
                if game.get("timer_task"): game["timer_task"].cancel()
                total = game["round_scores"].get(user.id, 0) + 500
                add_score(user.id, user.first_name, total); p["wins"] += 1
                await update.message.reply_text(f"🎉 *{user.first_name}* отгадал(а) слово!\n+{total} оч!\n\n🎡 /wheel", parse_mode="Markdown")
            else:
                add_score(user.id, user.first_name, -150)
                await update.message.reply_text(f"❌ Неверно! -150 оч\n\n🎡 /wheel", parse_mode="Markdown")
        return

    # Виселица
    game = hangman_games.get(chat_id)
    if game and game.get("active") and len(text) == 1 and text.isalpha():
        letter = text
        if letter not in game["guessed"]:
            game["guessed"].add(letter)
            if letter in game["word"]:
                add_score(user.id, user.first_name, 50)
                shown = display_word(game["word"], game["guessed"])
                if "_" not in shown.replace(" ", ""):
                    game["active"] = False
                    if game.get("timer_task"): game["timer_task"].cancel()
                    add_score(user.id, user.first_name, 200); p["wins"] += 1
                    await update.message.reply_text(f"🎉 *{user.first_name}* отгадал(а) слово: *{game['word'].upper()}*!\n+250 оч всего!\n\n📝 /hangman", parse_mode="Markdown")
                else:
                    await update.message.reply_text(f"✅ Буква есть! +50\nСлово: `{shown}`", parse_mode="Markdown")
            else:
                game["errors"] += 1
                pic_idx = min(game["errors"], len(HANGMAN_PICS) - 1)
                if game["errors"] >= game["max_errors"]:
                    game["active"] = False
                    if game.get("timer_task"): game["timer_task"].cancel()
                    await update.message.reply_text(f"{HANGMAN_PICS[-1]} *Проигрыш!* Слово было: *{game['word'].upper()}*\n\n📝 /hangman", parse_mode="Markdown")
                else:
                    await update.message.reply_text(f"{HANGMAN_PICS[pic_idx]} Нет такой буквы! Осталось попыток: {game['max_errors']-game['errors']}\nСлово: `{display_word(game['word'], game['guessed'])}`", parse_mode="Markdown")
        return

    # Спидран
    game = speed_games.get(chat_id)
    if game and game.get("active") and user.id == game["player_id"]:
        if text == game["word"]:
            game["count"] += 1
            game["word"] = random.choice(SPEEDRUN_WORDS)
            await update.message.reply_text(f"✅ Верно! Дальше: `{'_ '*len(game['word'])}` ({len(game['word'])} букв)")
        return
    
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("profile", cmd_profile))
    app.add_handler(CommandHandler("achievements", cmd_achievements))
    app.add_handler(CommandHandler("inventory", cmd_inventory))
    app.add_handler(CommandHandler("daily", cmd_daily))
    app.add_handler(CommandHandler("scores", cmd_scores))
    app.add_handler(CommandHandler("shop", cmd_shop))
    app.add_handler(CommandHandler("bar", cmd_bar))
    app.add_handler(CommandHandler("farm", cmd_farm))
    app.add_handler(CommandHandler("game", cmd_game))
    app.add_handler(CommandHandler("wheel", cmd_wheel))
    app.add_handler(CommandHandler("speedrun", cmd_speedrun))
    app.add_handler(CommandHandler("trivia", cmd_trivia))
    app.add_handler(CommandHandler("hangman", cmd_hangman))
    app.add_handler(CommandHandler("number", cmd_number))
    app.add_handler(CommandHandler("blackjack", cmd_blackjack))
    app.add_handler(CommandHandler("slots", cmd_slots))
    app.add_handler(CommandHandler("tod", cmd_tod))
    app.add_handler(CommandHandler("duel", cmd_duel))
    app.add_handler(CommandHandler("roulette", cmd_roulette))
    app.add_handler(CommandHandler("dice", cmd_dice))
    app.add_handler(CommandHandler("uno", cmd_uno))
    app.add_handler(CommandHandler("poker", cmd_poker))
    app.add_handler(CommandHandler("tournament", cmd_tournament))
    app.add_handler(CommandHandler("math", cmd_math))
    app.add_handler(CommandHandler("join", cmd_join))
    app.add_handler(CommandHandler("stopbot", cmd_stopbot))

    app.add_handler(CallbackQueryHandler(callback_handler))app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(ChatMemberHandler(greet_new_group, ChatMemberHandler.MY_CHAT_MEMBER))

    app.post_init = setup_commands

    print("Bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
