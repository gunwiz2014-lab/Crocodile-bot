"""
🐊 Крокодил-бот для Telegram-группы
====================================
Установка:
  pip install python-telegram-bot==20.7

Запуск:
  BOT_TOKEN=ваш_токен python crocodile_bot.py

Как получить токен:
  1. Напишите @BotFather в Telegram
  2. /newbot → задайте имя и username
  3. Скопируйте токен
  4. Добавьте бота в группу и дайте права администратора (необязательно, но желательно)
"""

import os
import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# ─── Токен ────────────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "ВСТАВЬТЕ_ТОКЕН_СЮДА")

# ─── Слова по категориям ──────────────────────────────────────────────────────
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
    "🎬 Фильмы и сериалы": [
        "Матрица", "Титаник", "Гарри Поттер", "Аватар", "Интерстеллар",
        "Игра престолов", "Друзья", "Симпсоны", "Ведьмак", "Шерлок",
        "Начало", "Джокер", "Мандалорец", "Офис", "Черное зеркало",
    ],
    "🌍 Места": [
        "Эйфелева башня", "Колизей", "Великая стена", "Мачу-Пикчу", "Ниагарский водопад",
        "Сахара", "Антарктида", "Амазонка", "Мальдивы", "Байкал",
        "Стоунхендж", "Помпеи", "Венеция", "Гранд-Каньон", "Кремль",
    ],
    "🎭 Профессии": [
        "пожарный", "астронавт", "дирижёр", "кинорежиссёр", "детектив",
        "ветеринар", "повар", "архитектор", "скульптор", "дайвер",
        "каскадёр", "дегустатор", "лётчик", "хирург", "переводчик",
    ],
    "🎲 Разное": [
        "радуга", "землетрясение", "телепортация", "гравитация", "эхо",
        "сновидение", "вулкан", "торнадо", "прилив", "созвездие",
        "магнит", "мираж", "туман", "молния", "лавина",
    ],
}

ROUND_TIME = 60  # секунд на угадывание

# ─── Хранилище состояний игр (chat_id → game_state) ──────────────────────────
games: dict[int, dict] = {}


def get_random_word() -> tuple[str, str]:
    category = random.choice(list(WORDS.keys()))
    word = random.choice(WORDS[category])
    return category, word


def make_game_keyboard(show_skip=True) -> InlineKeyboardMarkup:
    buttons = []
    if show_skip:
        buttons.append(InlineKeyboardButton("⏭ Пропустить слово", callback_data="skip"))
    buttons.append(InlineKeyboardButton("🛑 Завершить игру", callback_data="stop"))
    return InlineKeyboardMarkup([buttons])


def scores_text(scores: dict) -> str:
    if not scores:
        return "Пока никто не набрал очков."
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    lines = []
    medals = ["🥇", "🥈", "🥉"]
    for i, (name, pts) in enumerate(sorted_scores):
        medal = medals[i] if i < 3 else f"{i+1}."
        lines.append(f"{medal} {name} — {pts} очк.")
    return "\n".join(lines)


# ─── /start ───────────────────────────────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🐊 *Крокодил-бот* готов к игре!\n\n"
        "Команды:\n"
        "▶️ /game — начать новый раунд\n"
        "📊 /scores — таблица очков\n"
        "❓ /help — правила\n\n"
        "Добавьте меня в группу и пишите /game!",
        parse_mode="Markdown"
    )


# ─── /help ────────────────────────────────────────────────────────────────────
async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Правила Крокодила*\n\n"
        "1. Один игрок объясняет слово *без слов однокоренных* и без букв из слова.\n"
        "2. Остальные угадывают — пишут слово в чат.\n"
        "3. Кто первый угадал — получает *1 очко*.\n"
        "4. Объясняющий тоже получает *1 очко* за успешное объяснение.\n"
        "5. На каждое слово — *60 секунд*.\n\n"
        "▶️ /game — начать раунд\n"
        "📊 /scores — счёт",
        parse_mode="Markdown"
    )


# ─── /scores ─────────────────────────────────────────────────────────────────
async def cmd_scores(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    game = games.get(chat_id, {})
    scores = game.get("scores", {})
    await update.message.reply_text(
        f"📊 *Таблица очков*\n\n{scores_text(scores)}",
        parse_mode="Markdown"
    )


# ─── /game ────────────────────────────────────────────────────────────────────
async def cmd_game(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    explainer_name = user.first_name

    # Отменяем предыдущий таймер, если был
    if chat_id in games and games[chat_id].get("timer_task"):
        games[chat_id]["timer_task"].cancel()

    category, word = get_random_word()

    # Сохраняем предыдущие очки
    prev_scores = games.get(chat_id, {}).get("scores", {})

    games[chat_id] = {
        "word": word.lower(),
        "category": category,
        "explainer_id": user.id,
        "explainer_name": explainer_name,
        "scores": prev_scores,
        "active": True,
        "timer_task": None,
        "round_msg_id": None,
    }

    # Отправляем слово объясняющему в личку
    try:
        await ctx.bot.send_message(
            chat_id=user.id,
            text=f"🐊 Твоё слово: *{word.upper()}*\n"
                 f"Категория: {category}\n\n"
                 f"Объясняй в группе — не называй само слово и однокоренные!",
            parse_mode="Markdown"
        )
        dm_note = f"✉️ Слово отправлено {explainer_name} в личку."
    except Exception:
        dm_note = (
            f"⚠️ Не смог написать {explainer_name} в личку.\n"
            f"Напиши боту /start в личных сообщениях, чтобы получать слова там."
        )

    msg = await update.message.reply_text(
        f"🐊 *Новый раунд!*\n\n"
        f"Объясняет: *{explainer_name}*\n"
        f"Категория: {category}\n\n"
        f"{dm_note}\n\n"
        f"⏱ У вас *{ROUND_TIME} секунд*. Угадывайте в чате!",
        parse_mode="Markdown",
        reply_markup=make_game_keyboard()
    )

    games[chat_id]["round_msg_id"] = msg.message_id

    # Запускаем таймер
    task = asyncio.create_task(round_timer(chat_id, ctx))
    games[chat_id]["timer_task"] = task


async def round_timer(chat_id: int, ctx: ContextTypes.DEFAULT_TYPE):
    await asyncio.sleep(ROUND_TIME)
    game = games.get(chat_id)
    if game and game.get("active"):
        word = game["word"]
        game["active"] = False
        await ctx.bot.send_message(
            chat_id=chat_id,
            text=f"⏰ *Время вышло!*\n\nСлово было: *{word.upper()}*\n\n"
                 f"📊 Счёт:\n{scores_text(game['scores'])}\n\n"
                 f"▶️ /game — следующий раунд",
            parse_mode="Markdown"
        )


# ─── Inline-кнопки ────────────────────────────────────────────────────────────
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
        await ctx.bot.answer_callback_query(
            query.id, text="Только объясняющий может управлять раундом.", show_alert=True
        )
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
            f"⏭ *{game['explainer_name']}* пропустил слово (было: *{old_word}*).\n\n"
            f"Категория: {category}\n"
            f"⏱ Новые *{ROUND_TIME} секунд* — угадывайте!",
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
            f"🛑 *Раунд завершён* {game['explainer_name']}.\n\n"
            f"Слово было: *{word.upper()}*\n\n"
            f"📊 Счёт:\n{scores_text(game['scores'])}\n\n"
            f"▶️ /game — следующий раунд",
            parse_mode="Markdown"
        )


# ─── Угадывание слова ─────────────────────────────────────────────────────────
async def message_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    game = games.get(chat_id)

    if not game or not game.get("active"):
        return

    # Объясняющий не может угадывать
    if user.id == game["explainer_id"]:
        return

    text = (update.message.text or "").strip().lower()
    word = game["word"]

    if text == word:
        # Отменяем таймер
        if game["timer_task"]:
            game["timer_task"].cancel()

        guesser_name = user.first_name
        explainer_name = game["explainer_name"]

        # Начисляем очки
        game["scores"][guesser_name] = game["scores"].get(guesser_name, 0) + 1
        game["scores"][explainer_name] = game["scores"].get(explainer_name, 0) + 1
        game["active"] = False

        await update.message.reply_text(
            f"🎉 *{guesser_name}* угадал(а) слово *{word.upper()}*!\n\n"
            f"🏅 +1 очко: {guesser_name}\n"
            f"🏅 +1 очко: {explainer_name}\n\n"
            f"📊 Счёт:\n{scores_text(game['scores'])}\n\n"
            f"▶️ /game — следующий раунд",
            parse_mode="Markdown"
        )


# ─── Запуск ───────────────────────────────────────────────────────────────────
def main():
    if BOT_TOKEN == "ВСТАВЬТЕ_ТОКЕН_СЮДА":
        print("❌ Укажите BOT_TOKEN! Получите его у @BotFather.")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("scores", cmd_scores))
    app.add_handler(CommandHandler("game", cmd_game))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("🐊 Крокодил-бот запущен!")
    app.run_polling()


if __name__ == "__main__":
    main()
