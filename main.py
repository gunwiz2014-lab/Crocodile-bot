import os
import random
import asyncio
from datetime import date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, BotCommandScopeAllGroupChats, BotCommandScopeAllPrivateChats
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ChatMemberHandler
)

BOT_TOKEN = os.getenv("BOT_TOKEN", "ВСТАВЬТЕ_ТОКЕН_СЮДА")
BOT_USERNAME = os.getenv("BOT_USERNAME", "Vhfbju_bot")

WORDS = {
    "🐾 Животные": ["жираф", "дельфин", "кенгуру", "хамелеон", "утконос",
                    "броненосец", "ленивец", "осьминог", "пингвин", "фламинго",
                    "крокодил", "летучая мышь", "морж", "енот", "капибара"],
    "🍕 Еда": ["пицца", "суши", "борщ", "шаурма", "мороженое",
               "чизкейк", "круассан", "лазанья", "такос", "вафли",
               "мармелад", "шоколад", "пельмени", "блин", "бургер"],
    "🎬 Фильмы": ["матрица", "титаник", "аватар", "интерстеллар", "джокер",
                  "начало", "гладиатор", "дюна", "оппенгеймер", "паразиты"],
    "🌍 Места": ["эйфелева башня", "колизей", "мачу-пикчу", "байкал", "сахара",
                 "антарктида", "амазонка", "мальдивы", "стоунхендж", "кремль"],
    "🎭 Профессии": ["пожарный", "астронавт", "дирижёр", "детектив", "ветеринар",
                     "повар", "архитектор", "скульптор", "дайвер", "каскадёр"],
    "🎲 Разное": ["радуга", "землетрясение", "телепортация", "гравитация", "эхо",
                  "сновидение", "вулкан", "торнадо", "молния", "мираж"],
    "🏆 Спорт": ["футбол", "баскетбол", "теннис", "бокс", "плавание",
                 "гимнастика", "хоккей", "велоспорт", "борьба", "лыжи"],
    "🎵 Музыка": ["гитара", "пианино", "барабаны", "скрипка", "флейта",
                  "микрофон", "наушники", "концерт", "дирижёр", "опера"],
}

SPEEDRUN_WORDS = ["кот", "дом", "лес", "море", "гора", "река", "небо", "снег", "огонь", "вода",
    "хлеб", "соль", "свет", "тень", "мост", "дорога", "птица", "рыба", "конь", "волк",
    "медведь", "лиса", "заяц", "орёл", "змея", "черепаха", "бабочка", "цветок", "дерево", "камень",
    "корабль", "самолёт", "машина", "велосипед", "поезд", "ракета", "замок", "башня", "стена", "окно"]

TRIVIA = [
    {"q": "Столица Франции?", "a": "париж"},
    {"q": "Сколько планет в Солнечной системе?", "a": "8"},
    {"q": "Какой самый большой океан?", "a": "тихий"},
    {"q": "Кто написал 'Войну и мир'?", "a": "толстой"},
    {"q": "Самая длинная река в мире?", "a": "нил"},
    {"q": "Сколько цветов в радуге?", "a": "7"},
    {"q": "Столица Японии?", "a": "токио"},
    {"q": "Кто написал 'Гарри Поттера'?", "a": "роулинг"},
    {"q": "Сколько букв в русском алфавите?", "a": "33"},
    {"q": "Самая высокая гора в мире?", "a": "эверест"},
    {"q": "Столица России?", "a": "москва"},
    {"q": "Кто написал 'Мастер и Маргарита'?", "a": "булгаков"},
    {"q": "Сколько сторон у шестиугольника?", "a": "6"},
    {"q": "Столица Германии?", "a": "берлин"},
    {"q": "Какая планета ближайшая к Солнцу?", "a": "меркурий"},
    {"q": "Сколько нот в октаве?", "a": "7"},
    {"q": "Кто изобрёл телефон?", "a": "белл"},
    {"q": "Столица Италии?", "a": "рим"},
    {"q": "Сколько континентов на Земле?", "a": "6"},
    {"q": "Химический символ золота?", "a": "au"},
]

TOD_TRUTHS = [
    "Какой твой самый большой страх?",
    "Кто тебе нравится в этом чате?",
    "Какой твой самый неловкий момент?",
    "Что ты никогда не признаешь публично?",
    "Какая твоя самая большая ложь?",
    "Кому из чата ты бы позвонил в 3 ночи?",
    "Что ты скрываешь от родителей?",
    "Какой твой самый странный сон?",
    "Во что ты веришь, но стесняешься говорить?",
    "Какой поступок ты больше всего хотел бы отменить?",
]

TOD_DARES = [
    "Напиши комплимент каждому в чате!",
    "Расскажи смешную историю из жизни",
    "Напиши что-нибудь задом наперёд",
    "Придумай стих про кого-нибудь в чате",
    "Напиши следующее сообщение только капслоком",
    "Признайся в чём-нибудь смешном",
    "Отправь голосовое сообщение (можешь сказать любую чушь)",
    "Напиши имя своего краша 👀",
    "Расскажи самый стыдный момент в жизни",
    "Напиши комплимент человеку над тобой в чате",
]

DRUM = [100, 100, 200, 200, 300, 300, 500, 500, 1000, "БАНКРОТ", "БАНКРОТ", "ПРИЗ"]
SLOT_SYMBOLS = ["🍒", "🍋", "🔔", "⭐", "💎", "7️⃣"]
HANGMAN_PICS = ["😀", "😟", "😰", "😨", "😱", "💀"]

CARDS = ["2","3","4","5","6","7","8","9","10","J","Q","K","A"]
CARD_VALS = {"2":2,"3":3,"4":4,"5":5,"6":6,"7":7,"8":8,"9":9,"10":10,"J":10,"Q":10,"K":10,"A":11}

ACHIEVEMENTS = {
    "first_win": ("🏆", "Первая победа", "Выиграй первый раунд"),
    "streak3": ("🔥", "В огне", "3 буквы подряд в Поле чудес"),
    "rich": ("💰", "Богач", "Накопи 1000 очков"),
    "collector": ("🎮", "Геймер", "Сыграй в 5 разных игр"),
    "vip_buyer": ("👑", "VIP", "Купи VIP статус"),
    "speedrunner": ("⚡", "Спидраннер", "Купи доступ к спидрану"),
    "blackjack21": ("🃏", "Удача 21", "Набери ровно 21 в блэкджеке"),
    "lucky_slots": ("🎰", "Удачливый", "Выиграй в слоты"),
    "winner10": ("🥇", "Чемпион", "Выиграй 10 раз"),
    "daily7": ("📅", "Постоянный", "7 дней подряд ежедневный бонус"),
}

TITLES = [
    (0, "🐣 Новичок"), (100, "🌱 Начинающий"), (300, "⚔️ Игрок"),
    (500, "🎯 Опытный"), (1000, "🔥 Мастер"), (2000, "💎 Элита"), (5000, "👑 Легенда"),
]

SHOP_ITEMS = {
    "hint": ("💡", "Подсказка", "Открыть букву в Поле чудес", 200),
    "protection": ("🛡", "Защита", "Следующий банкрот не сработает", 400),
    "double": ("🎯", "Удвоение", "Следующая буква x2", 500),
    "sabotage": ("💣", "Диверсия", "Враг пропускает ход", 350),
    "vip": ("👑", "VIP статус", "Значок в таблице очков", 1000),
    "speedrun": ("⚡", "Спидран", "Открыть режим спидрана", 750),
    "extra_life": ("❤️", "Жизнь в виселице", "Доп. попытка в виселице", 300),
    "time_bonus": ("⏱", "Доп. время", "+30 сек в любой игре", 250),
    "double_daily": ("🎁", "Двойной бонус", "x2 к ежедневному бонусу", 500),
    "lottery": ("🎟", "Лотерея", "Случайный приз 50-500 очков", 150),
}

ROUND_TIME_CROC = 60
ROUND_TIME_WHEEL = 300
SPEEDRUN_TIME = 30
TRIVIA_TIME = 20
HANGMAN_TIME = 120
NUMBER_TIME = 60

games = {}
wheel_games = {}
speed_games = {}
trivia_games = {}
hangman_games = {}
number_games = {}
blackjack_games = {}
duel_games = {}
players = {}
group_players = {}


def get_player(user_id, name):
    if user_id not in players:
        players[user_id] = {
            "name": name, "total_score": 0,
            "speedrun_access": False, "vip": False,
            "streak": 0, "protection": False, "double": False,
            "extra_life": False, "time_bonus": False, "double_daily": False,
            "achievements": set(), "games_played": set(),
            "wins": 0, "last_daily": None, "daily_streak": 0,
            "inventory": {},
        }
    players[user_id]["name"] = name
    return players[user_id]


def add_score(user_id, name, amount):
    p = get_player(user_id, name)
    p["total_score"] = max(0, p["total_score"] + amount)
    check_achievements(user_id, name)


def check_achievements(user_id, name):
    p = get_player(user_id, name)
    new = []
    checks = [
        ("first_win", p["wins"] >= 1),
        ("rich", p["total_score"] >= 1000),
        ("collector", len(p["games_played"]) >= 5),
        ("winner10", p["wins"] >= 10),
    ]
    for key, cond in checks:
        if cond and key not in p["achievements"]:
            p["achievements"].add(key); new.append(key)
    return new


def get_title(score):
    title = TITLES[0][1]
    for threshold, t in TITLES:
        if score >= threshold: title = t
    return title


def global_scores_text():
    if not players: return "Пока никто не набрал очков."
    sorted_p = sorted(players.values(), key=lambda x: x["total_score"], reverse=True)
    medals = ["🥇", "🥈", "🥉"]
    lines = []
    for i, p in enumerate(sorted_p[:10]):
        medal = medals[i] if i < 3 else f"{i+1}."
        vip = " 👑" if p["vip"] else ""
        title = get_title(p["total_score"])
        lines.append(f"{medal} {p['name']}{vip} {title} — {p['total_score']} оч.")
    return "\n".join(lines)


def display_word(word, guessed):
    return " ".join(c if c in guessed or c == " " else "\\_" for c in word)


def spin_drum(): return random.choice(DRUM)

def spin_slots(): return [random.choice(SLOT_SYMBOLS) for _ in range(3)]

def check_slots(symbols):
    if symbols[0] == symbols[1] == symbols[2]:
        prizes = {"💎": 1000, "7️⃣": 777, "⭐": 500, "🔔": 300, "🍋": 200, "🍒": 150}
        return prizes.get(symbols[0], 200)
    if len(set(symbols)) < 3: return 50
    return 0

def card_value(hand):
    val = sum(CARD_VALS[c] for c in hand)
    aces = hand.count("A")
    while val > 21 and aces: val -= 10; aces -= 1
    return val

def deal_card(): return random.choice(CARDS)
def hand_str(hand): return " ".join(hand) + f" (={card_value(hand)})"
def is_group(chat): return chat.type in ("group", "supergroup")


# ─── КЛАВИАТУРЫ ───────────────────────────────────────────────────────────────
def make_main_keyboard(group=False):
    rows = [
        [InlineKeyboardButton("🐊 Крокодил", callback_data="menu_game"),
         InlineKeyboardButton("🎡 Поле чудес", callback_data="menu_wheel")],
        [InlineKeyboardButton("⚡ Спидран", callback_data="menu_speedrun"),
         InlineKeyboardButton("🧠 Викторина", callback_data="menu_trivia")],
        [InlineKeyboardButton("📝 Виселица", callback_data="menu_hangman"),
         InlineKeyboardButton("🔢 Угадай число", callback_data="menu_number")],
        [InlineKeyboardButton("🃏 Блэкджек", callback_data="menu_blackjack"),
         InlineKeyboardButton("🎰 Слоты", callback_data="menu_slots")],
        [InlineKeyboardButton("❓ Правда/Действие", callback_data="menu_tod"),
         InlineKeyboardButton("⚔️ Дуэль", callback_data="menu_duel")],
        [InlineKeyboardButton("🛒 Магазин", callback_data="menu_shop"),
         InlineKeyboardButton("📊 Счёт", callback_data="menu_scores")],
        [InlineKeyboardButton("🏆 Достижения", callback_data="menu_achievements"),
         InlineKeyboardButton("🎁 Бонус", callback_data="menu_daily")],
        [InlineKeyboardButton("👤 Профиль", callback_data="menu_profile"),
         InlineKeyboardButton("🎒 Инвентарь", callback_data="menu_inventory")],
    ]
    if group:
        rows.append([InlineKeyboardButton("✋ Присоединиться к игре", callback_data="menu_join")])
    else:
        rows.insert(0, [InlineKeyboardButton(
            "➕ Добавить бота в группу",
            url=f"https://t.me/{BOT_USERNAME}?startgroup=true"
        )])
    return InlineKeyboardMarkup(rows)


def make_croc_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("⏭ Пропустить", callback_data="croc_skip"),
        InlineKeyboardButton("🛑 Стоп", callback_data="croc_stop"),
    ]])

def make_wheel_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🎡 Крутить барабан", callback_data="wheel_spin"),
        InlineKeyboardButton("🛑 Стоп", callback_data="wheel_stop"),
    ]])

def make_blackjack_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🃏 Ещё карту", callback_data="bj_hit"),
        InlineKeyboardButton("✋ Хватит", callback_data="bj_stand"),
    ]])

def make_duel_keyboard(challenger_id):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("⚔️ Принять!", callback_data=f"duel_accept_{challenger_id}"),
        InlineKeyboardButton("❌ Отказать", callback_data="duel_decline"),
    ]])

def make_shop_keyboard(p):
    rows = []
    for key, (icon, name, desc, price) in SHOP_ITEMS.items():
        owned = ""
        if key == "vip" and p.get("vip"): owned = " ✅"
        if key == "speedrun" and p.get("speedrun_access"): owned = " ✅"
        rows.append([InlineKeyboardButton(
            f"{icon} {name}{owned} — {price} оч.", callback_data=f"shop_{key}")])
    rows.append([InlineKeyboardButton("🔙 Назад", callback_data="menu_back")])
    return InlineKeyboardMarkup(rows)


# ─── SETUP COMMANDS ───────────────────────────────────────────────────────────
async def setup_commands(app):
    private_commands = [
        BotCommand("start", "🎮 Главное меню"),
        BotCommand("profile", "👤 Мой профиль"),
        BotCommand("achievements", "🏆 Достижения"),
        BotCommand("inventory", "🎒 Инвентарь"),
        BotCommand("daily", "🎁 Ежедневный бонус"),
        BotCommand("scores", "📊 Таблица очков"),
        BotCommand("shop", "🛒 Магазин"),
        BotCommand("game", "🐊 Крокодил"),
        BotCommand("wheel", "🎡 Поле чудес"),
        BotCommand("speedrun", "⚡ Спидран"),
        BotCommand("trivia", "🧠 Викторина"),
        BotCommand("hangman", "📝 Виселица"),
        BotCommand("number", "🔢 Угадай число"),
        BotCommand("blackjack", "🃏 Блэкджек"),
        BotCommand("slots", "🎰 Слоты"),
        BotCommand("tod", "❓ Правда или Действие"),
        BotCommand("help", "❓ Правила всех игр"),
    ]
    group_commands = [
        BotCommand("start", "🎮 Главное меню"),
        BotCommand("join", "✋ Присоединиться к игре"),
        BotCommand("game", "🐊 Крокодил"),
        BotCommand("wheel", "🎡 Поле чудес"),
        BotCommand("speedrun", "⚡ Спидран"),
        BotCommand("trivia", "🧠 Викторина"),
        BotCommand("hangman", "📝 Виселица"),
        BotCommand("number", "🔢 Угадай число"),
        BotCommand("blackjack", "🃏 Блэкджек"),
        BotCommand("slots", "🎰 Слоты"),
        BotCommand("tod", "❓ Правда или Действие"),
        BotCommand("duel", "⚔️ Дуэль (ответь на сообщение)"),
        BotCommand("daily", "🎁 Ежедневный бонус"),
        BotCommand("scores", "📊 Таблица очков"),
        BotCommand("profile", "👤 Мой профиль"),
        BotCommand("shop", "🛒 Магазин"),
        BotCommand("help", "❓ Правила"),
    ]
    await app.bot.set_my_commands(private_commands, scope=BotCommandScopeAllPrivateChats())
    await app.bot.set_my_commands(group_commands, scope=BotCommandScopeAllGroupChats())


async def greet_new_group(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    result = update.my_chat_member
    if not result: return
    old = result.old_chat_member.status
    new = result.new_chat_member.status
    if old in ("left", "kicked") and new in ("member", "administrator"):
        chat = update.effective_chat
        await ctx.bot.send_message(
            chat_id=chat.id,
            text=f"👋 Привет, *{chat.title}*!\n\n"
                 f"🎮 Я игровой бот — 10 игр для всей группы!\n\n"
                 f"🐊 Крокодил | 🎡 Поле чудес | ⚡ Спидран\n"
                 f"🧠 Викторина | 📝 Виселица | 🔢 Угадай число\n"
                 f"🃏 Блэкджек | 🎰 Слоты | ❓ Правда/Действие | ⚔️ Дуэль\n\n"
                 f"🏆 Достижения | 🎁 Бонусы | 👑 Титулы | 🎒 Инвентарь\n\n"
                 f"✋ Нажмите *Присоединиться* и выбирайте игру!",
            parse_mode="Markdown",
            reply_markup=make_main_keyboard(group=True)
        )


# ─── КОМАНДЫ ──────────────────────────────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    p = get_player(user.id, user.first_name)
    g = is_group(chat)
    title = get_title(p["total_score"])
    await update.message.reply_text(
        f"👋 Привет, *{user.first_name}*! {title}\n\n"
        f"🎮 *Игровой бот* — 10 игр в одном!\n\n"
        f"💰 Очков: *{p['total_score']}* | 🏆 Побед: {p['wins']}\n\n"
        f"{'✋ Нажми Присоединиться! 👇' if g else 'Добавь бота в группу и играй с друзьями! 👇'}",
        parse_mode="Markdown",
        reply_markup=make_main_keyboard(group=g)
    )


async def cmd_profile(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    p = get_player(user.id, user.first_name)
    title = get_title(p["total_score"])
    achs = [f"{ACHIEVEMENTS[a][0]}" for a in p["achievements"] if a in ACHIEVEMENTS]
    inv = p.get("inventory", {})
    inv_text = ", ".join([f"{SHOP_ITEMS[k][0]}{v}шт" for k, v in inv.items() if v > 0]) or "пусто"
    await update.message.reply_text(
        f"👤 *{user.first_name}*\n\n"
        f"🏅 Титул: {title}\n"
        f"💰 Очки: *{p['total_score']}*\n"
        f"🏆 Победы: {p['wins']}\n"
        f"🎮 Игр: {len(p['games_played'])}\n"
        f"👑 VIP: {'Да' if p['vip'] else 'Нет'}\n"
        f"⚡ Спидран: {'Да' if p['speedrun_access'] else 'Нет'}\n\n"
        f"🏆 Достижения: {' '.join(achs) if achs else 'Нет'}\n\n"
        f"🎒 Инвентарь: {inv_text}",
        parse_mode="Markdown"
    )


async def cmd_achievements(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    p = get_player(user.id, user.first_name)
    lines = []
    for key, (icon, name, desc) in ACHIEVEMENTS.items():
        if key in p["achievements"]:
            lines.append(f"✅ {icon} *{name}* — {desc}")
        else:
            lines.append(f"🔒 {icon} {name} — {desc}")
    await update.message.reply_text(
        f"🏆 *Достижения {user.first_name}*\n\n" + "\n".join(lines),
        parse_mode="Markdown"
    )


async def cmd_inventory(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    p = get_player(user.id, user.first_name)
    inv = p.get("inventory", {})
    if not inv or all(v == 0 for v in inv.values()):
        await update.message.reply_text(
            "🎒 *Инвентарь пуст*\n\nКупи предметы в /shop!",
            parse_mode="Markdown"); return
    lines = []
    for key, count in inv.items():
        if count > 0 and key in SHOP_ITEMS:
            icon, name, desc, price = SHOP_ITEMS[key]
            lines.append(f"{icon} *{name}* x{count} — {desc}")
    await update.message.reply_text(
        f"🎒 *Инвентарь {user.first_name}*\n\n" + "\n".join(lines),
        parse_mode="Markdown"
    )


async def cmd_daily(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    p = get_player(user.id, user.first_name)
    today = date.today().isoformat()
    if p.get("last_daily") == today:
        await update.message.reply_text(
            "🎁 Уже получил бонус сегодня!\nПриходи завтра 😊", parse_mode="Markdown"); return
    bonus = random.randint(50, 300)
    if p.get("double_daily"):
        bonus *= 2; p["double_daily"] = False
    p["last_daily"] = today
    p["daily_streak"] = p.get("daily_streak", 0) + 1
    streak = p["daily_streak"]
    if streak >= 7 and "daily7" not in p["achievements"]:
        p["achievements"].add("daily7")
    add_score(user.id, user.first_name, bonus)
    streak_bonus = ""
    if streak > 1: streak_bonus = f"\n🔥 Серия {streak} дней! Так держать!"
    await update.message.reply_text(
        f"🎁 *Ежедневный бонус!*\n\n+*{bonus}* очков!{streak_bonus}\n\n💰 Всего: {p['total_score']}",
        parse_mode="Markdown"
    )


async def cmd_scores(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"📊 *Таблица очков*\n\n{global_scores_text()}", parse_mode="Markdown")


async def cmd_shop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    p = get_player(user.id, user.first_name)
    await update.message.reply_text(
        f"🛒 *Магазин*\n\nТвои очки: *{p['total_score']}*\n\nВыбери предмет:",
        parse_mode="Markdown", reply_markup=make_shop_keyboard(p))


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    g = is_group(update.effective_chat)
    await update.message.reply_text(
        "📖 *Все игры*\n\n"
        "🐊 /game — Крокодил (объясняй слова)\n"
        "🎡 /wheel — Поле чудес (барабан)\n"
        "⚡ /speedrun — Спидран (30 сек)\n"
        "🧠 /trivia — Викторина (+150 оч)\n"
        "📝 /hangman — Виселица (+200 оч)\n"
        "🔢 /number — Угадай число (+100 оч)\n"
        "🃏 /blackjack — Блэкджек (ставки)\n"
        "🎰 /slots — Слоты (-100 оч за спин)\n"
        "❓ /tod — Правда или Действие\n"
        "⚔️ /duel — Дуэль (ответь на сообщение)\n\n"
        "🎁 /daily — Ежедневный бонус\n"
        "🏆 /achievements — Достижения\n"
        "👤 /profile — Профиль\n"
        "🎒 /inventory — Инвентарь\n"
        "🛒 /shop — Магазин\n"
        "📊 /scores — Таблица очков",
        parse_mode="Markdown", reply_markup=make_main_keyboard(group=g))


async def cmd_join(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    get_player(user.id, user.first_name)
    if chat_id not in group_players: group_players[chat_id] = {}
    if user.id in group_players[chat_id]:
        await update.message.reply_text(f"✅ *{user.first_name}*, ты уже в игре!", parse_mode="Markdown"); return
    group_players[chat_id][user.id] = user.first_name
    names = ", ".join(group_players[chat_id].values())
    await update.message.reply_text(
        f"✋ *{user.first_name}* присоединился(ась)!\n👥 {names}\nВыбирайте игру!",
        parse_mode="Markdown", reply_markup=make_main_keyboard(group=True))


# ══════════════════════════════════════════════════════════════════════════════
# ИГРЫ — таймеры и запуски
# ══════════════════════════════════════════════════════════════════════════════
async def croc_timer(chat_id, ctx):
    await asyncio.sleep(ROUND_TIME_CROC)
    game = games.get(chat_id)
    if game and game.get("active"):
        game["active"] = False
        await ctx.bot.send_message(chat_id=chat_id,
            text=f"⏰ Время вышло!\nСлово: *{game['word'].upper()}*\n\n▶️ /game", parse_mode="Markdown")


async def start_croc(chat_id, user, ctx, reply_func):
    p = get_player(user.id, user.first_name); p["games_played"].add("croc")
    if chat_id in games and games[chat_id].get("timer_task"): games[chat_id]["timer_task"].cancel()
    category = random.choice(list(WORDS.keys()))
    word = random.choice(WORDS[category])
    games[chat_id] = {"word": word.lower(), "category": category,
        "explainer_id": user.id, "explainer_name": user.first_name, "active": True, "timer_task": None}
    try:
        await ctx.bot.send_message(chat_id=user.id,
            text=f"🐊 Твоё слово: *{word.upper()}*\nКатегория: {category}", parse_mode="Markdown")
        dm = f"✉️ Слово отправлено {user.first_name} в личку."
    except: dm = f"⚠️ {user.first_name}, напиши /start боту в личку!"
    await reply_func(f"🐊 *Крокодил!*\nОбъясняет: *{user.first_name}*\nКатегория: {category}\n\n{dm}\n\n⏱ {ROUND_TIME_CROC} сек!",
        parse_mode="Markdown", reply_markup=make_croc_keyboard())
    task = asyncio.create_task(croc_timer(chat_id, ctx))
    games[chat_id]["timer_task"] = task

async def cmd_game(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await start_croc(update.effective_chat.id, update.effective_user, ctx, update.message.reply_text)


async def wheel_timer(chat_id, ctx):
    await asyncio.sleep(ROUND_TIME_WHEEL)
    game = wheel_games.get(chat_id)
    if game and game.get("active"):
        game["active"] = False
        await ctx.bot.send_message(chat_id=chat_id,
            text=f"⏰ Время вышло!\nСлово: *{game['word'].upper()}*\n\n🎡 /wheel", parse_mode="Markdown")

async def start_wheel(chat_id, user, ctx, reply_func):
    p = get_player(user.id, user.first_name); p["games_played"].add("wheel")
    if chat_id in wheel_games and wheel_games[chat_id].get("timer_task"): wheel_games[chat_id]["timer_task"].cancel()
    category = random.choice(list(WORDS.keys()))
    word = random.choice(WORDS[category]).lower()
    wheel_games[chat_id] = {"word": word, "category": category, "guessed": set(), "wrong_letters": set(),
        "active": True, "round_scores": {}, "drum_value": None, "timer_task": None, "sabotage_target": None}
    shown = display_word(word, set())
    await reply_func(f"🎡 *Поле чудес!*\nКатегория: {category}\n\nСлово: `{shown}`\n\n"
        f"Нажмите барабан → назовите букву!\n❌ Буква: -100 | ❌ Слово: -150 | ✅ Слово: +500\n⏱ 5 мин!",
        parse_mode="Markdown", reply_markup=make_wheel_keyboard())
    task = asyncio.create_task(wheel_timer(chat_id, ctx))
    wheel_games[chat_id]["timer_task"] = task

async def cmd_wheel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await start_wheel(update.effective_chat.id, update.effective_user, ctx, update.message.reply_text)


async def speedrun_timer(chat_id, ctx):
    await asyncio.sleep(SPEEDRUN_TIME)
    game = speed_games.get(chat_id)
    if game and game.get("active"):
        game["active"] = False
        bonus = game["count"] * 50
        add_score(game["player_id"], game["player_name"], bonus)
        await ctx.bot.send_message(chat_id=chat_id,
            text=f"⏰ *Спидран!*\n*{game['player_name']}* угадал(а) {game['count']} слов!\n+{bonus} оч\n\n📊 /scores", parse_mode="Markdown")

async def start_speedrun(chat_id, user, ctx, reply_func):
    p = get_player(user.id, user.first_name); p["games_played"].add("speedrun")
    if not p["speedrun_access"]: await reply_func("⚡ Купи доступ в /shop за 750 очков!", parse_mode="Markdown"); return
    if chat_id in speed_games and speed_games[chat_id].get("active"): await reply_func("⚡ Спидран уже идёт!"); return
    word = random.choice(SPEEDRUN_WORDS)
    speed_games[chat_id] = {"word": word, "active": True, "player_id": user.id, "player_name": user.first_name, "count": 0, "timer_task": None}
    await reply_func(f"⚡ *СПИДРАН!* {user.first_name}\n30 сек!\n\nПервое: `{'_ ' * len(word)}`\nБукв: {len(word)}", parse_mode="Markdown")
    task = asyncio.create_task(speedrun_timer(chat_id, ctx))
    speed_games[chat_id]["timer_task"] = task

async def cmd_speedrun(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await start_speedrun(update.effective_chat.id, update.effective_user, ctx, update.message.reply_text)


async def trivia_timer(chat_id, ctx):
    await asyncio.sleep(TRIVIA_TIME)
    game = trivia_games.get(chat_id)
    if game and game.get("active"):
        game["active"] = False
        await ctx.bot.send_message(chat_id=chat_id,
            text=f"⏰ Время вышло!\nОтвет: *{game['answer'].upper()}*\n\n🧠 /trivia", parse_mode="Markdown")

async def start_trivia(chat_id, user, ctx, reply_func):
    get_player(user.id, user.first_name)["games_played"].add("trivia")
    if chat_id in trivia_games and trivia_games[chat_id].get("timer_task"): trivia_games[chat_id]["timer_task"].cancel()
    q = random.choice(TRIVIA)
    trivia_games[chat_id] = {"question": q["q"], "answer": q["a"], "active": True, "timer_task": None}
    await reply_func(f"🧠 *Викторина!*\n\n❓ {q['q']}\n\n⏱ {TRIVIA_TIME} сек | +150 очков", parse_mode="Markdown")
    task = asyncio.create_task(trivia_timer(chat_id, ctx))
    trivia_games[chat_id]["timer_task"] = task

async def cmd_trivia(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await start_trivia(update.effective_chat.id, update.effective_user, ctx, update.message.reply_text)


async def hangman_timer(chat_id, ctx):
    await asyncio.sleep(HANGMAN_TIME)
    game = hangman_games.get(chat_id)
    if game and game.get("active"):
        game["active"] = False
        await ctx.bot.send_message(chat_id=chat_id,
            text=f"⏰ Время вышло!\nСлово: *{game['word'].upper()}*\n\n📝 /hangman", parse_mode="Markdown")

async def start_hangman(chat_id, user, ctx, reply_func):
    p = get_player(user.id, user.first_name); p["games_played"].add("hangman")
    if chat_id in hangman_games and hangman_games[chat_id].get("timer_task"): hangman_games[chat_id]["timer_task"].cancel()
    category = random.choice(list(WORDS.keys()))
    word = random.choice(WORDS[category]).lower()
    max_errors = 7 if p.get("extra_life") else 6
    if p.get("extra_life"): p["extra_life"] = False
    hangman_games[chat_id] = {"word": word, "category": category, "guessed": set(),
        "errors": 0, "max_errors": max_errors, "active": True, "timer_task": None}
    shown = display_word(word, set())
    await reply_func(f"📝 *Виселица!*\nКатегория: {category}\n\n{HANGMAN_PICS[0]} Попыток: {max_errors}\n\n"
        f"Слово: `{shown}`\n\n+50 за букву, +200 за слово. ⏱ 2 мин!", parse_mode="Markdown")
    task = asyncio.create_task(hangman_timer(chat_id, ctx))
    hangman_games[chat_id]["timer_task"] = task

async def cmd_hangman(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await start_hangman(update.effective_chat.id, update.effective_user, ctx, update.message.reply_text)


async def number_timer(chat_id, ctx):
    await asyncio.sleep(NUMBER_TIME)
    game = number_games.get(chat_id)
    if game and game.get("active"):
        game["active"] = False
        await ctx.bot.send_message(chat_id=chat_id,
            text=f"⏰ Время вышло!\nЧисло: *{game['number']}*\n\n🔢 /number", parse_mode="Markdown")

async def start_number(chat_id, user, ctx, reply_func):
    p = get_player(user.id, user.first_name); p["games_played"].add("number")
    extra_time = 30 if p.get("time_bonus") else 0
    if p.get("time_bonus"): p["time_bonus"] = False
    if chat_id in number_games and number_games[chat_id].get("timer_task"): number_games[chat_id]["timer_task"].cancel()
    number = random.randint(1, 100)
    total_time = NUMBER_TIME + extra_time
    number_games[chat_id] = {"number": number, "active": True, "attempts": {}, "timer_task": None}
    await reply_func(f"🔢 *Угадай число!*\nОт *1 до 100*\n+100 очков | ⏱ {total_time} сек!", parse_mode="Markdown")
    task = asyncio.create_task(number_timer(chat_id, ctx))
    number_games[chat_id]["timer_task"] = task

async def cmd_number(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await start_number(update.effective_chat.id, update.effective_user, ctx, update.message.reply_text)


async def start_blackjack(chat_id, user, ctx, reply_func):
    p = get_player(user.id, user.first_name); p["games_played"].add("blackjack")
    if p["total_score"] < 50: await reply_func("🃏 Нужно 50 очков!", parse_mode="Markdown"); return
    hand = [deal_card(), deal_card()]; dealer = [deal_card(), deal_card()]
    blackjack_games[chat_id] = {"player_id": user.id, "player_name": user.first_name,
        "hand": hand, "dealer": dealer, "bet": 50, "active": True}
    val = card_value(hand)
    msg = await reply_func(f"🃏 *Блэкджек!*\n\nТвои карты: {hand_str(hand)}\nДилер: {dealer[0]} + ?\n\n"
        f"Ставка: 50 очков\n{'🎉 БЛЭКДЖЕК!' if val == 21 else 'Ещё карту или хватит?'}",
        parse_mode="Markdown", reply_markup=None if val == 21 else make_blackjack_keyboard())
    if val == 21:
        p["total_score"] = max(0, p["total_score"] - 50)
        add_score(user.id, user.first_name, 125); p["wins"] += 1
        p["achievements"].add("blackjack21"); blackjack_games[chat_id]["active"] = False
        await ctx.bot.send_message(chat_id=chat_id,
            text=f"🎉 *БЛЭКДЖЕК!* {user.first_name} +125 оч!\n🃏 /blackjack", parse_mode="Markdown")

async def cmd_blackjack(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await start_blackjack(update.effective_chat.id, update.effective_user, ctx, update.message.reply_text)


async def start_slots(chat_id, user, ctx, reply_func):
    p = get_player(user.id, user.first_name); p["games_played"].add("slots")
    if p["total_score"] < 100: await reply_func("🎰 Нужно 100 очков!", parse_mode="Markdown"); return
    p["total_score"] -= 100
    symbols = spin_slots(); prize = check_slots(symbols)
    result = " | ".join(symbols)
    if prize > 0:
        add_score(user.id, user.first_name, prize)
        p["achievements"].add("lucky_slots")
        msg = f"🎰 *{result}*\n\n🎉 ВЫИГРЫШ *+{prize}* очков!\nВсего: {p['total_score']}"
    else:
        msg = f"🎰 *{result}*\n\nНе повезло! -100 оч\nВсего: {p['total_score']}\n🎰 /slots — ещё раз"
    await reply_func(msg, parse_mode="Markdown")

async def cmd_slots(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await start_slots(update.effective_chat.id, update.effective_user, ctx, update.message.reply_text)


async def start_tod(chat_id, user, ctx, reply_func):
    get_player(user.id, user.first_name)["games_played"].add("tod")
    choice = random.choice(["truth", "dare"])
    if choice == "truth":
        q = random.choice(TOD_TRUTHS)
        await reply_func(f"❓ *Правда или Действие*\n\n*{user.first_name}* выбирает...\n\n🗣 *ПРАВДА:*\n{q}", parse_mode="Markdown")
    else:
        a = random.choice(TOD_DARES)
        await reply_func(f"❓ *Правда или Действие*\n\n*{user.first_name}* выбирает...\n\n🎯 *ДЕЙСТВИЕ:*\n{a}", parse_mode="Markdown")

async def cmd_tod(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await start_tod(update.effective_chat.id, update.effective_user, ctx, update.message.reply_text)


async def cmd_duel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id; user = update.effective_user
    p = get_player(user.id, user.first_name); p["games_played"].add("duel")
    if p["total_score"] < 100: await update.message.reply_text("⚔️ Нужно 100 очков!", parse_mode="Markdown"); return
    if update.message.reply_to_message:
        opp = update.message.reply_to_message.from_user
        if opp.id == user.id: await update.message.reply_text("Нельзя драться с собой 😄", parse_mode="Markdown"); return
        duel_games[chat_id] = {"challenger_id": user.id, "challenger_name": user.first_name,
            "opponent_id": opp.id, "opponent_name": opp.first_name, "active": True}
        await update.message.reply_text(
            f"⚔️ *{user.first_name}* вызывает *{opp.first_name}* на дуэль!\nСтавка: 100 очков\n\n*{opp.first_name}*, принимаешь?",
            parse_mode="Markdown", reply_markup=make_duel_keyboard(user.id))
    else:
        await update.message.reply_text("⚔️ Ответь на сообщение игрока командой /duel", parse_mode="Markdown")


# ══════════════════════════════════════════════════════════════════════════════
# CALLBACK
# ══════════════════════════════════════════════════════════════════════════════
async def callback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id
    user = update.effective_user
    data = query.data
    p = get_player(user.id, user.first_name)
    g = is_group(update.effective_chat)

    async def reply(text, **kwargs):
        await ctx.bot.send_message(chat_id=chat_id, text=text, **kwargs)

    if data == "menu_game": await start_croc(chat_id, user, ctx, reply)
    elif data == "menu_wheel": await start_wheel(chat_id, user, ctx, reply)
    elif data == "menu_speedrun": await start_speedrun(chat_id, user, ctx, reply)
    elif data == "menu_trivia": await start_trivia(chat_id, user, ctx, reply)
    elif data == "menu_hangman": await start_hangman(chat_id, user, ctx, reply)
    elif data == "menu_number": await start_number(chat_id, user, ctx, reply)
    elif data == "menu_blackjack": await start_blackjack(chat_id, user, ctx, reply)
    elif data == "menu_slots": await start_slots(chat_id, user, ctx, reply)
    elif data == "menu_tod": await start_tod(chat_id, user, ctx, reply)
    elif data == "menu_duel": await reply("⚔️ Ответь на сообщение игрока командой /duel", parse_mode="Markdown")
    elif data == "menu_scores": await reply(f"📊 *Таблица очков*\n\n{global_scores_text()}", parse_mode="Markdown")
    elif data == "menu_shop": await reply(f"🛒 *Магазин*\n\nТвои очки: *{p['total_score']}*", parse_mode="Markdown", reply_markup=make_shop_keyboard(p))
    elif data == "menu_achievements":
        lines = [f"{'✅' if k in p['achievements'] else '🔒'} {v[0]} {v[1]}" for k, v in ACHIEVEMENTS.items()]
        await reply("🏆 *Достижения*\n\n" + "\n".join(lines), parse_mode="Markdown")
    elif data == "menu_profile":
        title = get_title(p["total_score"])
        await reply(f"👤 *{user.first_name}*\n\n🏅 {title}\n💰 {p['total_score']} оч | 🏆 {p['wins']} побед\n🎮 Игр: {len(p['games_played'])}", parse_mode="Markdown")
    elif data == "menu_inventory":
        inv = p.get("inventory", {})
        if not inv or all(v == 0 for v in inv.values()):
            await reply("🎒 Инвентарь пуст! Купи предметы в /shop", parse_mode="Markdown")
        else:
            lines = [f"{SHOP_ITEMS[k][0]} *{SHOP_ITEMS[k][1]}* x{v}" for k, v in inv.items() if v > 0 and k in SHOP_ITEMS]
            await reply("🎒 *Инвентарь*\n\n" + "\n".join(lines), parse_mode="Markdown")
    elif data == "menu_daily":
        today = date.today().isoformat()
        if p.get("last_daily") == today:
            await query.answer("Уже получил сегодня!", show_alert=True); return
        bonus = random.randint(50, 300)
        if p.get("double_daily"): bonus *= 2; p["double_daily"] = False
        p["last_daily"] = today
        add_score(user.id, user.first_name, bonus)
        await reply(f"🎁 *{user.first_name}* получает *+{bonus}* очков!\n💰 Всего: {p['total_score']}", parse_mode="Markdown")
    elif data == "menu_join":
        if chat_id not in group_players: group_players[chat_id] = {}
        if user.id in group_players[chat_id]:
            await query.answer("Ты уже в игре!", show_alert=True); return
        group_players[chat_id][user.id] = user.first_name
        names = ", ".join(group_players[chat_id].values())
        await reply(f"✋ *{user.first_name}* присоединился(ась)!\n👥 {names}", parse_mode="Markdown")
    elif data == "menu_back":
        await query.edit_message_reply_markup(reply_markup=make_main_keyboard(group=g))

    elif data == "croc_skip":
        game = games.get(chat_id)
        if not game or not game.get("active"): return
        if user.id != game["explainer_id"]: await query.answer("Только объясняющий!", show_alert=True); return
        if game["timer_task"]: game["timer_task"].cancel()
        old = game["word"]
        category = random.choice(list(WORDS.keys())); word = random.choice(WORDS[category])
        game["word"] = word.lower(); game["category"] = category
        try: await ctx.bot.send_message(chat_id=user.id, text=f"⏭ Новое: *{word.upper()}*", parse_mode="Markdown")
        except: pass
        await query.edit_message_text(f"⏭ Пропущено (было: *{old}*).\nКатегория: {category}\n⏱ {ROUND_TIME_CROC} сек!",
            parse_mode="Markdown", reply_markup=make_croc_keyboard())
        task = asyncio.create_task(croc_timer(chat_id, ctx)); game["timer_task"] = task

    elif data == "croc_stop":
        game = games.get(chat_id)
        if not game or not game.get("active"): return
        if user.id != game["explainer_id"]: await query.answer("Только объясняющий!", show_alert=True); return
        if game["timer_task"]: game["timer_task"].cancel()
        game["active"] = False
        await query.edit_message_text(f"🛑 Стоп.\nСлово: *{game['word'].upper()}*\n\n▶️ /game", parse_mode="Markdown")

    elif data == "wheel_spin":
        game = wheel_games.get(chat_id)
        if not game or not game.get("active"): return
        result = spin_drum()
        if result == "БАНКРОТ":
            if p["protection"]:
                p["protection"] = False; game["drum_value"] = 100
                await reply(f"🛡 *{user.first_name}* защитился! Барабан: 100\nНазови букву:", parse_mode="Markdown")
            else:
                game["round_scores"][user.id] = 0; game["drum_value"] = None
                await reply(f"💸 *БАНКРОТ!* {user.first_name} теряет очки!\n\nСлово: `{display_word(game['word'], game['guessed'])}`",
                    parse_mode="Markdown", reply_markup=make_wheel_keyboard())
        elif result == "ПРИЗ":
            bonus = random.choice([300, 500, 700])
            game["round_scores"][user.id] = game["round_scores"].get(user.id, 0) + bonus; game["drum_value"] = None
            await reply(f"🎁 *ПРИЗ!* {user.first_name} +{bonus}!\n\nСлово: `{display_word(game['word'], game['guessed'])}`",
                parse_mode="Markdown", reply_markup=make_wheel_keyboard())
        else:
            game["drum_value"] = result
            await reply(f"🎡 *{user.first_name}* крутит: *{result}* очков!\nНазови букву:", parse_mode="Markdown")

    elif data == "wheel_stop":
        game = wheel_games.get(chat_id)
        if not game or not game.get("active"): return
        if game["timer_task"]: game["timer_task"].cancel()
        game["active"] = False
        await query.edit_message_text(f"🛑 Стоп.\nСлово: *{game['word'].upper()}*\n\n🎡 /wheel", parse_mode="Markdown")

    elif data == "bj_hit":
        game = blackjack_games.get(chat_id)
        if not game or not game.get("active"): return
        if user.id != game["player_id"]: await query.answer("Не твоя игра!", show_alert=True); return
        game["hand"].append(deal_card()); val = card_value(game["hand"])
        if val > 21:
            game["active"] = False; p["total_score"] = max(0, p["total_score"] - 50)
            await query.edit_message_text(f"🃏 {hand_str(game['hand'])}\n\n💥 *Перебор!* -50 оч\nВсего: {p['total_score']}\n\n🃏 /blackjack", parse_mode="Markdown")
        else:
            await query.edit_message_text(f"🃏 {hand_str(game['hand'])}\nДилер: {game['dealer'][0]} + ?\n\nЕщё или хватит?",
                parse_mode="Markdown", reply_markup=make_blackjack_keyboard())

    elif data == "bj_stand":
        game = blackjack_games.get(chat_id)
        if not game or not game.get("active"): return
        if user.id != game["player_id"]: await query.answer("Не твоя игра!", show_alert=True); return
        game["active"] = False; dealer = game["dealer"]
        while card_value(dealer) < 17: dealer.append(deal_card())
        pval = card_value(game["hand"]); dval = card_value(dealer)
        p["total_score"] = max(0, p["total_score"] - 50)
        if dval > 21 or pval > dval:
            add_score(user.id, user.first_name, 100); p["wins"] += 1; result = f"🎉 *Победа!* +100 оч"
        elif pval == dval:
            add_score(user.id, user.first_name, 50); result = "🤝 *Ничья!* Ставка возвращена"
        else:
            result = f"😔 *Дилер победил!* -50 оч"
        await query.edit_message_text(f"🃏 Ты: {hand_str(game['hand'])}\nДилер: {hand_str(dealer)}\n\n{result}\nВсего: {p['total_score']}\n\n🃏 /blackjack", parse_mode="Markdown")

    elif data.startswith("duel_accept_"):
        challenger_id = int(data.split("_")[2]); game = duel_games.get(chat_id)
        if not game or not game.get("active"): return
        if user.id != game["opponent_id"]: await query.answer("Это не твоя дуэль!", show_alert=True); return
        game["active"] = False
        cp = get_player(challenger_id, game["challenger_name"]); op = p
        if cp["total_score"] < 100 or op["total_score"] < 100:
            await query.edit_message_text("❌ Не хватает очков!", parse_mode="Markdown"); return
        winner_name = random.choice([game["challenger_name"], game["opponent_name"]])
        loser_name = game["opponent_name"] if winner_name == game["challenger_name"] else game["challenger_name"]
        winner_id = challenger_id if winner_name == game["challenger_name"] else user.id
        loser_id = user.id if winner_name == game["challenger_name"] else challenger_id
        add_score(winner_id, winner_name, 100)
        get_player(loser_id, loser_name)["total_score"] = max(0, get_player(loser_id, loser_name)["total_score"] - 100)
        get_player(winner_id, winner_name)["wins"] += 1
        await query.edit_message_text(
            f"⚔️ *ДУЭЛЬ!*\n\n🎯 {game['challenger_name']} vs {game['opponent_name']}\n\n"
            f"🏆 *{winner_name}* победил! +100 оч\n😔 *{loser_name}* -100 оч\n\n📊 {global_scores_text()}", parse_mode="Markdown")

    elif data == "duel_decline":
        if chat_id in duel_games: duel_games[chat_id]["active"] = False
        await query.edit_message_text("❌ Дуэль отклонена.", parse_mode="Markdown")

    elif data.startswith("shop_"):
        key = data[5:]
        if key not in SHOP_ITEMS: return
        icon, name, desc, price = SHOP_ITEMS[key]
        if p["total_score"] < price:
            await query.answer(f"Недостаточно очков! Нужно {price}", show_alert=True); return

        if key == "vip":
            if p["vip"]: await query.answer("У тебя уже VIP!", show_alert=True); return
            p["total_score"] -= price; p["vip"] = True; p["achievements"].add("vip_buyer")
            await reply(f"👑 *{user.first_name}* получает VIP статус!", parse_mode="Markdown")
        elif key == "speedrun":
            if p["speedrun_access"]: await query.answer("Уже есть доступ!", show_alert=True); return
            p["total_score"] -= price; p["speedrun_access"] = True; p["achievements"].add("speedrunner")
            await reply(f"⚡ *{user.first_name}* купил(а) Спидран!\n/speedrun — вперёд!", parse_mode="Markdown")
        elif key == "hint":
            game = wheel_games.get(chat_id)
            if not game or not game.get("active"):
                await query.answer("Нет активного Поля чудес!", show_alert=True); return
            hidden = [c for c in game["word"] if c not in game["guessed"] and c != " "]
            if not hidden: await query.answer("Все буквы открыты!", show_alert=True); return
            letter = random.choice(hidden); game["guessed"].add(letter); p["total_score"] -= price
            await reply(f"💡 *{user.first_name}* открывает *{letter.upper()}* (-{price})\n\nСлово: `{display_word(game['word'], game['guessed'])}`",
                parse_mode="Markdown", reply_markup=make_wheel_keyboard())
        elif key == "protection":
            p["total_score"] -= price; p["protection"] = True
            await query.answer("🛡 Защита активирована!", show_alert=True)
        elif key == "double":
            p["total_score"] -= price; p["double"] = True
            await query.answer("🎯 Удвоение активировано!", show_alert=True)
        elif key == "sabotage":
            game = wheel_games.get(chat_id)
            if not game or not game.get("active"):
                await query.answer("Нет активного Поля чудес!", show_alert=True); return
            p["total_score"] -= price
            other = [uid for uid in game["round_scores"] if uid != user.id]
            if other:
                target = random.choice(other); game["sabotage_target"] = target
                tname = players.get(target, {}).get("name", "игрок")
                await reply(f"💣 *{user.first_name}* — диверсия против *{tname}*!", parse_mode="Markdown")
            else: await query.answer("Нет других игроков!", show_alert=True)
        elif key == "extra_life":
            p["total_score"] -= price; p["extra_life"] = True
            await query.answer("❤️ Доп. жизнь в виселице активирована!", show_alert=True)
        elif key == "time_bonus":
            p["total_score"] -= price; p["time_bonus"] = True
            await query.answer("⏱ +30 сек к следующей игре!", show_alert=True)
        elif key == "double_daily":
            p["total_score"] -= price; p["double_daily"] = True
            await query.answer("🎁 Следующий бонус x2!", show_alert=True)
        elif key == "lottery":
            p["total_score"] -= price
            prize = random.randint(50, 500)
            add_score(user.id, user.first_name, prize)
            await reply(f"🎟 *{user.first_name}* покупает лотерейный билет!\n\n🎉 Выигрыш: *+{prize}* очков!\nВсего: {p['total_score']}", parse_mode="Markdown")


# ══════════════════════════════════════════════════════════════════════════════
# MESSAGE ROUTER
# ══════════════════════════════════════════════════════════════════════════════
async def message_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    p = get_player(user.id, user.first_name)
    text = (update.message.text or "").strip().lower()
    g = is_group(update.effective_chat)

    if chat_id in speed_games and speed_games[chat_id].get("active"):
        game = speed_games[chat_id]
        if user.id != game["player_id"]: return
        if text == game["word"]:
            game["count"] += 1; new_word = random.choice(SPEEDRUN_WORDS); game["word"] = new_word
            await update.message.reply_text(f"✅ Верно! Угадано: {game['count']}\n\nСледующее: `{'_ ' * len(new_word)}`\nБукв: {len(new_word)}", parse_mode="Markdown")
        return

    if chat_id in number_games and number_games[chat_id].get("active"):
        game = number_games[chat_id]
        if text.isdigit():
            guess = int(text); number = game["number"]
            game["attempts"][user.id] = game["attempts"].get(user.id, 0) + 1
            attempts = game["attempts"][user.id]
            if guess == number:
                if game["timer_task"]: game["timer_task"].cancel()
                game["active"] = False; add_score(user.id, user.first_name, 100); p["wins"] += 1
                new_achs = check_achievements(user.id, user.first_name)
                await update.message.reply_text(
                    f"🎉 *{user.first_name}* угадал(а) *{number}*! За {attempts} попыток! +100\n\n"
                    f"📊 {global_scores_text()}\n\n🔢 /number", parse_mode="Markdown", reply_markup=make_main_keyboard(group=g))
            elif guess < number: await update.message.reply_text(f"📈 Больше! (попытка {attempts})", parse_mode="Markdown")
            else: await update.message.reply_text(f"📉 Меньше! (попытка {attempts})", parse_mode="Markdown")
        return

    if chat_id in trivia_games and trivia_games[chat_id].get("active"):
        game = trivia_games[chat_id]
        if text == game["answer"]:
            if game["timer_task"]: game["timer_task"].cancel()
            game["active"] = False; add_score(user.id, user.first_name, 150); p["wins"] += 1
            await update.message.reply_text(
                f"🎉 *{user.first_name}* ответил(а) правильно! +150\n\n📊 {global_scores_text()}\n\n🧠 /trivia",
                parse_mode="Markdown", reply_markup=make_main_keyboard(group=g))
        return

    if chat_id in hangman_games and hangman_games[chat_id].get("active"):
        game = hangman_games[chat_id]; word = game["word"]; guessed = game["guessed"]
        max_errors = game.get("max_errors", 6)
        if len(text) > 1:
            if text == word:
                if game["timer_task"]: game["timer_task"].cancel()
                game["active"] = False; add_score(user.id, user.first_name, 200); p["wins"] += 1
                await update.message.reply_text(
                    f"🎉 *{user.first_name}* угадал(а) *{word.upper()}*! +200\n\n📊 {global_scores_text()}\n\n📝 /hangman",
                    parse_mode="Markdown", reply_markup=make_main_keyboard(group=g))
            else: await update.message.reply_text(f"❌ Неверно! *{text.upper()}* — не то.", parse_mode="Markdown")
            return
        if len(text) == 1 and text.isalpha():
            if text in guessed: await update.message.reply_text(f"Буква *{text.upper()}* уже была!", parse_mode="Markdown"); return
            guessed.add(text); errors = sum(1 for c in guessed if c not in word)
            game["errors"] = errors; pic = HANGMAN_PICS[min(errors, 5)]; shown = display_word(word, guessed)
            wrong = [c.upper() for c in guessed if c not in word]
            if text in word:
                add_score(user.id, user.first_name, 50)
                if set(c for c in word if c != " ") <= guessed:
                    if game["timer_task"]: game["timer_task"].cancel()
                    game["active"] = False; add_score(user.id, user.first_name, 200); p["wins"] += 1
                    await update.message.reply_text(
                        f"🎉 *{user.first_name}* открыл(а) все буквы! +250\nСлово: *{word.upper()}*\n\n📊 {global_scores_text()}\n\n📝 /hangman",
                        parse_mode="Markdown", reply_markup=make_main_keyboard(group=g))
                else:
                    await update.message.reply_text(
                        f"✅ Буква *{text.upper()}* есть! +50\n\n{pic} Ошибок: {errors}/{max_errors}\nСлово: `{shown}`\nНеверные: {' '.join(wrong) if wrong else '—'}",
                        parse_mode="Markdown")
            else:
                if errors >= max_errors:
                    if game["timer_task"]: game["timer_task"].cancel()
                    game["active"] = False
                    await update.message.reply_text(f"💀 *{user.first_name}* проиграл(а)!\nСлово: *{word.upper()}*\n\n📝 /hangman",
                        parse_mode="Markdown", reply_markup=make_main_keyboard(group=g))
                else:
                    await update.message.reply_text(
                        f"❌ Буквы *{text.upper()}* нет!\n\n{pic} Ошибок: {errors}/{max_errors}\nСлово: `{shown}`\nНеверные: {' '.join(wrong)}",
                        parse_mode="Markdown")
        return

    if chat_id in wheel_games and wheel_games[chat_id].get("active"):
        game = wheel_games[chat_id]; word = game["word"]; guessed = game["guessed"]
        if game.get("sabotage_target") == user.id:
            game["sabotage_target"] = None
            await update.message.reply_text(f"💣 *{user.first_name}* пропускает ход (диверсия)!", parse_mode="Markdown"); return
        if len(text) > 1:
            if text == word:
                if game["timer_task"]: game["timer_task"].cancel()
                game["active"] = False; bonus = 500
                game["round_scores"][user.id] = game["round_scores"].get(user.id, 0) + bonus
                rs = max(0, game["round_scores"].get(user.id, 0))
                add_score(user.id, user.first_name, rs); p["wins"] += 1
                await update.message.reply_text(
                    f"🎉 *{user.first_name}* угадал(а) *{word.upper()}*!\n+{bonus} бонус! За раунд: +{rs}\n\n📊 {global_scores_text()}\n\n🎡 /wheel",
                    parse_mode="Markdown", reply_markup=make_main_keyboard(group=g))
            else:
                game["round_scores"][user.id] = game["round_scores"].get(user.id, 0) - 150; p["streak"] = 0
                await update.message.reply_text(f"❌ *{user.first_name}*, неверно! -150\nСлово: `{display_word(word, guessed)}`", parse_mode="Markdown")
            return
        if len(text) == 1 and text.isalpha():
            if text in guessed or text in game.get("wrong_letters", set()):
                await update.message.reply_text(f"Буква *{text.upper()}* уже была!", parse_mode="Markdown"); return
            if game.get("drum_value") is None:
                await update.message.reply_text("Сначала крутите барабан! 🎡", parse_mode="Markdown"); return
            drum_val = game["drum_value"]; game["drum_value"] = None
            if text in word:
                count = word.count(text); guessed.add(text)
                points = drum_val * count if isinstance(drum_val, int) else 0
                if p["double"]: points *= 2; p["double"] = False; dm = " 🎯x2!"
                else: dm = ""
                game["round_scores"][user.id] = game["round_scores"].get(user.id, 0) + points
                p["streak"] = p.get("streak", 0) + 1; sm = ""
                if p["streak"] >= 3:
                    game["round_scores"][user.id] += 100; sm = f"\n🔥 Серия {p['streak']}! +100"; p["streak"] = 0
                    p["achievements"].add("streak3")
                shown = display_word(word, guessed)
                if set(c for c in word if c != " ") <= guessed:
                    if game["timer_task"]: game["timer_task"].cancel()
                    game["active"] = False; rs = max(0, game["round_scores"].get(user.id, 0))
                    add_score(user.id, user.first_name, rs); p["wins"] += 1
                    await update.message.reply_text(
                        f"✅ *{user.first_name}* +{points}{dm}{sm}\n\n🎉 Слово: *{word.upper()}*! За раунд: +{rs}\n\n📊 {global_scores_text()}\n\n🎡 /wheel",
                        parse_mode="Markdown", reply_markup=make_main_keyboard(group=g))
                else:
                    await update.message.reply_text(
                        f"✅ *{user.first_name}* открыл(а) *{text.upper()}* ({count}шт) +{points}{dm}{sm}\n\nСлово: `{shown}`",
                        parse_mode="Markdown", reply_markup=make_wheel_keyboard())
            else:
                game.setdefault("wrong_letters", set()).add(text); p["streak"] = 0
                game["round_scores"][user.id] = game["round_scores"].get(user.id, 0) - 100
                await update.message.reply_text(
                    f"❌ *{user.first_name}*, *{text.upper()}* нет! -100\nСлово: `{display_word(word, guessed)}`",
                    parse_mode="Markdown", reply_markup=make_wheel_keyboard())
        return

    game = games.get(chat_id)
    if not game or not game.get("active"): return
    if user.id == game["explainer_id"]: return
    if text == game["word"]:
        if game["timer_task"]: game["timer_task"].cancel()
        game["active"] = False
        add_score(user.id, user.first_name, 1); add_score(game["explainer_id"], game["explainer_name"], 1)
        p["wins"] += 1; new_achs = check_achievements(user.id, user.first_name)
        ach_text = ""
        if new_achs: ach_text = "\n\n🏆 " + " ".join([f"{ACHIEVEMENTS[a][0]}" for a in new_achs if a in ACHIEVEMENTS])
        await update.message.reply_text(
            f"🎉 *{user.first_name}* угадал(а) *{game['word'].upper()}*!\n\n"
            f"🏅 +1: {user.first_name}\n🏅 +1: {game['explainer_name']}{ach_text}\n\n"
            f"📊 {global_scores_text()}\n\n▶️ /game",
            parse_mode="Markdown", reply_markup=make_main_keyboard(group=g))


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(ChatMemberHandler(greet_new_group, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("scores", cmd_scores))
    app.add_handler(CommandHandler("profile", cmd_profile))
    app.add_handler(CommandHandler("achievements", cmd_achievements))
    app.add_handler(CommandHandler("inventory", cmd_inventory))
    app.add_handler(CommandHandler("daily", cmd_daily))
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
    app.add_handler(CommandHandler("shop", cmd_shop))
    app.add_handler(CommandHandler("join", cmd_join))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    async def post_init(application):
        await setup_commands(application)
    app.post_init = post_init

    print("🎮 Бот запущен!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
