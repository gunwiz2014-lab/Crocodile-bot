import os
import random
import telebot
from telebot import types

# Берем токен из переменных окружения Railway
TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

# База данных пользователей в памяти
user_data = {}

# Викторина по уровням сложности
QUIZ = {
    "easy": [
        {"q": "Сколько дней в неделе?", "a": "7"},
        {"q": "Какого цвета трава?", "a": "зеленая"},
        {"q": "Зимой и летом одним цветом. Что это?", "a": "елка"}
    ],
    "medium": [
        {"q": "Какая планета ближе всего к Солнцу?", "a": "меркурий"},
        {"q": "Сколько градусов в прямом угле?", "a": "90"},
        {"q": "Автор романа 'Преступление и наказание'?", "a": "достоевский"}
    ],
    "hard": [
        {"q": "Какое химическое вещество имеет формулу O3?", "a": "озон"},
        {"q": "В каком году затонул Титаник?", "a": "1912"},
        {"q": "Какая пустыня является самой большой в мире?", "a": "антарктическая"}
    ]
}

# Магазин: Предмет, Базовая цена, Скидка (%)
SHOP = {
    "👑 VIP Статус": {"price": 500, "discount": 20},
    "🍀 Амулет Удачи (X2 монеты)": {"price": 300, "discount": 10},
    "🃏 Эксклюзивная колода": {"price": 150, "discount": 0},
    "🔥 Огненная аватарка": {"price": 100, "discount": 50},
    "🎁 Секретный бокс": {"price": 250, "discount": 15}
}

CARD_DECK = ["6", "7", "8", "9", "10", "Валет", "Дама", "Король", "Туз"]
CARD_VALUES = {card: idx for idx, card in enumerate(CARD_DECK)}

UNO_COLORS = ["Красный", "Желтый", "Зеленый", "Синий"]
UNO_VALUES = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "Пропуск хода", "Разворот"]

def init_user(user_id):
    if user_id not in user_data:
        user_data[user_id] = {
            "balance": 100,
            "inventory": [],
            "state": "menu",
            "quiz_level": None,
            "quiz_q": None,
            "active": True
        }

def main_menu_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("🎮 Игры"),
        types.KeyboardButton("🛍️ Магазин со скидками"),
        types.KeyboardButton("👤 Профиль"),
        types.KeyboardButton("🛑 ОСТАНОВИТЬ БОТА")
    )
    return markup

def games_menu_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("❓ Викторина (3 уровня)"),
        types.KeyboardButton("🔴 Игра Уно"),
        types.KeyboardButton("🃏 Высокая Карта"),
        types.KeyboardButton("🎲 Кубик (Рандом)"),
        types.KeyboardButton("⬅️ В главное меню")
    )
    return markup

def quiz_menu_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    markup.add(types.KeyboardButton("🟢 Легкий"), types.KeyboardButton("🟡 Средний"), types.KeyboardButton("🔴 Сложный"))
    markup.add(types.KeyboardButton("⬅️ Назад к играм"))
    return markup

@bot.message_handler(func=lambda msg: True)
def handle_messages(message):
    user_id = message.from_user.id
    init_user(user_id)
    
    text = message.text

    if not user_data[user_id]["active"]:
        if text in ["/start", "🚀 Запустить бота заново"]:
            user_data[user_id]["active"] = True
            user_data[user_id]["state"] = "menu"
            bot.send_message(message.chat.id, "Бот снова активирован!", reply_markup=main_menu_keyboard())
        return

    if text == "🛑 ОСТАНОВИТЬ БОТА":
        user_data[user_id]["active"] = False
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("🚀 Запустить бота заново"))
        bot.send_message(message.chat.id, "🛑 Бот остановлен. Игровой процесс заморожен.", reply_markup=markup)
        return

    if text in ["⬅️ В главное меню", "/start"]:
        user_data[user_id]["state"] = "menu"
        bot.send_message(message.chat.id, "Вы в главном меню платформы:", reply_markup=main_menu_keyboard())
        return
        
    if text == "⬅️ Назад к играм":
        user_data[user_id]["state"] = "games"
        bot.send_message(message.chat.id, "Выберите игру:", reply_markup=games_menu_keyboard())
        return

    # МЕНЮ
    if user_data[user_id]["state"] == "menu":
        if text == "🎮 Игры":
            user_data[user_id]["state"] = "games"
            bot.send_message(message.chat.id, "🎮 Добро пожаловать в игровой зал!", reply_markup=games_menu_keyboard())
            
        elif text == "🛍️ Магазин со скидками":
            user_data[user_id]["state"] = "shop"
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
            msg_text = "🛍️ **МАГАЗИН СКИДОК** 🛍️\n\n"
            
            for item, info in SHOP.items():
                final_price = int(info["price"] * (1 - info["discount"]/100))
                if info["discount"] > 0:
                    msg_text += f"• {item} — 💰 *{final_price} монет* (~~{info['price']}~~) [-{info['discount']}%]\n"
                else:
                    msg_text += f"• {item} — 💰 *{final_price} монет*\n"
                markup.add(types.KeyboardButton(f"Купить {item}"))
            
            markup.add(types.KeyboardButton("⬅️ В главное меню"))
            bot.send_message(message.chat.id, msg_text, parse_mode="Markdown", reply_markup=markup)
            
        elif text == "👤 Профиль":
            ud = user_data[user_id]
            inv = ", ".join(ud["inventory"]) if ud["inventory"] else "Пусто"
            bot.send_message(message.chat.id, f"👤 **Профиль:**\n\n💰 Баланс: {ud['balance']} монет\n📦 Инвентарь: {inv}", parse_mode="Markdown")

    # МАГАЗИН
    elif user_data[user_id]["state"] == "shop" and text.startswith("Купить "):
        item_to_buy = text.replace("Купить ", "")
        if item_to_buy in SHOP:
            info = SHOP[item_to_buy]
            final_price = int(info["price"] * (1 - info["discount"]/100))
            
            if user_data[user_id]["balance"] >= final_price:
                user_data[user_id]["balance"] -= final_price
                user_data[user_id]["inventory"].append(item_to_buy)
                bot.send_message(message.chat.id, f"🎉 Куплено: **{item_to_buy}** за {final_price} монет.", parse_mode="Markdown")
            else:
                bot.send_message(message.chat.id, "❌ Недостаточно монет!")

    # ИГРЫ
    elif user_data[user_id]["state"] == "games":
        if text == "❓ Викторина (3 уровня)":
            user_data[user_id]["state"] = "quiz_choice"
            bot.send_message(message.chat.id, "Выбери сложность викторины:", reply_markup=quiz_menu_keyboard())
            
        elif text == "🎲 Кубик (Рандом)":
            b_score, u_score = random.randint(1, 6), random.randint(1, 6)
            msg = f"🤖 Бот: {b_score}\n👤 Ты: {u_score}\n\n"
            if u_score > b_score:
                user_data[user_id]["balance"] += 20
                msg += "🎉 +20 монет!"
            elif u_score < b_score:
                user_data[user_id]["balance"] = max(0, user_data[user_id]["balance"] - 10)
                msg += "😢 -10 монет."
            else:
                msg += "🤝 Ничья."
            bot.send_message(message.chat.id, msg)
            
        elif text == "🃏 Высокая Карта":
            b_card, u_card = random.choice(CARD_DECK), random.choice(CARD_DECK)
            msg = f"🤖 Бот: *{b_card}*\n👤 Ты: *{u_card}*\n\n"
            if CARD_VALUES[u_card] > CARD_VALUES[b_card]:
                user_data[user_id]["balance"] += 30
                msg += "🏆 Твоя карта старше! +30 монет!"
            elif CARD_VALUES[u_card] < CARD_VALUES[b_card]:
                user_data[user_id]["balance"] = max(0, user_data[user_id]["balance"] - 15)
                msg += "📉 Карта бота старше. -15 монет."
            else:
                msg += "⚖️ Ничья."
            bot.send_message(message.chat.id, msg, parse_mode="Markdown")
            
        elif text == "🔴 Игра Уно":
            bot_card = f"{random.choice(UNO_COLORS)} {random.choice(UNO_VALUES)}"
            user_card = f"{random.choice(UNO_COLORS)} {random.choice(UNO_VALUES)}"
            msg = f"🤖 Карта бота: `{bot_card}`\n👤 Твоя карта: `{user_card}`\n\n"
            
            b_color, b_val = bot_card.split(" ", 1)
            u_color, u_val = user_card.split(" ", 1)
            
            if b_color == u_color or b_val == u_val:
                user_data[user_id]["balance"] += 40
                msg += "🔥 УНО! Карты совпали! +40 монет! 🎉"
            else:
                user_data[user_id]["balance"] = max(0, user_data[user_id]["balance"] - 20)
                msg += "❌ Не совпало. Штраф -20 монет."
            bot.send_message(message.chat.id, msg, parse_mode="Markdown")

    # ВЫБОР СЛОЖНОСТИ
    elif user_data[user_id]["state"] == "quiz_choice":
        level = None
        if text == "🟢 Легкий": level = "easy"
        elif text == "🟡 Средний": level = "medium"
        elif text == "🔴 Сложный": level = "hard"
        
        if level:
            q_item = random.choice(QUIZ[level])
            user_data[user_id]["state"] = "quiz_answering"
            user_data[user_id]["quiz_level"] = level
            user_data[user_id]["quiz_q"] = q_item
            
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(types.KeyboardButton("🏳️ Сдаться"))
            bot.send_message(message.chat.id, f"Вопрос:\n\n*{q_item['q']}*", parse_mode="Markdown", reply_markup=markup)

    # ОТВЕТ НА ВОПРОС
    elif user_data[user_id]["state"] == "quiz_answering":
        if text == "🏳️ Сдаться":
            user_data[user_id]["state"] = "games"
            bot.send_message(message.chat.id, "Возвращаемся в меню.", reply_markup=games_menu_keyboard())
            return
            
        correct_ans = user_data[user_id]["quiz_q"]["a"]
        level = user_data[user_id]["quiz_level"]
        rewards = {"easy": 15, "medium": 35, "hard": 70}
        
        if text.strip().lower() == correct_ans:
            reward = rewards[level]
            user_data[user_id]["balance"] += reward
            bot.send_message(message.chat.id, f"🎉 Правильно! +{reward} монет.", reply_markup=games_menu_keyboard())
        else:
            bot.send_message(message.chat.id, "❌ Неверно. Попробуй еще раз или нажми '🏳️ Сдаться'.")
        
        user_data[user_id]["state"] = "games"

if __name__ == '__main__':
    bot.polling(none_stop=True)
