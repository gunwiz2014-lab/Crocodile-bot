import os
import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

BOT_TOKEN = os.getenv("BOT_TOKEN", "ВСТАВЬТЕ_ТОКЕН_СЮДА")

WORDS = {
    "🐾 Животные": [
        "жираф", "дельфин", "кенгуру", "хамелеон", "утконос",
        "броненосец", "ленивец", "осьминог", "пингвин", "фламинго",
        "крокодил", "летучая мышь", "морж", "енот", "капибара",
    ],
    "🍕 Еда": [
        "пицца", "суши", "борщ", "шаурма", "мороженое",
        "чизкейк", "круассан", "лазанья", "такос", "вафли",
        "мармелад", "шоколад", "пельмени", "блин", "бургер",
    ],
    "🎬 Фильмы": [
        "Матрица", "Титаник", "Аватар", "Интерстеллар", "Джокер",
        "Начало", "Гладиатор", "Дюна", "Оппенгеймер", "Паразиты",
    ],
    "🌍 Места": [
        "Эйфелева башня", "Колизей", "Мачу-Пикчу", "Байкал", "Сахара",
        "Антарктида", "Амазонка", "Мальдивы", "Стоунхендж", "Кремль",
    ],
    "🎭 Профессии": [
        "пожарный", "астронавт", "дирижёр", "детектив", "ветеринар",
        "повар", "архитектор", "скульптор", "дайвер", "каскадёр",
    ],
    "🎲 Разное": [
        "радуга", "землетрясение", "телепортация", "гравитация", "эхо",
        "сновидение", "вулкан", "торнадо", "молния", "мираж",
    ],
}

ROUND_TIME = 60
games = {}


def get_random_word():
    category = random.choice(list(WORDS.keys()))
    word = random.choice(WORDS[category])
    return category, word


def make_game_keyboard():
    buttons = [
        InlineKeyboardButton("⏭ Пропустить", callback_data="skip"),
        InlineKeyboardButton("🛑 Стоп", callback_data="stop"),
    ]
    return InlineKeyboardMarkup([buttons])


def scores_text(scores):
    if not scores:
        return "Пока никто не набрал очков."
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    medals = ["🥇", "🥈", "🥉"]
    lines = []
    for i, (name, pts) in enumerate(sorted_scores):
        medal = medals[i] if i < 3 else f"{i+1}."
        lines.append(f"{medal} {name} — {pts} очк.")
    return "\n".join(lines)


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🐊 *Крокодил-бот* готов!\n\n"
        "▶️ /game — начать раунд\n"
        "📊 /scores — счёт\n"
        "❓ /help — правила",
        parse_mode="Markdown"
    )


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Правила*\n\n"
        "1. Один игрок объясняет слово без однокоренных слов.\n"
        "2. Остальные угадывают в чате.\n"
        "3. Кто угадал — +1 очко. Объясняющий тоже +1.\n"
        "4. На каждое слово 60 секунд.\n\n"
        "▶️ /game — начать!",
        parse_mode="Markdown"
    )


async def cmd_scores(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    scores = games.get(chat_id, {}).get("scores", {})
    await update.message.reply_text(
        f"📊 *Счёт*\n\n{scores_text(scores)}",
        parse_mode="Markdown"
    )


async def round_timer(chat_id, ctx):
    await asyncio.sleep(ROUND_TIME)
    game = games.get(chat_id)
    if game and game.get("active"):
        word = game["word"]
        game["active"] = False
        await ctx.bot.send_message(
            chat_id=chat_id,
            text=f"⏰ *Время вышло!*\n\nСлово: *{word.upper()}*\n\n"
                 f"📊 Счёт:\n{scores_text(game['scores'])}\n\n▶️ /game",
            parse_mode="Markdown"
        )


async def cmd_game(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user

    if chat_id in games and games[chat_id].get("timer_task"):
        games[chat_id]["timer_task"].cancel()

    category, word = get_random_word()
    prev_scores = games.get(chat_id, {}).get("scores", {})

    games[chat_id] = {
        "word": word.lower(),
        "category": category,
        "explainer_id": user.id,
        "explainer_name": user.first_name,
        "scores": prev_scores,
        "active": True,
        "timer_task": None,
    }

    try:
        await ctx.bot.send_message(
            chat_id=user.id,
            text=f"🐊 Твоё слово: *{word.upper()}*\nКатегория: {category}\n\nОбъясняй в группе!",
            parse_mode="Markdown"
        )
        dm = f"✉️ Слово отправлено {user.first_name} в личку."
    except Exception:
        dm = f"⚠️ Напиши боту /start в личку чтобы получать слова."

    await update.message.reply_text(
        f"🐊 *Новый раунд!*\n\nОбъясняет: *{user.first_name}*\n"
        f"Категория: {category}\n\n{dm}\n\n⏱ {ROUND_TIME} секунд!",
        parse_mode="Markdown",
        reply_markup=make_game_keyboard()
    )

    task = asyncio.create_task(round_timer(chat_id, ctx))
    games[chat_id]["timer_task"] = task


async def callback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id
    user = update.effective_user
    game = games.get(chat_id)

    if not game or not game.get("active"):
        await query.edit_message_reply_markup(reply_markup=None)
        return

    if user.id != game["explainer_id"]:
        await query.answer("Только объясняющий может управлять раундом.", show_alert=True)
        return

    if query.data == "skip":
        if game["timer_task"]:
            game["timer_task"].cancel()
        old_word = game["word"]
        category, word = get_random_word()
        game["word"] = word.lower()
        game["category"] = category
        try:
            await ctx.bot.send_message(
                chat_id=user.id,
                text=f"⏭ Новое слово: *{word.upper()}*\nКатегория: {category}",
                parse_mode="Markdown"
            )
        except Exception:
            pass
        await query.edit_message_text(
            f"⏭ Пропущено (было: *{old_word}*).\n\nКатегория: {category}\n⏱ {ROUND_TIME} секунд!",
            parse_mode="Markdown",
            reply_markup=make_game_keyboard()
        )
        task = asyncio.create_task(round_timer(chat_id, ctx))
        game["timer_task"] = task

    elif query.data == "stop":
        if game["timer_task"]:
            game["timer_task"].cancel()
        word = game["word"]
        game["active"] = False
        await query.edit_message_text(
            f"🛑 Раунд остановлен.\n\nСлово: *{word.upper()}*\n\n"
            f"📊 Счёт:\n{scores_text(game['scores'])}\n\n▶️ /game",
            parse_mode="Markdown"
        )


async def message_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    game = games.get(chat_id)

    if not game or not game.get("active"):
        return
    if user.id == game["explainer_id"]:
        return

    text = (update.message.text or "").strip().lower()
    if text == game["word"]:
        if game["timer_task"]:
            game["timer_task"].cancel()
        guesser = user.first_name
        explainer = game["explainer_name"]
        game["scores"][guesser] = game["scores"].get(guesser, 0) + 1
        game["scores"][explainer] = game["scores"].get(explainer, 0) + 1
        game["active"] = False
        await update.message.reply_text(
            f"🎉 *{guesser}* угадал(а) *{game['word'].upper()}*!\n\n"
            f"🏅 +1: {guesser}\n🏅 +1: {explainer}\n\n"
            f"📊 Счёт:\n{scores_text(game['scores'])}\n\n▶️ /game",
            parse_mode="Markdown"
        )


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("scores", cmd_scores))
    app.add_handler(CommandHandler("game", cmd_game))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    print("🐊 Бот запущен!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
