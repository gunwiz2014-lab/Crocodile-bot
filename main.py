import os
import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

BOT_TOKEN = os.getenv("BOT_TOKEN", "ВСТАВЬТЕ_ТОКЕН_СЮДА")

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

DRUM = [100, 100, 200, 200, 300, 300, 500, 500, 1000, "БАНКРОТ", "БАНКРОТ", "ПРИЗ"]

ROUND_TIME_CROC = 60
ROUND_TIME_WHEEL = 300  # 5 минут
SPEEDRUN_TIME = 30

# ─── ХРАНИЛИЩЕ ────────────────────────────────────────────────────────────────
games = {}        # chat_id → croc game
wheel_games = {}  # chat_id → wheel game
speed_games = {}  # chat_id → speedrun game
players = {}      # user_id → {name, total_score, speedrun_access, vip, streak, protection, double, sabotage_target}


def get_player(user_id, name):
    if user_id not in players:
        players[user_id] = {
            "name": name,
            "total_score": 0,
            "speedrun_access": False,
            "vip": False,
            "streak": 0,
            "protection": False,
            "double": False,
            "sabotage": 0,
        }
    players[user_id]["name"] = name
    return players[user_id]


def add_score(user_id, name, amount):
    p = get_player(user_id, name)
    p["total_score"] = max(0, p["total_score"] + amount)


def get_score(user_id, name):
    return get_player(user_id, name)["total_score"]


def scores_text(score_dict):
    if not score_dict:
        return "Пока никто не набрал очков."
    sorted_s = sorted(score_dict.items(), key=lambda x: x[1], reverse=True)
    medals = ["🥇", "🥈", "🥉"]
    lines = []
    for i, (name, pts) in enumerate(sorted_s):
        medal = medals[i] if i < 3 else f"{i+1}."
        vip = " 👑" if any(p["name"] == name and p["vip"] for p in players.values()) else ""
        lines.append(f"{medal} {name}{vip} — {pts} оч.")
    return "\n".join(lines)


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


# ─── /start ───────────────────────────────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎮 *Игровой бот* готов!\n\n"
        "🐊 /game — Крокодил\n"
        "🎡 /wheel — Поле чудес\n"
        "⚡ /speedrun — Спидран *(купить в магазине)*\n"
        "🛒 /shop — Магазин\n"
        "📊 /scores — Таблица очков\n"
        "❓ /help — Правила",
        parse_mode="Markdown"
    )


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Правила*\n\n"
        "🐊 *Крокодил* — один объясняет, остальные угадывают. +1 очко угадавшему и объясняющему.\n\n"
        "🎡 *Поле чудес* — угадывайте буквы и слово. "
        "Барабан даёт 100/200/300/500/1000/БАНКРОТ. "
        "Неверная буква: -100. Неверное слово: -150. "
        "Угадать слово: +500 бонус. Серия из 3 букв подряд: +100.\n\n"
        "⚡ *Спидран* — 30 секунд, угадай как можно больше слов. "
        "Доступен после покупки в /shop за 750 очков.\n\n"
        "🛒 *Магазин* — тратьте очки на усиления!",
        parse_mode="Markdown"
    )


async def cmd_scores(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"📊 *Таблица очков*\n\n{global_scores_text()}",
        parse_mode="Markdown"
    )


# ══════════════════════════════════════════════════════════════════════════════
# 🐊 КРОКОДИЛ
# ══════════════════════════════════════════════════════════════════════════════
def make_croc_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("⏭ Пропустить", callback_data="croc_skip"),
        InlineKeyboardButton("🛑 Стоп", callback_data="croc_stop"),
    ]])


async def croc_timer(chat_id, ctx):
    await asyncio.sleep(ROUND_TIME_CROC)
    game = games.get(chat_id)
    if game and game.get("active"):
        game["active"] = False
        await ctx.bot.send_message(
            chat_id=chat_id,
            text=f"⏰ Время вышло!\n\nСлово: *{game['word'].upper()}*\n\n▶️ /game",
            parse_mode="Markdown"
        )


async def cmd_game(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    get_player(user.id, user.first_name)

    if chat_id in games and games[chat_id].get("timer_task"):
        games[chat_id]["timer_task"].cancel()

    category = random.choice(list(WORDS.keys()))
    word = random.choice(WORDS[category])
    prev_scores = games.get(chat_id, {}).get("scores", {})

    games[chat_id] = {
        "word": word.lower(), "category": category,
        "explainer_id": user.id, "explainer_name": user.first_name,
        "scores": prev_scores, "active": True, "timer_task": None,
    }

    try:
        await ctx.bot.send_message(chat_id=user.id,
            text=f"🐊 Твоё слово: *{word.upper()}*\nКатегория: {category}",
            parse_mode="Markdown")
        dm = f"✉️ Слово отправлено {user.first_name} в личку."
    except Exception:
        dm = "⚠️ Напиши боту /start в личку!"

    await update.message.reply_text(
        f"🐊 *Новый раунд!*\n\nОбъясняет: *{user.first_name}*\n"
        f"Категория: {category}\n\n{dm}\n\n⏱ {ROUND_TIME_CROC} секунд!",
        parse_mode="Markdown", reply_markup=make_croc_keyboard()
    )
    task = asyncio.create_task(croc_timer(chat_id, ctx))
    games[chat_id]["timer_task"] = task


# ══════════════════════════════════════════════════════════════════════════════
# 🎡 ПОЛЕ ЧУДЕС
# ══════════════════════════════════════════════════════════════════════════════
def display_word(word, guessed):
    return " ".join(c if c in guessed or c == " " else "\_" for c in word)


def spin_drum():
    return random.choice(DRUM)


def make_wheel_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🎡 Крутить барабан", callback_data="wheel_spin"),
        InlineKeyboardButton("🛑 Стоп", callback_data="wheel_stop"),
    ]])


async def wheel_timer(chat_id, ctx):
    await asyncio.sleep(ROUND_TIME_WHEEL)
    game = wheel_games.get(chat_id)
    if game and game.get("active"):
        game["active"] = False
        await ctx.bot.send_message(
            chat_id=chat_id,
            text=f"⏰ Время вышло!\n\nСлово было: *{game['word'].upper()}*\n\n🎡 /wheel — новый раунд",
            parse_mode="Markdown"
        )


async def cmd_wheel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if chat_id in wheel_games and wheel_games[chat_id].get("timer_task"):
        wheel_games[chat_id]["timer_task"].cancel()

    category = random.choice(list(WORDS.keys()))
    word = random.choice(WORDS[category]).lower()
    prev_scores = wheel_games.get(chat_id, {}).get("scores", {})

    wheel_games[chat_id] = {
        "word": word, "category": category,
        "guessed": set(), "active": True,
        "scores": prev_scores, "round_scores": {},
        "drum_value": None, "timer_task": None,
        "wrong_letters": set(),
    }

    shown = display_word(word, set())
    await update.message.reply_text(
        f"🎡 *Поле чудес!*\n\nКатегория: {category}\n\n"
        f"Слово: `{shown}`\n\n"
        f"Нажмите барабан и угадывайте буквы!\n"
        f"❌ Неверная буква: -100 | ❌ Неверное слово: -150\n"
        f"⏱ 5 минут на раунд!",
        parse_mode="Markdown", reply_markup=make_wheel_keyboard()
    )
    task = asyncio.create_task(wheel_timer(chat_id, ctx))
    wheel_games[chat_id]["timer_task"] = task


async def wheel_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    game = wheel_games.get(chat_id)

    if not game or not game.get("active"):
        return

    text = (update.message.text or "").strip().lower()
    word = game["word"]
    guessed = game["guessed"]
    p = get_player(user.id, user.first_name)

    # Проверка диверсии
    if game.get("sabotage_target") == user.id:
        game["sabotage_target"] = None
        await update.message.reply_text(f"💣 *{user.first_name}* пропускает ход (диверсия)!", parse_mode="Markdown")
        return

    # Угадывание слова целиком
    if len(text) > 1 and text != word:
        penalty = 150
        if p["double"]:
            penalty = 300
            p["double"] = False
        game["round_scores"][user.id] = game["round_scores"].get(user.id, 0) - penalty
        p["streak"] = 0
        await update.message.reply_text(
            f"❌ *{user.first_name}*, неверно! -{penalty} очков за раунд.\n"
            f"Слово: `{display_word(word, guessed)}`",
            parse_mode="Markdown"
        )
        return

    if len(text) > 1 and text == word:
        if game["timer_task"]:
            game["timer_task"].cancel()
        game["active"] = False
        bonus = 500
        game["round_scores"][user.id] = game["round_scores"].get(user.id, 0) + bonus
        rs = game["round_scores"].get(user.id, 0)
        add_score(user.id, user.first_name, rs)
        await update.message.reply_text(
            f"🎉 *{user.first_name}* угадал(а) слово *{word.upper()}*!\n"
            f"+{bonus} бонус! Итого за раунд: +{rs}\n\n"
            f"📊 Счёт:\n{global_scores_text()}\n\n🎡 /wheel",
            parse_mode="Markdown"
        )
        return

    # Угадывание буквы
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

            # Удвоение
            if p["double"]:
                points *= 2
                p["double"] = False
                double_msg = " 🎯 *Удвоение сработало!*"
            else:
                double_msg = ""

            game["round_scores"][user.id] = game["round_scores"].get(user.id, 0) + points

            # Серия
            p["streak"] = p.get("streak", 0) + 1
            streak_bonus = 0
            streak_msg = ""
            if p["streak"] >= 3:
                streak_bonus = 100
                game["round_scores"][user.id] += streak_bonus
                streak_msg = f"\n🔥 Серия {p['streak']}! +{streak_bonus} бонус!"
                p["streak"] = 0

            shown = display_word(word, guessed)

            if set(c for c in word if c != " ") <= guessed:
                if game["timer_task"]:
                    game["timer_task"].cancel()
                game["active"] = False
                rs = game["round_scores"].get(user.id, 0)
                add_score(user.id, user.first_name, rs)
                await update.message.reply_text(
                    f"✅ *{user.first_name}* открыл(а) букву *{text.upper()}* ({count} шт.) +{points}{double_msg}{streak_msg}\n\n"
                    f"🎉 Слово открыто: *{word.upper()}*!\n"
                    f"Итого за раунд: +{rs}\n\n"
                    f"📊 Счёт:\n{global_scores_text()}\n\n🎡 /wheel",
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text(
                    f"✅ *{user.first_name}* открыл(а) букву *{text.upper()}* ({count} шт.) +{points}{double_msg}{streak_msg}\n\n"
                    f"Слово: `{shown}`",
                    parse_mode="Markdown", reply_markup=make_wheel_keyboard()
                )
        else:
            game.setdefault("wrong_letters", set()).add(text)
            p["streak"] = 0
            penalty = 100
            game["round_scores"][user.id] = game["round_scores"].get(user.id, 0) - penalty
            shown = display_word(word, guessed)
            await update.message.reply_text(
                f"❌ *{user.first_name}*, буквы *{text.upper()}* нет! -{penalty} очков за раунд.\n\n"
                f"Слово: `{shown}`",
                parse_mode="Markdown", reply_markup=make_wheel_keyboard()
            )


# ══════════════════════════════════════════════════════════════════════════════
# ⚡ СПИДРАН
# ══════════════════════════════════════════════════════════════════════════════
async def cmd_speedrun(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    p = get_player(user.id, user.first_name)

    if not p["speedrun_access"]:
        await update.message.reply_text(
            "⚡ *Спидран режим*\n\n"
            "Этот режим нужно купить в магазине за 750 очков!\n"
            "🛒 /shop",
            parse_mode="Markdown"
        )
        return

    if chat_id in speed_games and speed_games[chat_id].get("active"):
        await update.message.reply_text("⚡ Спидран уже идёт!")
        return

    word = random.choice(SPEEDRUN_WORDS)
    speed_games[chat_id] = {
        "word": word, "active": True,
        "player_id": user.id, "player_name": user.first_name,
        "count": 0, "start_time": asyncio.get_event_loop().time(),
        "timer_task": None,
    }

    await update.message.reply_text(
        f"⚡ *СПИДРАН!* {user.first_name}\n\n"
        f"30 секунд! Угадывай слова как можно быстрее!\n\n"
        f"Первое слово: `{'_ ' * len(word)}`\n"
        f"Букв: {len(word)}",
        parse_mode="Markdown"
    )

    task = asyncio.create_task(speedrun_timer(chat_id, ctx))
    speed_games[chat_id]["timer_task"] = task


async def speedrun_timer(chat_id, ctx):
    await asyncio.sleep(SPEEDRUN_TIME)
    game = speed_games.get(chat_id)
    if game and game.get("active"):
        game["active"] = False
        count = game["count"]
        bonus = count * 50
        add_score(game["player_id"], game["player_name"], bonus)
        await ctx.bot.send_message(
            chat_id=chat_id,
            text=f"⏰ *Спидран завершён!*\n\n"
                 f"*{game['player_name']}* угадал(а) {count} слов!\n"
                 f"Бонус: +{bonus} очков\n\n"
                 f"📊 /scores",
            parse_mode="Markdown"
        )


async def speedrun_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    game = speed_games.get(chat_id)

    if not game or not game.get("active"):
        return
    if user.id != game["player_id"]:
        return

    text = (update.message.text or "").strip().lower()
    if text == game["word"]:
        game["count"] += 1
        elapsed = asyncio.get_event_loop().time() - game["start_time"]
        remaining = max(0, SPEEDRUN_TIME - elapsed)

        new_word = random.choice(SPEEDRUN_WORDS)
        game["word"] = new_word
        game["start_time"] = asyncio.get_event_loop().time()

        await update.message.reply_text(
            f"✅ Верно! Угадано: {game['count']}\n"
            f"⏱ Осталось: {int(remaining)} сек\n\n"
            f"Следующее слово: `{'_ ' * len(new_word)}`\n"
            f"Букв: {len(new_word)}",
            parse_mode="Markdown"
        )


# ══════════════════════════════════════════════════════════════════════════════
# 🛒 МАГАЗИН
# ══════════════════════════════════════════════════════════════════════════════
def make_shop_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💡 Подсказка — 200 оч.", callback_data="shop_hint")],
        [InlineKeyboardButton("🛡 Защита от банкрота — 400 оч.", callback_data="shop_protection")],
        [InlineKeyboardButton("🎯 Удвоение — 500 оч.", callback_data="shop_double")],
        [InlineKeyboardButton("💣 Диверсия — 350 оч.", callback_data="shop_sabotage")],
        [InlineKeyboardButton("👑 VIP статус — 1000 оч.", callback_data="shop_vip")],
        [InlineKeyboardButton("⚡ Спидран доступ — 750 оч.", callback_data="shop_speedrun")],
    ])


async def cmd_shop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    p = get_player(user.id, user.first_name)
    await update.message.reply_text(
        f"🛒 *Магазин*\n\n"
        f"Твои очки: *{p['total_score']}*\n\n"
        f"💡 *Подсказка* — открыть случайную букву в Поле чудес\n"
        f"🛡 *Защита от банкрота* — следующий банкрот не сработает\n"
        f"🎯 *Удвоение* — следующая буква даёт x2 очков\n"
        f"💣 *Диверсия* — следующий игрок пропускает ход\n"
        f"👑 *VIP статус* — значок 👑 в таблице\n"
        f"⚡ *Спидран доступ* — открыть режим спидрана",
        parse_mode="Markdown",
        reply_markup=make_shop_keyboard()
    )


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

    # ── Крокодил ──
    if data == "croc_skip":
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
                text=f"⏭ Новое слово: *{word.upper()}*", parse_mode="Markdown")
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
            f"🛑 Раунд остановлен.\nСлово: *{game['word'].upper()}*\n\n▶️ /game",
            parse_mode="Markdown")

    # ── Поле чудес ──
    elif data == "wheel_spin":
        game = wheel_games.get(chat_id)
        if not game or not game.get("active"): return
        result = spin_drum()
        if result == "БАНКРОТ":
            if p["protection"]:
                p["protection"] = False
                await query.answer("🛡 Защита сработала! Банкрот отменён.", show_alert=True)
                game["drum_value"] = 100
                await ctx.bot.send_message(chat_id=chat_id,
                    text=f"🛡 *{user.first_name}* защитился от БАНКРОТА! Барабан: 100",
                    parse_mode="Markdown")
            else:
                game["round_scores"][user.id] = 0
                game["drum_value"] = None
                await ctx.bot.send_message(chat_id=chat_id,
                    text=f"💸 *БАНКРОТ!* {user.first_name} теряет очки за этот раунд!\n\n"
                         f"Слово: `{display_word(game['word'], game['guessed'])}`",
                    parse_mode="Markdown", reply_markup=make_wheel_keyboard())
        elif result == "ПРИЗ":
            bonus = random.choice([300, 500, 700])
            game["round_scores"][user.id] = game["round_scores"].get(user.id, 0) + bonus
            game["drum_value"] = None
            await ctx.bot.send_message(chat_id=chat_id,
                text=f"🎁 *ПРИЗ!* {user.first_name} получает {bonus} очков!\n\n"
                     f"Слово: `{display_word(game['word'], game['guessed'])}`",
                parse_mode="Markdown", reply_markup=make_wheel_keyboard())
        else:
            game["drum_value"] = result
            await ctx.bot.send_message(chat_id=chat_id,
                text=f"🎡 *{user.first_name}* крутит барабан: *{result}* очков!\n\nНазови букву:",
                parse_mode="Markdown")

    elif data == "wheel_stop":
        game = wheel_games.get(chat_id)
        if not game or not game.get("active"): return
        if game["timer_task"]: game["timer_task"].cancel()
        game["active"] = False
        await query.edit_message_text(
            f"🛑 Раунд остановлен.\nСлово: *{game['word'].upper()}*\n\n🎡 /wheel",
            parse_mode="Markdown")

    # ── Магазин ──
    elif data == "shop_hint":
        if p["total_score"] < 200:
            await query.answer("Недостаточно очков!", show_alert=True); return
        game = wheel_games.get(chat_id)
        if not game or not game.get("active"):
            await query.answer("Сейчас нет активного Поля чудес!", show_alert=True); return
        hidden = [c for c in game["word"] if c not in game["guessed"] and c != " "]
        if not hidden:
            await query.answer("Все буквы уже открыты!", show_alert=True); return
        letter = random.choice(hidden)
        game["guessed"].add(letter)
        p["total_score"] -= 200
        await ctx.bot.send_message(chat_id=chat_id,
            text=f"💡 *{user.first_name}* использует подсказку (-200 оч.)\n"
                 f"Открыта буква: *{letter.upper()}*\n\n"
                 f"Слово: `{display_word(game['word'], game['guessed'])}`",
            parse_mode="Markdown", reply_markup=make_wheel_keyboard())

    elif data == "shop_protection":
        if p["total_score"] < 400:
            await query.answer("Недостаточно очков!", show_alert=True); return
        p["total_score"] -= 400
        p["protection"] = True
        await query.answer("🛡 Защита от банкрота активирована!", show_alert=True)

    elif data == "shop_double":
        if p["total_score"] < 500:
            await query.answer("Недостаточно очков!", show_alert=True); return
        p["total_score"] -= 500
        p["double"] = True
        await query.answer("🎯 Удвоение активировано!", show_alert=True)

    elif data == "shop_sabotage":
        if p["total_score"] < 350:
            await query.answer("Недостаточно очков!", show_alert=True); return
        game = wheel_games.get(chat_id)
        if not game or not game.get("active"):
            await query.answer("Сейчас нет активного Поля чудес!", show_alert=True); return
        p["total_score"] -= 350
        other_players = [uid for uid in game["round_scores"] if uid != user.id]
        if other_players:
            target = random.choice(other_players)
            game["sabotage_target"] = target
            target_name = players.get(target, {}).get("name", "игрок")
            await ctx.bot.send_message(chat_id=chat_id,
                text=f"💣 *{user.first_name}* применяет диверсию против *{target_name}*!\n"
                     f"Следующий ход {target_name} будет пропущен!",
                parse_mode="Markdown")
        else:
            await query.answer("Нет других игроков!", show_alert=True)

    elif data == "shop_vip":
        if p["total_score"] < 1000:
            await query.answer("Недостаточно очков!", show_alert=True); return
        p["total_score"] -= 1000
        p["vip"] = True
        await ctx.bot.send_message(chat_id=chat_id,
            text=f"👑 *{user.first_name}* получает VIP статус!",
            parse_mode="Markdown")

    elif data == "shop_speedrun":
        if p["total_score"] < 750:
            await query.answer("Недостаточно очков!", show_alert=True); return
        if p["speedrun_access"]:
            await query.answer("У тебя уже есть доступ!", show_alert=True); return
        p["total_score"] -= 750
        p["speedrun_access"] = True
        await ctx.bot.send_message(chat_id=chat_id,
            text=f"⚡ *{user.first_name}* купил(а) доступ к Спидрану!\n/speedrun — вперёд!",
            parse_mode="Markdown")


# ══════════════════════════════════════════════════════════════════════════════
# MESSAGE ROUTER
# ══════════════════════════════════════════════════════════════════════════════
async def message_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    get_player(user.id, user.first_name)

    # Спидран
    if chat_id in speed_games and speed_games[chat_id].get("active"):
        await speedrun_message(update, ctx)
        return

    # Поле чудес
    if chat_id in wheel_games and wheel_games[chat_id].get("active"):
        await wheel_message(update, ctx)
        return

    # Крокодил
    game = games.get(chat_id)
    if not game or not game.get("active"): return
    if user.id == game["explainer_id"]: return

    text = (update.message.text or "").strip().lower()
    if text == game["word"]:
        if game["timer_task"]: game["timer_task"].cancel()
        guesser = user.first_name
        explainer = game["explainer_name"]
        game["scores"][guesser] = game["scores"].get(guesser, 0) + 1
        game["scores"][explainer] = game["scores"].get(explainer, 0) + 1
        add_score(user.id, guesser, 1)
        add_score(game["explainer_id"], explainer, 1)
        game["active"] = False
        await update.message.reply_text(
            f"🎉 *{guesser}* угадал(а) *{game['word'].upper()}*!\n\n"
            f"🏅 +1: {guesser}\n🏅 +1: {explainer}\n\n"
            f"📊 Счёт:\n{global_scores_text()}\n\n▶️ /game",
            parse_mode="Markdown"
        )


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("scores", cmd_scores))
    app.add_handler(CommandHandler("game", cmd_game))
    app.add_handler(CommandHandler("wheel", cmd_wheel))
    app.add_handler(CommandHandler("speedrun", cmd_speedrun))
    app.add_handler(CommandHandler("shop", cmd_shop))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    print("🎮 Бот запущен!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
