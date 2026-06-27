import os
import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ChatMemberHandler
)

BOT_TOKEN = os.getenv("BOT_TOKEN", "ВСТАВЬТЕ_ТОКЕН_СЮДА")
BOT_USERNAME = os.getenv("BOT_USERNAME", "your_bot")

# ─── СЛОВА ────────────────────────────────────────────────────────────────────
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
}

SPEEDRUN_WORDS = [
    "кот", "дом", "лес", "море", "гора", "река", "небо", "снег", "огонь", "вода",
    "хлеб", "соль", "свет", "тень", "мост", "дорога", "птица", "рыба", "конь", "волк",
    "медведь", "лиса", "заяц", "орёл", "змея", "черепаха", "бабочка", "цветок", "дерево", "камень",
    "корабль", "самолёт", "машина", "велосипед", "поезд", "ракета", "замок", "башня", "стена", "окно",
]

TRIVIA = [
    {"q": "Столица Франции?", "a": "париж"},
    {"q": "Сколько планет в Солнечной системе?", "a": "8"},
    {"q": "Какой самый большой океан?", "a": "тихий"},
    {"q": "Кто написал 'Войну и мир'?", "a": "толстой"},
    {"q": "Химический символ золота?", "a": "au"},
    {"q": "Самая длинная река в мире?", "a": "нил"},
    {"q": "Сколько цветов в радуге?", "a": "7"},
    {"q": "Столица Японии?", "a": "токио"},
    {"q": "Кто написал 'Гарри Поттера'?", "a": "роулинг"},
    {"q": "Какой газ мы вдыхаем?", "a": "кислород"},
    {"q": "Сколько букв в русском алфавите?", "a": "33"},
    {"q": "Самая высокая гора в мире?", "a": "эверест"},
    {"q": "Столица России?", "a": "москва"},
    {"q": "Кто написал 'Мастер и Маргарита'?", "a": "булгаков"},
    {"q": "Какой металл самый лёгкий?", "a": "литий"},
    {"q": "Сколько сторон у шестиугольника?", "a": "6"},
    {"q": "Столица Германии?", "a": "берлин"},
    {"q": "Кто изобрёл телефон?", "a": "белл"},
    {"q": "Какая планета ближайшая к Солнцу?", "a": "меркурий"},
    {"q": "Сколько нот в октаве?", "a": "7"},
]

DRUM = [100, 100, 200, 200, 300, 300, 500, 500, 1000, "БАНКРОТ", "БАНКРОТ", "ПРИЗ"]

ROUND_TIME_CROC = 60
ROUND_TIME_WHEEL = 300
SPEEDRUN_TIME = 30
TRIVIA_TIME = 20
HANGMAN_TIME = 120
NUMBER_TIME = 30

# ─── ХРАНИЛИЩЕ ────────────────────────────────────────────────────────────────
games = {}
wheel_games = {}
speed_games = {}
trivia_games = {}
hangman_games = {}
number_games = {}
players = {}
group_players = {}


def get_player(user_id, name):
    if user_id not in players:
        players[user_id] = {
            "name": name, "total_score": 0,
            "speedrun_access": False, "vip": False,
            "streak": 0, "protection": False,
            "double": False, "sabotage_target": None,
        }
    players[user_id]["name"] = name
    return players[user_id]


def add_score(user_id, name, amount):
    p = get_player(user_id, name)
    p["total_score"] = max(0, p["total_score"] + amount)


def global_scores_text():
    if not players:
        return "Пока никто не набрал очков."
    sorted_p = sorted(players.values(), key=lambda x: x["total_score"], reverse=True)
    medals = ["🥇", "🥈", "🥉"]
    lines = []
    for i, p in enumerate(sorted_p[:10]):
        medal = medals[i] if i < 3 else f"{i+1}."
        vip = " 👑" if p["vip"] else ""
        lines.append(f"{medal} {p['name']}{vip} — {p['total_score']} оч.")
    return "\n".join(lines)


def display_word(word, guessed):
    return " ".join(c if c in guessed or c == " " else "\\_" for c in word)


def display_hangman(word, guessed):
    shown = " ".join(c.upper() if c in guessed or c == " " else "\_" for c in word)
    wrong = [c.upper() for c in guessed if c not in word]
    return shown, wrong


def spin_drum():
    return random.choice(DRUM)


# ─── КЛАВИАТУРЫ ───────────────────────────────────────────────────────────────
def make_main_keyboard(is_group=False):
    rows = [
        [InlineKeyboardButton("🐊 Крокодил", callback_data="menu_game"),
         InlineKeyboardButton("🎡 Поле чудес", callback_data="menu_wheel")],
        [InlineKeyboardButton("⚡ Спидран", callback_data="menu_speedrun"),
         InlineKeyboardButton("🛒 Магазин", callback_data="menu_shop")],
        [InlineKeyboardButton("🧠 Викторина", callback_data="menu_trivia"),
         InlineKeyboardButton("📝 Виселица", callback_data="menu_hangman")],
        [InlineKeyboardButton("🔢 Угадай число", callback_data="menu_number"),
         InlineKeyboardButton("📊 Счёт", callback_data="menu_scores")],
    ]
    if is_group:
        rows.append([InlineKeyboardButton("✋ Присоединиться", callback_data="menu_join")])
    else:
        rows.insert(0, [InlineKeyboardButton("➕ Добавить в группу",
            url=f"https://t.me/{BOT_USERNAME}?startgroup=true")])
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


def make_shop_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💡 Подсказка — 200 оч.", callback_data="shop_hint")],
        [InlineKeyboardButton("🛡 Защита от банкрота — 400 оч.", callback_data="shop_protection")],
        [InlineKeyboardButton("🎯 Удвоение — 500 оч.", callback_data="shop_double")],
        [InlineKeyboardButton("💣 Диверсия — 350 оч.", callback_data="shop_sabotage")],
        [InlineKeyboardButton("👑 VIP статус — 1000 оч.", callback_data="shop_vip")],
        [InlineKeyboardButton("⚡ Спидран доступ — 750 оч.", callback_data="shop_speedrun")],
        [InlineKeyboardButton("🔙 Назад", callback_data="menu_back")],
    ])


# ─── /start ───────────────────────────────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    get_player(user.id, user.first_name)
    is_group = chat.type in ("group", "supergroup")
    await update.message.reply_text(
        f"👋 Привет, *{user.first_name}*!\n\n"
        f"🎮 *Игровой бот* — 7 игр в одном!\n\n"
        f"🐊 Крокодил | 🎡 Поле чудес | ⚡ Спидран\n"
        f"🧠 Викторина | 📝 Виселица | 🔢 Угадай число\n\n"
        f"{'Выбери игру 👇' if is_group else 'Добавь в группу и играй с друзьями! 👇'}",
        parse_mode="Markdown",
        reply_markup=make_main_keyboard(is_group)
    )


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
                 f"🎮 Я игровой бот — 7 игр для всей группы!\n\n"
                 f"🐊 Крокодил — объясняй слова\n"
                 f"🎡 Поле чудес — крути барабан\n"
                 f"⚡ Спидран — кто быстрее\n"
                 f"🧠 Викторина — вопросы и ответы\n"
                 f"📝 Виселица — угадай слово по буквам\n"
                 f"🔢 Угадай число — от 1 до 100\n\n"
                 f"✋ Сначала нажмите *Присоединиться*!",
            parse_mode="Markdown",
            reply_markup=make_main_keyboard(is_group=True)
        )


async def cmd_join(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    get_player(user.id, user.first_name)
    if chat_id not in group_players:
        group_players[chat_id] = {}
    if user.id in group_players[chat_id]:
        await update.message.reply_text(f"✅ *{user.first_name}*, ты уже в игре!", parse_mode="Markdown")
        return
    group_players[chat_id][user.id] = user.first_name
    names = ", ".join(group_players[chat_id].values())
    await update.message.reply_text(
        f"✋ *{user.first_name}* присоединился(ась)!\n\n"
        f"Игроков: {len(group_players[chat_id])}\n👥 {names}",
        parse_mode="Markdown", reply_markup=make_main_keyboard(is_group=True)
    )


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    is_group = update.effective_chat.type in ("group", "supergroup")
    await update.message.reply_text(
        "📖 *Правила*\n\n"
        "🐊 *Крокодил* — один объясняет, все угадывают. +1 каждому.\n\n"
        "🎡 *Поле чудес* — крути барабан, называй букву.\n"
        "Барабан: 100/200/300/500/1000/БАНКРОТ/ПРИЗ\n"
        "❌ Неверная буква: -100 | ❌ Неверное слово: -150\n"
        "✅ Угадать слово: +500 | 🔥 Серия 3 буквы: +100\n\n"
        "⚡ *Спидран* — 30 сек, угадай больше слов. 750 оч.\n\n"
        "🧠 *Викторина* — вопрос на 20 сек. +150 за ответ.\n\n"
        "📝 *Виселица* — угадывай буквы. 6 ошибок = конец.\n"
        "+50 за букву, +200 за слово.\n\n"
        "🔢 *Угадай число* — от 1 до 100. +100 за угадывание.",
        parse_mode="Markdown",
        reply_markup=make_main_keyboard(is_group)
    )


async def cmd_scores(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"📊 *Таблица очков*\n\n{global_scores_text()}",
        parse_mode="Markdown"
    )


async def cmd_shop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    p = get_player(user.id, user.first_name)
    await update.message.reply_text(
        f"🛒 *Магазин*\n\nТвои очки: *{p['total_score']}*",
        parse_mode="Markdown", reply_markup=make_shop_keyboard()
    )


# ══════════════════════════════════════════════════════════════════════════════
# 🐊 КРОКОДИЛ
# ══════════════════════════════════════════════════════════════════════════════
async def croc_timer(chat_id, ctx):
    await asyncio.sleep(ROUND_TIME_CROC)
    game = games.get(chat_id)
    if game and game.get("active"):
        game["active"] = False
        await ctx.bot.send_message(chat_id=chat_id,
            text=f"⏰ Время вышло!\nСлово: *{game['word'].upper()}*\n\n▶️ /game",
            parse_mode="Markdown")


async def start_croc(chat_id, user, ctx, reply_func):
    get_player(user.id, user.first_name)
    if chat_id in games and games[chat_id].get("timer_task"):
        games[chat_id]["timer_task"].cancel()
    category = random.choice(list(WORDS.keys()))
    word = random.choice(WORDS[category])
    games[chat_id] = {
        "word": word.lower(), "category": category,
        "explainer_id": user.id, "explainer_name": user.first_name,
        "active": True, "timer_task": None,
    }
    try:
        await ctx.bot.send_message(chat_id=user.id,
            text=f"🐊 Твоё слово: *{word.upper()}*\nКатегория: {category}",
            parse_mode="Markdown")
        dm = f"✉️ Слово отправлено {user.first_name} в личку."
    except Exception:
        dm = "⚠️ Напиши боту /start в личку!"
    await reply_func(
        f"🐊 *Новый раунд!*\nОбъясняет: *{user.first_name}*\n"
        f"Категория: {category}\n\n{dm}\n\n⏱ {ROUND_TIME_CROC} сек!",
        parse_mode="Markdown", reply_markup=make_croc_keyboard()
    )
    task = asyncio.create_task(croc_timer(chat_id, ctx))
    games[chat_id]["timer_task"] = task


async def cmd_game(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await start_croc(update.effective_chat.id, update.effective_user, ctx, update.message.reply_text)


# ══════════════════════════════════════════════════════════════════════════════
# 🎡 ПОЛЕ ЧУДЕС
# ══════════════════════════════════════════════════════════════════════════════
async def wheel_timer(chat_id, ctx):
    await asyncio.sleep(ROUND_TIME_WHEEL)
    game = wheel_games.get(chat_id)
    if game and game.get("active"):
        game["active"] = False
        await ctx.bot.send_message(chat_id=chat_id,
            text=f"⏰ Время вышло!\nСлово: *{game['word'].upper()}*\n\n🎡 /wheel",
            parse_mode="Markdown")


async def start_wheel(chat_id, ctx, reply_func):
    if chat_id in wheel_games and wheel_games[chat_id].get("timer_task"):
        wheel_games[chat_id]["timer_task"].cancel()
    category = random.choice(list(WORDS.keys()))
    word = random.choice(WORDS[category]).lower()
    wheel_games[chat_id] = {
        "word": word, "category": category,
        "guessed": set(), "wrong_letters": set(),
        "active": True, "round_scores": {},
        "drum_value": None, "timer_task": None,
        "sabotage_target": None,
    }
    shown = display_word(word, set())
    await reply_func(
        f"🎡 *Поле чудес!*\nКатегория: {category}\n\n"
        f"Слово: `{shown}`\n\n"
        f"Крутите барабан → называйте буквы!\n"
        f"❌ Буква: -100 | ❌ Слово: -150 | ✅ Слово: +500\n⏱ 5 мин!",
        parse_mode="Markdown", reply_markup=make_wheel_keyboard()
    )
    task = asyncio.create_task(wheel_timer(chat_id, ctx))
    wheel_games[chat_id]["timer_task"] = task


async def cmd_wheel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await start_wheel(update.effective_chat.id, ctx, update.message.reply_text)


# ══════════════════════════════════════════════════════════════════════════════
# ⚡ СПИДРАН
# ══════════════════════════════════════════════════════════════════════════════
async def speedrun_timer(chat_id, ctx):
    await asyncio.sleep(SPEEDRUN_TIME)
    game = speed_games.get(chat_id)
    if game and game.get("active"):
        game["active"] = False
        count = game["count"]
        bonus = count * 50
        add_score(game["player_id"], game["player_name"], bonus)
        await ctx.bot.send_message(chat_id=chat_id,
            text=f"⏰ *Спидран завершён!*\n"
                 f"*{game['player_name']}* угадал(а) {count} слов!\n"
                 f"Бонус: +{bonus} очков\n\n📊 /scores",
            parse_mode="Markdown")


async def start_speedrun(chat_id, user, ctx, reply_func):
    p = get_player(user.id, user.first_name)
    if not p["speedrun_access"]:
        await reply_func("⚡ Купи доступ в /shop за 750 очков!", parse_mode="Markdown")
        return
    if chat_id in speed_games and speed_games[chat_id].get("active"):
        await reply_func("⚡ Спидран уже идёт!")
        return
    word = random.choice(SPEEDRUN_WORDS)
    speed_games[chat_id] = {
        "word": word, "active": True,
        "player_id": user.id, "player_name": user.first_name,
        "count": 0, "timer_task": None,
    }
    await reply_func(
        f"⚡ *СПИДРАН!* {user.first_name}\n\n"
        f"30 сек! Угадывай слова!\n\n"
        f"Первое: `{'_ ' * len(word)}`\nБукв: {len(word)}",
        parse_mode="Markdown"
    )
    task = asyncio.create_task(speedrun_timer(chat_id, ctx))
    speed_games[chat_id]["timer_task"] = task


async def cmd_speedrun(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await start_speedrun(update.effective_chat.id, update.effective_user, ctx, update.message.reply_text)


# ══════════════════════════════════════════════════════════════════════════════
# 🧠 ВИКТОРИНА
# ══════════════════════════════════════════════════════════════════════════════
async def trivia_timer(chat_id, ctx):
    await asyncio.sleep(TRIVIA_TIME)
    game = trivia_games.get(chat_id)
    if game and game.get("active"):
        game["active"] = False
        await ctx.bot.send_message(chat_id=chat_id,
            text=f"⏰ Время вышло!\nПравильный ответ: *{game['answer'].upper()}*\n\n🧠 /trivia",
            parse_mode="Markdown")


async def start_trivia(chat_id, ctx, reply_func):
    if chat_id in trivia_games and trivia_games[chat_id].get("timer_task"):
        trivia_games[chat_id]["timer_task"].cancel()
    q = random.choice(TRIVIA)
    trivia_games[chat_id] = {
        "question": q["q"], "answer": q["a"],
        "active": True, "timer_task": None,
    }
    await reply_func(
        f"🧠 *Викторина!*\n\n❓ {q['q']}\n\n"
        f"⏱ {TRIVIA_TIME} секунд на ответ!\n+150 очков за правильный ответ",
        parse_mode="Markdown"
    )
    task = asyncio.create_task(trivia_timer(chat_id, ctx))
    trivia_games[chat_id]["timer_task"] = task


async def cmd_trivia(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await start_trivia(update.effective_chat.id, ctx, update.message.reply_text)


# ══════════════════════════════════════════════════════════════════════════════
# 📝 ВИСЕЛИЦА
# ══════════════════════════════════════════════════════════════════════════════
HANGMAN_PICS = ["😀", "😟", "😰", "😨", "😱", "💀"]

async def hangman_timer(chat_id, ctx):
    await asyncio.sleep(HANGMAN_TIME)
    game = hangman_games.get(chat_id)
    if game and game.get("active"):
        game["active"] = False
        await ctx.bot.send_message(chat_id=chat_id,
            text=f"⏰ Время вышло!\nСлово: *{game['word'].upper()}*\n\n📝 /hangman",
            parse_mode="Markdown")


async def start_hangman(chat_id, ctx, reply_func):
    if chat_id in hangman_games and hangman_games[chat_id].get("timer_task"):
        hangman_games[chat_id]["timer_task"].cancel()
    category = random.choice(list(WORDS.keys()))
    word = random.choice(WORDS[category]).lower()
    hangman_games[chat_id] = {
        "word": word, "category": category,
        "guessed": set(), "errors": 0,
        "active": True, "timer_task": None,
    }
    shown = display_word(word, set())
    await reply_func(
        f"📝 *Виселица!*\nКатегория: {category}\n\n"
        f"{HANGMAN_PICS[0]} Попыток: 6\n\n"
        f"Слово: `{shown}`\n\n"
        f"Называй буквы! +50 за букву, +200 за слово.\n"
        f"6 ошибок = конец игры. ⏱ 2 мин!",
        parse_mode="Markdown"
    )
    task = asyncio.create_task(hangman_timer(chat_id, ctx))
    hangman_games[chat_id]["timer_task"] = task


async def cmd_hangman(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await start_hangman(update.effective_chat.id, ctx, update.message.reply_text)


# ══════════════════════════════════════════════════════════════════════════════
# 🔢 УГАДАЙ ЧИСЛО
# ══════════════════════════════════════════════════════════════════════════════
async def number_timer(chat_id, ctx):
    await asyncio.sleep(NUMBER_TIME)
    game = number_games.get(chat_id)
    if game and game.get("active"):
        game["active"] = False
        await ctx.bot.send_message(chat_id=chat_id,
            text=f"⏰ Время вышло!\nЧисло было: *{game['number']}*\n\n🔢 /number",
            parse_mode="Markdown")


async def start_number(chat_id, user, ctx, reply_func):
    if chat_id in number_games and number_games[chat_id].get("timer_task"):
        number_games[chat_id]["timer_task"].cancel()
    number = random.randint(1, 100)
    number_games[chat_id] = {
        "number": number, "active": True,
        "starter_id": user.id, "attempts": {},
        "timer_task": None,
    }
    await reply_func(
        f"🔢 *Угадай число!*\n\n"
        f"Я загадал число от *1 до 100*\n"
        f"Пиши числа в чат — я подскажу больше/меньше!\n"
        f"+100 очков за угадывание\n⏱ {NUMBER_TIME} сек!",
        parse_mode="Markdown"
    )
    task = asyncio.create_task(number_timer(chat_id, ctx))
    number_games[chat_id]["timer_task"] = task


async def cmd_number(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await start_number(update.effective_chat.id, update.effective_user, ctx, update.message.reply_text)


# ══════════════════════════════════════════════════════════════════════════════
# CALLBACK HANDLER
# ══════════════════════════════════════════════════════════════════════════════
async def callback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id
    user = update.effective_user
    data = query.data
    p = get_player(user.id, user.first_name)
    is_group = update.effective_chat.type in ("group", "supergroup")

    async def reply(text, **kwargs):
        await ctx.bot.send_message(chat_id=chat_id, text=text, **kwargs)

    if data == "menu_game":
        await start_croc(chat_id, user, ctx, reply)
    elif data == "menu_wheel":
        await start_wheel(chat_id, ctx, reply)
    elif data == "menu_speedrun":
        await start_speedrun(chat_id, user, ctx, reply)
    elif data == "menu_trivia":
        await start_trivia(chat_id, ctx, reply)
    elif data == "menu_hangman":
        await start_hangman(chat_id, ctx, reply)
    elif data == "menu_number":
        await start_number(chat_id, user, ctx, reply)
    elif data == "menu_scores":
        await reply(f"📊 *Таблица очков*\n\n{global_scores_text()}", parse_mode="Markdown")
    elif data == "menu_shop":
        await reply(f"🛒 *Магазин*\n\nТвои очки: *{p['total_score']}*",
            parse_mode="Markdown", reply_markup=make_shop_keyboard())
    elif data == "menu_join":
        if chat_id not in group_players:
            group_players[chat_id] = {}
        if user.id in group_players[chat_id]:
            await query.answer("Ты уже в игре!", show_alert=True); return
        group_players[chat_id][user.id] = user.first_name
        names = ", ".join(group_players[chat_id].values())
        await reply(f"✋ *{user.first_name}* присоединился(ась)!\n👥 {names}", parse_mode="Markdown")
    elif data == "menu_back":
        await query.edit_message_reply_markup(reply_markup=make_main_keyboard(is_group))

    elif data == "croc_skip":
        game = games.get(chat_id)
        if not game or not game.get("active"): return
        if user.id != game["explainer_id"]:
            await query.answer("Только объясняющий!", show_alert=True); return
        if game["timer_task"]: game["timer_task"].cancel()
        old = game["word"]
        category = random.choice(list(WORDS.keys()))
        word = random.choice(WORDS[category])
        game["word"] = word.lower(); game["category"] = category
        try:
            await ctx.bot.send_message(chat_id=user.id,
                text=f"⏭ Новое: *{word.upper()}*", parse_mode="Markdown")
        except: pass
        await query.edit_message_text(
            f"⏭ Пропущено (было: *{old}*).\nКатегория: {category}\n⏱ {ROUND_TIME_CROC} сек!",
            parse_mode="Markdown", reply_markup=make_croc_keyboard())
        task = asyncio.create_task(croc_timer(chat_id, ctx))
        game["timer_task"] = task

    elif data == "croc_stop":
        game = games.get(chat_id)
        if not game or not game.get("active"): return
        if user.id != game["explainer_id"]:
            await query.answer("Только объясняющий!", show_alert=True); return
        if game["timer_task"]: game["timer_task"].cancel()
        game["active"] = False
        await query.edit_message_text(
            f"🛑 Стоп.\nСлово: *{game['word'].upper()}*\n\n▶️ /game", parse_mode="Markdown")

    elif data == "wheel_spin":
        game = wheel_games.get(chat_id)
        if not game or not game.get("active"): return
        result = spin_drum()
        if result == "БАНКРОТ":
            if p["protection"]:
                p["protection"] = False
                game["drum_value"] = 100
                await reply(f"🛡 *{user.first_name}* защитился! Барабан: 100\nНазови букву:", parse_mode="Markdown")
            else:
                game["round_scores"][user.id] = 0
                game["drum_value"] = None
                await reply(
                    f"💸 *БАНКРОТ!* {user.first_name} теряет очки!\n\n"
                    f"Слово: `{display_word(game['word'], game['guessed'])}`",
                    parse_mode="Markdown", reply_markup=make_wheel_keyboard())
        elif result == "ПРИЗ":
            bonus = random.choice([300, 500, 700])
            game["round_scores"][user.id] = game["round_scores"].get(user.id, 0) + bonus
            game["drum_value"] = None
            await reply(
                f"🎁 *ПРИЗ!* {user.first_name} +{bonus}!\n\n"
                f"Слово: `{display_word(game['word'], game['guessed'])}`",
                parse_mode="Markdown", reply_markup=make_wheel_keyboard())
        else:
            game["drum_value"] = result
            await reply(f"🎡 *{user.first_name}* крутит: *{result}* очков!\nНазови букву:", parse_mode="Markdown")

    elif data == "wheel_stop":
        game = wheel_games.get(chat_id)
        if not game or not game.get("active"): return
        if game["timer_task"]: game["timer_task"].cancel()
        game["active"] = False
        await query.edit_message_text(
            f"🛑 Стоп.\nСлово: *{game['word'].upper()}*\n\n🎡 /wheel", parse_mode="Markdown")

    elif data == "shop_hint":
        if p["total_score"] < 200:
            await query.answer("Недостаточно очков!", show_alert=True); return
        game = wheel_games.get(chat_id)
        if not game or not game.get("active"):
            await query.answer("Нет активного Поля чудес!", show_alert=True); return
        hidden = [c for c in game["word"] if c not in game["guessed"] and c != " "]
        if not hidden:
            await query.answer("Все буквы открыты!", show_alert=True); return
        letter = random.choice(hidden)
        game["guessed"].add(letter)
        p["total_score"] -= 200
        await reply(
            f"💡 *{user.first_name}* открывает букву (-200): *{letter.upper()}*\n\n"
            f"Слово: `{display_word(game['word'], game['guessed'])}`",
            parse_mode="Markdown", reply_markup=make_wheel_keyboard())

    elif data == "shop_protection":
        if p["total_score"] < 400:
            await query.answer("Недостаточно очков!", show_alert=True); return
        p["total_score"] -= 400; p["protection"] = True
        await query.answer("🛡 Защита активирована!", show_alert=True)

    elif data == "shop_double":
        if p["total_score"] < 500:
            await query.answer("Недостаточно очков!", show_alert=True); return
        p["total_score"] -= 500; p["double"] = True
        await query.answer("🎯 Удвоение активировано!", show_alert=True)

    elif data == "shop_sabotage":
        if p["total_score"] < 350:
            await query.answer("Недостаточно очков!", show_alert=True); return
        game = wheel_games.get(chat_id)
        if not game or not game.get("active"):
            await query.answer("Нет активного Поля чудес!", show_alert=True); return
        p["total_score"] -= 350
        other = [uid for uid in game["round_scores"] if uid != user.id]
        if other:
            target = random.choice(other)
            game["sabotage_target"] = target
            tname = players.get(target, {}).get("name", "игрок")
            await reply(f"💣 *{user.first_name}* — диверсия против *{tname}*!", parse_mode="Markdown")
        else:
            await query.answer("Нет других игроков!", show_alert=True)

    elif data == "shop_vip":
        if p["total_score"] < 1000:
            await query.answer("Недостаточно очков!", show_alert=True); return
        p["total_score"] -= 1000; p["vip"] = True
        await reply(f"👑 *{user.first_name}* получает VIP!", parse_mode="Markdown")

    elif data == "shop_speedrun":
        if p["total_score"] < 750:
            await query.answer("Недостаточно очков!", show_alert=True); return
        if p["speedrun_access"]:
            await query.answer("Уже есть доступ!", show_alert=True); return
        p["total_score"] -= 750; p["speedrun_access"] = True
        await reply(f"⚡ *{user.first_name}* купил(а) Спидран!\n/speedrun", parse_mode="Markdown")


# ══════════════════════════════════════════════════════════════════════════════
# MESSAGE ROUTER
# ══════════════════════════════════════════════════════════════════════════════
async def message_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    p = get_player(user.id, user.first_name)
    text = (update.message.text or "").strip().lower()
    is_group = update.effective_chat.type in ("group", "supergroup")

    # ── Спидран ──
    if chat_id in speed_games and speed_games[chat_id].get("active"):
        game = speed_games[chat_id]
        if user.id != game["player_id"]: return
        if text == game["word"]:
            game["count"] += 1
            new_word = random.choice(SPEEDRUN_WORDS)
            game["word"] = new_word
            await update.message.reply_text(
                f"✅ Верно! Угадано: {game['count']}\n\n"
                f"Следующее: `{'_ ' * len(new_word)}`\nБукв: {len(new_word)}",
                parse_mode="Markdown")
        return

    # ── Угадай число ──
    if chat_id in number_games and number_games[chat_id].get("active"):
        game = number_games[chat_id]
        if text.isdigit():
            guess = int(text)
            number = game["number"]
            game["attempts"][user.id] = game["attempts"].get(user.id, 0) + 1
            if guess == number:
                if game["timer_task"]: game["timer_task"].cancel()
                game["active"] = False
                attempts = game["attempts"][user.id]
                add_score(user.id, user.first_name, 100)
                await update.message.reply_text(
                    f"🎉 *{user.first_name}* угадал(а) число *{number}*!\n"
                    f"За {attempts} попыток! +100 очков\n\n"
                    f"📊 {global_scores_text()}\n\n🔢 /number",
                    parse_mode="Markdown", reply_markup=make_main_keyboard(is_group))
            elif guess < number:
                await update.message.reply_text(f"📈 *{user.first_name}*, больше! (попытка {game['attempts'][user.id]})", parse_mode="Markdown")
            else:
                await update.message.reply_text(f"📉 *{user.first_name}*, меньше! (попытка {game['attempts'][user.id]})", parse_mode="Markdown")
        return

    # ── Викторина ──
    if chat_id in trivia_games and trivia_games[chat_id].get("active"):
        game = trivia_games[chat_id]
        if text == game["answer"]:
            if game["timer_task"]: game["timer_task"].cancel()
            game["active"] = False
            add_score(user.id, user.first_name, 150)
            await update.message.reply_text(
                f"🎉 *{user.first_name}* ответил(а) правильно! +150 очков\n\n"
                f"📊 {global_scores_text()}\n\n🧠 /trivia",
                parse_mode="Markdown", reply_markup=make_main_keyboard(is_group))
        return

    # ── Виселица ──
    if chat_id in hangman_games and hangman_games[chat_id].get("active"):
        game = hangman_games[chat_id]
        word = game["word"]
        guessed = game["guessed"]

        if len(text) > 1:
            if text == word:
                if game["timer_task"]: game["timer_task"].cancel()
                game["active"] = False
                add_score(user.id, user.first_name, 200)
                await update.message.reply_text(
                    f"🎉 *{user.first_name}* угадал(а) слово *{word.upper()}*! +200\n\n"
                    f"📊 {global_scores_text()}\n\n📝 /hangman",
                    parse_mode="Markdown", reply_markup=make_main_keyboard(is_group))
            else:
                await update.message.reply_text(f"❌ Неверно! Слово не *{text.upper()}*.", parse_mode="Markdown")
            return

        if len(text) == 1 and text.isalpha():
            if text in guessed:
                await update.message.reply_text(f"Буква *{text.upper()}* уже была!", parse_mode="Markdown")
                return
            guessed.add(text)
            shown, wrong = display_hangman(word, guessed)
            errors = sum(1 for c in guessed if c not in word)
            game["errors"] = errors
            pic = HANGMAN_PICS[min(errors, 5)]

            if text in word:
                add_score(user.id, user.first_name, 50)
                if set(c for c in word if c != " ") <= guessed:
                    if game["timer_task"]: game["timer_task"].cancel()
                    game["active"] = False
                    add_score(user.id, user.first_name, 200)
                    await update.message.reply_text(
                        f"🎉 *{user.first_name}* открыл(а) все буквы!\nСлово: *{word.upper()}*\n+250 очков\n\n"
                        f"📊 {global_scores_text()}\n\n📝 /hangman",
                        parse_mode="Markdown", reply_markup=make_main_keyboard(is_group))
                else:
                    await update.message.reply_text(
                        f"✅ Буква *{text.upper()}* есть! +50\n\n"
                        f"{pic} Ошибок: {errors}/6\n"
                        f"Слово: `{shown}`\n"
                        f"Неверные: {' '.join(wrong) if wrong else '—'}",
                        parse_mode="Markdown")
            else:
                if errors >= 6:
                    if game["timer_task"]: game["timer_task"].cancel()
                    game["active"] = False
                    await update.message.reply_text(
                        f"💀 *{user.first_name}* проиграл(а)!\nСлово: *{word.upper()}*\n\n📝 /hangman",
                        parse_mode="Markdown", reply_markup=make_main_keyboard(is_group))
                else:
                    await update.message.reply_text(
                        f"❌ Буквы *{text.upper()}* нет!\n\n"
                        f"{pic} Ошибок: {errors}/6\n"
                        f"Слово: `{shown}`\n"
                        f"Неверные: {' '.join(wrong)}",
                        parse_mode="Markdown")
        return

    # ── Поле чудес ──
    if chat_id in wheel_games and wheel_games[chat_id].get("active"):
        game = wheel_games[chat_id]
        word = game["word"]
        guessed = game["guessed"]

        if game.get("sabotage_target") == user.id:
            game["sabotage_target"] = None
            await update.message.reply_text(f"💣 *{user.first_name}* пропускает ход!", parse_mode="Markdown")
            return

        if len(text) > 1:
            if text == word:
                if game["timer_task"]: game["timer_task"].cancel()
                game["active"] = False
                bonus = 500
                game["round_scores"][user.id] = game["round_scores"].get(user.id, 0) + bonus
                rs = max(0, game["round_scores"].get(user.id, 0))
                add_score(user.id, user.first_name, rs)
                await update.message.reply_text(
                    f"🎉 *{user.first_name}* угадал(а) *{word.upper()}*!\n"
                    f"+{bonus} бонус! За раунд: +{rs}\n\n"
                    f"📊 {global_scores_text()}\n\n🎡 /wheel",
                    parse_mode="Markdown", reply_markup=make_main_keyboard(is_group))
            else:
                game["round_scores"][user.id] = game["round_scores"].get(user.id, 0) - 150
                p["streak"] = 0
                await update.message.reply_text(
                    f"❌ *{user.first_name}*, неверно! -150\nСлово: `{display_word(word, guessed)}`",
                    parse_mode="Markdown")
            return

        if len(text) == 1 and text.isalpha():
            if text in guessed or text in game.get("wrong_letters", set()):
                await update.message.reply_text(f"Буква *{text.upper()}* уже была!", parse_mode="Markdown")
                return
            if game.get("drum_value") is None:
                await update.message.reply_text("Сначала крутите барабан! 🎡", parse_mode="Markdown")
                return
            drum_val = game["drum_value"]
            game["drum_value"] = None
            if text in word:
                count = word.count(text)
                guessed.add(text)
                points = drum_val * count if isinstance(drum_val, int) else 0
                if p["double"]:
                    points *= 2; p["double"] = False; dm = " 🎯x2!"
                else:
                    dm = ""
                game["round_scores"][user.id] = game["round_scores"].get(user.id, 0) + points
                p["streak"] = p.get("streak", 0) + 1
                sm = ""
                if p["streak"] >= 3:
                    game["round_scores"][user.id] += 100
                    sm = f"\n🔥 Серия {p['streak']}! +100"
                    p["streak"] = 0
                shown = display_word(word, guessed)
                if set(c for c in word if c != " ") <= guessed:
                    if game["timer_task"]: game["timer_task"].cancel()
                    game["active"] = False
                    rs = max(0, game["round_scores"].get(user.id, 0))
                    add_score(user.id, user.first_name, rs)
                    await update.message.reply_text(
                        f"✅ *{user.first_name}* открыл(а) *{text.upper()}* +{points}{dm}{sm}\n\n"
                        f"🎉 *{word.upper()}*! За раунд: +{rs}\n\n"
                        f"📊 {global_scores_text()}\n\n🎡 /wheel",
                        parse_mode="Markdown", reply_markup=make_main_keyboard(is_group))
                else:
                    await update.message.reply_text(
                        f"✅ *{user.first_name}* +{points}{dm}{sm}\nСлово: `{shown}`",
                        parse_mode="Markdown", reply_markup=make_wheel_keyboard())
            else:
                game.setdefault("wrong_letters", set()).add(text)
                p["streak"] = 0
                game["round_scores"][user.id] = game["round_scores"].get(user.id, 0) - 100
                await update.message.reply_text(
                    f"❌ *{user.first_name}*, *{text.upper()}* нет! -100\nСлово: `{display_word(word, guessed)}`",
                    parse_mode="Markdown", reply_markup=make_wheel_keyboard())
        return

    # ── Крокодил ──
    game = games.get(chat_id)
    if not game or not game.get("active"): return
    if user.id == game["explainer_id"]: return
    if text == game["word"]:
        if game["timer_task"]: game["timer_task"].cancel()
        game["active"] = False
        add_score(user.id, user.first_name, 1)
        add_score(game["explainer_id"], game["explainer_name"], 1)
        await update.message.reply_text(
            f"🎉 *{user.first_name}* угадал(а) *{game['word'].upper()}*!\n\n"
            f"🏅 +1: {user.first_name}\n🏅 +1: {game['explainer_name']}\n\n"
            f"📊 {global_scores_text()}\n\n▶️ /game",
            parse_mode="Markdown", reply_markup=make_main_keyboard(is_group))


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(ChatMemberHandler(greet_new_group, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("scores", cmd_scores))
    app.add_handler(CommandHandler("game", cmd_game))
    app.add_handler(CommandHandler("wheel", cmd_wheel))
    app.add_handler(CommandHandler("speedrun", cmd_speedrun))
    app.add_handler(CommandHandler("trivia", cmd_trivia))
    app.add_handler(CommandHandler("hangman", cmd_hangman))
    app.add_handler(CommandHandler("number", cmd_number))
    app.add_handler(CommandHandler("shop", cmd_shop))
    app.add_handler(CommandHandler("join", cmd_join))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    print("🎮 Бот запущен!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
