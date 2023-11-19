import requests
from telegram.ext import JobQueue
import logging
import sqlite3
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext
TOKEN = '6329575854:AAEWTNYX_Lz-yKFRb3Q22o-tmUauXCA0f_M'

# Настройка логирования ошибок
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
room_timers = {}
# Функция для подключения к базе данных
def connect_db():
    return sqlite3.connect('bot_database.db')

# Создайте таблицу, если она не существует
with connect_db() as conn:
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            balance REAL,
            chat_id INTEGER
        )
    ''')
    conn.commit()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player1_chat_id INT,
        player2_chat_id INT,
        Bet INT,
        player1_dice INT DEFAULT 0,
        player2_dice INT DEFAULT 0,
        player1_balance DECIMAL(10, 2) DEFAULT 0,
        player2_balance DECIMAL(10, 2) DEFAULT 0,
        total_winnings DECIMAL(10, 2) DEFAULT 0,
        status VARCHAR(10) DEFAULT 'open'
    )
    ''')
    conn.commit()

# Функция для проверки существования записи в базе данных
def user_exists(conn, user_id):
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM users WHERE chat_id = ?", (user_id,))
    return cursor.fetchone() is not None

# Функция для удаления всех записей из таблицы 'rooms'
def delete_all_rooms():
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM rooms")
        conn.commit()

# Функция для обработки команды /start
def start(update: Update, context: CallbackContext):
    # Проверяем наличие update.message
    if update.message:
        user = update.message.from_user
        username = user.username
        first_name = user.first_name
        last_name = user.last_name
        user_id = update.message.chat_id
        message_to_edit = update.message.reply_text(f"Привет, {first_name}! Выберите одну из опций:")
    else:
        # Если update.message отсутствует, значит, это было вызвано из кнопки "Меню"
        # В этом случае, можно использовать информацию из callback_query
        user = update.callback_query.from_user
        username = user.username
        first_name = user.first_name
        last_name = user.last_name
        user_id = update.callback_query.message.chat_id
        message_to_edit = update.callback_query.message

    try:
        # Используем контекстный менеджер для создания и выполнения SQL-запроса
        with connect_db() as conn:
            # Проверяем, существует ли запись с данным chat_id
            if not user_exists(conn, user_id):
                # Если записи нет, выполняем вставку
                cursor = conn.cursor()
                cursor.execute("INSERT INTO users (username, first_name, last_name, balance, chat_id) VALUES (?, ?, ?, ?, ?)",
                               (username, first_name, last_name, 0.0, user_id))
                conn.commit()

        # Создание клавиатуры с инлайн-кнопками
        keyboard = [
            [
                InlineKeyboardButton("🎲Играть", callback_data="play"),
                InlineKeyboardButton("💰Финансы", callback_data="finances")
            ],
            [
                InlineKeyboardButton("🐞Нашел Баг?", callback_data="bug"),
                InlineKeyboardButton("📞Поддержка", callback_data="support")
            ],
            [
                InlineKeyboardButton("⚙️Настройки", callback_data="settings"),
                InlineKeyboardButton("⚙️Настройки", callback_data="dell")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Изменение сообщения
        context.bot.edit_message_text(
            chat_id=user_id,
            message_id=message_to_edit.message_id,
            text=f"Привет, {first_name}! Выберите одну из опций:",
            reply_markup=reply_markup
        )

    except Exception as e:
        logger.error(f"Ошибка при выполнении команды /start: {str(e)}")
        if update.message:
            update.message.reply_text(f"{username} Произошла ошибка. Пожалуйста, попробуйте позже.")
        else:
            update.callback_query.message.reply_text(f"{username} Произошла ошибка. Пожалуйста, попробуйте позже.")
def delete_room(context: CallbackContext):
    room_id = context.job.context
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM rooms WHERE id = ?", (room_id,))
        conn.commit()
# Функция для обработки нажатий на инлайн-кнопки
def button(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    data = query.data.split(':')
    action = data[0]
    value = int(data[1]) if len(data) > 1 else None
    if query.data == "play":
        # Обработка нажатия кнопки "Играть"
        keyboard = [
            [
                InlineKeyboardButton("⚔Создать Комнату", callback_data="create_r"),
                InlineKeyboardButton("Присоединится в комнату", callback_data="join_r")

            ],
            [
                InlineKeyboardButton("📊Статистика", callback_data="stats"),
                InlineKeyboardButton("🏠Главное Меню", callback_data="menu")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(text="Выберите игру:", reply_markup=reply_markup)

    elif query.data == "finances":
        # Обработка нажатия кнопки "Финансы"
        #query.edit_message_text(text="Вы выбрали Финансы 💰")
        balance_info(update, context)
    elif query.data == "bug":
        # Обработка нажатия кнопки "Нашел Баг?"
        query.edit_message_text(text="Вы выбрали Нашел Баг? 🐞")

    elif query.data == "support":
        # Обработка нажатия кнопки "Поддержка"
        query.edit_message_text(text="Вы выбрали Поддержка 📞")

    elif query.data == "settings":
        # Обработка нажатия кнопки "Настройки"
        query.edit_message_text(text="Вы выбрали Настройки ⚙️")

    elif query.data == "menu":
        start(update, context)
    elif query.data == "duel":
        duel(update, context)
    elif query.data == "dell":
        delete_all_rooms()
    elif query.data == "create_r":
        create_room(update, context)
    elif query.data == "join_r":
        join_room(update, context)
        join_room(update, context, value)
    elif query.data == "play100":
        bet_value = 100
        set_bet(update, context, bet_value)
    elif query.data == "play1000":
        bet_value = 1000
        set_bet(update, context, bet_value)
    elif query.data == "play5000":
        bet_value = 5000
        set_bet(update, context, bet_value)
    elif query.data == "play10000":
        bet_value = 10000
        set_bet(update, context, bet_value)
    elif query.data == "p100":
        bet_value = 100
        join_room1(update,context,bet_value)
    elif query.data == "p1000":
        bet_value = 1000
        join_room1(update,context,bet_value)
    elif query.data == "p5000":
        bet_value = 5000
        join_room1(update,context,bet_value)
    elif query.data == "p10000":
        bet_value = 10000
        join_room1(update,context,bet_value)
    elif query.data == "transfer_to_another_bot":
        transfer_to_another_bot1(update, context)
    elif query.data == "e100":
        toamount = 100
        transfer_to_another_bot2(update,context,toamount)
    elif query.data == "e1000":
        toamount = 1000
        transfer_to_another_bot2(update,context,toamount)
    elif query.data == "e5000":
        toamount = 5000
        transfer_to_another_bot2(update,context,toamount)
    elif query.data == "e10000":
        toamount = 10000
        transfer_to_another_bot2(update,context,toamount)
    elif query.data == "transfer_from_another_bot":
        transfer_from_another_bot1(update, context)
    elif query.data == "f100":
        toamount = 100
        transfer_from_another_bot2(update,context,toamount)
    elif query.data == "f1000":
        toamount = 1000
        transfer_from_another_bot2(update,context,toamount)
    elif query.data == "f5000":
        toamount = 5000
        transfer_from_another_bot2(update,context,toamount)
    elif query.data == "f10000":
        toamount = 10000
        transfer_from_another_bot2(update,context,toamount)
def transfer_to_another_bot1(update: Update, context: CallbackContext):
    query = update.callback_query
    text = "Укажите сумму обмена"
    keyboard2 = [
            [
                InlineKeyboardButton("💰100 PR", callback_data="e100"),
                InlineKeyboardButton("💰1000 PR", callback_data="e1000")
            ],
            [
                InlineKeyboardButton("💰5000 PR", callback_data="e5000"),
                InlineKeyboardButton("💰10000 PR", callback_data="e10000")
            ],
            [
                InlineKeyboardButton("🏠Главное Меню", callback_data="menu")
            ]
        ]
    reply_markup2 = InlineKeyboardMarkup(keyboard2)
    query.edit_message_text(text=text,reply_markup = reply_markup2)

def transfer_to_another_bot2(update: Update, context: CallbackContext,toamount):
    user_id = update.callback_query.message.chat_id
    query = update.callback_query
    amount = toamount

    # Transfer funds from this bot to another bot
    success, error = transfer_tbalance(user_id, amount)

    if success:
        # Update the user's balance in the local database
        update_balance_in_database(user_id, -amount)

        text = f"Перевод {amount} PR на другой бот выполнен успешно!"
    else:
        text = f"Ошибка при переводе баланса: {error}"
    query.edit_message_text(text=text)
    # Edit the original message and display the result
def transfer_from_another_bot1(update: Update, context: CallbackContext):
    query = update.callback_query
    text = "Укажите сумму обмена"
    keyboard2 = [
            [
                InlineKeyboardButton("💰100 PR", callback_data="f100"),
                InlineKeyboardButton("💰1000 PR", callback_data="f1000")
            ],
            [
                InlineKeyboardButton("💰5000 PR", callback_data="f5000"),
                InlineKeyboardButton("💰10000 PR", callback_data="f10000")
            ],
            [
                InlineKeyboardButton("🏠Главное Меню", callback_data="menu")
            ]
        ]
    reply_markup2 = InlineKeyboardMarkup(keyboard2)
    query.edit_message_text(text=text,reply_markup = reply_markup2)

def transfer_from_another_bot2(update: Update, context: CallbackContext,toamount):
    user_id = update.callback_query.message.chat_id
    query = update.callback_query
    amount = toamount

    # Transfer funds from this bot to another bot
    success, error = transfer_fbalance(user_id, amount)

    if success:
        # Update the user's balance in the local database
        update_balance_in_database(user_id, amount)

        text = f"Перевод {amount} PR на этот бот выполнен успешно!"
    else:
        text = f"Ошибка при переводе баланса: {error}"

    # Edit the original message and display the result
    query.edit_message_text(text=text)
def transfer_tbalance(user_id, amount):
    API_URL = "https://pr.social/api/transfer_balance/"
    # Perform the transfer using the API
    params = {
        "key": "Owuftwg4PJV31SP6",
        "us_id": user_id,
        "type": "to",
        "num": amount,
        "currency": "pr",
    }

    response = requests.get(API_URL, params=params)

    # Process the response
    if response.status_code == 200:
        data = response.json()
        if data.get("error"):
            return False, f"Error: {data['error']}"
        elif data.get("success"):
            return True, None
    else:
        return False, f"Failed to transfer balance. Status code: {response.status_code}"
def transfer_fbalance(user_id, amount):
    API_URL = "https://pr.social/api/transfer_balance/"
    # Perform the transfer using the API
    params = {
        "key": "Owuftwg4PJV31SP6",
        "us_id": user_id,
        "type": "from",
        "num": amount,
        "currency": "pr",
    }

    response = requests.get(API_URL, params=params)

    # Process the response
    if response.status_code == 200:
        data = response.json()
        if data.get("error"):
            return False, f"Error: {data['error']}"
        elif data.get("success"):
            return True, None
    else:
        return False, f"Failed to transfer balance. Status code: {response.status_code}"

def update_balance_in_database(user_id, amount):
    # Update the user's balance in the local database
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET balance = balance + ? WHERE chat_id = ?", (amount, user_id))
        conn.commit()
def balance_info(update: Update, context: CallbackContext):
    user_id = update.callback_query.message.chat_id
    query = update.callback_query

    # Получение баланса пользователя
    balance, error = get_balance(user_id)
    balance2, error = get_balance_from_database(user_id)

    if error:
        query.edit_message_text(text=f"Ошибка при получении баланса: {error}")
        return

    # Вывод баланса и создание кнопок для обмена
    text = f"Ваш баланс: {balance} PR\nВаш баланс в боте:  {balance2}"

    keyboard = [
        [InlineKeyboardButton("Обменять Баланс", callback_data="exchange_balance")],
        [InlineKeyboardButton("С игрового бота на другой бот", callback_data="transfer_to_another_bot")],
        [InlineKeyboardButton("С другого бота на игровой бот", callback_data="transfer_from_another_bot")],
        [InlineKeyboardButton("🏠Главное Меню", callback_data="menu")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    query.edit_message_text(text=text, reply_markup=reply_markup)
def get_balance_from_database(user_id):
    # Здесь вы должны написать код для получения баланса из вашей базы данных
    # Пример:
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM users WHERE chat_id = ?", (user_id,))
        result = cursor.fetchone()

        if result:
            return result[0], None
        else:
            return None, "Пользователь не найден в базе данных"
def get_balance(user_id):
    api_url = "https://pr.social/api/transfer_balance/"
    api_key = "Owuftwg4PJV31SP6"

    # Запрос для получения баланса
    params = {
        "key": api_key,
        "type": "balance",
        "us_id": user_id,
        "currency": "pr"
    }

    response = requests.get(api_url,params = params)

    # Обработка ответа
    if response.status_code == 200:
        data = response.json()
        if data.get("error"):
            return None, f"Error: {data['error']}"
        elif data.get("success"):
            return data['success'], None
    else:
        return None, f"Failed to retrieve balance. Status code: {response.status_code}"

def create_room(update: Update, context: CallbackContext):
    user_id = update.callback_query.message.chat_id
    query = update.callback_query
    keyboard2 = [
            [
                InlineKeyboardButton("💰100 PR", callback_data="play100"),
                InlineKeyboardButton("💰1000 PR", callback_data="play1000")
            ],
            [
                InlineKeyboardButton("💰5000 PR", callback_data="play5000"),
                InlineKeyboardButton("💰10000 PR", callback_data="play10000")
            ],
            [
                InlineKeyboardButton("🏠Главное Меню", callback_data="menu")
            ]
        ]
    reply_markup2 = InlineKeyboardMarkup(keyboard2)
    query.edit_message_text(text="Перед созданием комнаты выберите ставку",reply_markup=reply_markup2)
def set_bet(update: Update, context: CallbackContext, bet_value):
    user_id = update.callback_query.message.chat_id
    try:
        with connect_db() as conn:
            cursor = conn.cursor()
            # Проверяем, создана ли уже комната для данного пользователя
            cursor.execute("SELECT id FROM rooms WHERE player1_chat_id = ? AND status = 'betted'", (user_id,))
            existing_room = cursor.fetchone()

            if existing_room:
                context.bot.send_message(user_id, "Вы уже создали комнату. Ожидайте присоединения второго игрока.")
                return

            # Создаем запись в базе данных
            cursor.execute("INSERT INTO rooms (player1_chat_id, player2_chat_id, Bet, status) VALUES (?, NULL, ?, 'betted')", (user_id, bet_value))
            conn.commit()

            # Получаем идентификатор только что созданной комнаты
            cursor.execute("SELECT last_insert_rowid()")
            room_id = cursor.fetchone()[0]

            # Устанавливаем таймер на 60 секунд для удаления комнаты
            job = context.job_queue.run_once(delete_room, 60, context=room_id)
            room_timers[room_id] = job

            context.bot.send_message(user_id, f"Вы успешно создали комнату c ставкой {bet_value}, подождите, чтобы к комнате кто-то присоединился. Если в течение минуты никто не подключится, то комната удалится.")
    except Exception as e:
        logger.error(f"Error in set_bet: {str(e)}")
# Функция для обработки нажатия кнопки "Дуэль"
def duel(update: Update, context: CallbackContext):
    user_id = update.callback_query.message.chat_id

    # Проверяем, есть ли свободные комнаты с ожидающими игроками
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, player1_chat_id FROM rooms WHERE status = 'open' AND player1_chat_id != ?", (user_id,))
        room = cursor.fetchone()

        if room:
            # Присоединяемся к существующей комнате
            room_id, player1_chat_id = room
            cursor.execute("UPDATE rooms SET player2_chat_id = ? WHERE id = ?", (user_id, room_id))
            cursor.execute("UPDATE rooms SET status = 'started' WHERE id = ?", (room_id,))
            conn.commit()

            # Отправляем сообщение об начале игры обоим игрокам
            dice_handler(update, context)

        else:
            # Поиск активных комнат, в которых текущий пользователь уже является первым игроком
            cursor.execute("SELECT id FROM rooms WHERE status = 'open' AND player1_chat_id = ?", (user_id,))
            room = cursor.fetchone()

            if room:
                # В этой комнате пользователь уже является первым игроком, ничего не делаем
                pass
            else:
                # Создаем новую комнату для текущего игрока
                cursor.execute("INSERT INTO rooms (player1_chat_id, player2_chat_id, status) VALUES (?, NULL, 'open')", (user_id,))
                conn.commit()
                update.callback_query.message.reply_text("Ожидание другого игрока...")

# Глобальные статусы комнаты
ROOM_STATUS_BETTED = "betted"
ROOM_STATUS_OPEN = "open"     # Комната открыта для присоединения другого игрока
ROOM_STATUS_STARTED = "started"  # Игра началась
ROOM_STATUS_ENDED = "ended"  # Игра закончилась
def dice_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.message.chat_id
    chat_id = query.message.chat_id
    message_id = query.message.message_id

    try:
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, player1_chat_id, player2_chat_id, player1_dice, player2_dice, status FROM rooms WHERE (player1_chat_id = ? OR player2_chat_id = ?) AND (status = ? OR status = ? OR status = ?)",
                           (user_id, user_id, ROOM_STATUS_BETTED, ROOM_STATUS_STARTED, ROOM_STATUS_OPEN))
            room = cursor.fetchone()

            if room:
                room_id, player1_chat_id, player2_chat_id, player1_dice, player2_dice, room_status = room
                if room_status == ROOM_STATUS_BETTED:
                    cursor.execute("UPDATE rooms SET status = 'open' WHERE id = ?", (room_id,))
                if room_status == ROOM_STATUS_STARTED:
                    print("Sending dice for player 1")
                    bot_dice = context.bot.send_dice(chat_id=player1_chat_id, emoji='🎲').dice.value
                    print(f"Player 1 dice value: {bot_dice}")
                    cursor.execute("UPDATE rooms SET player1_dice = ? WHERE id = ?", (bot_dice, room_id))
                    print("Sending dice for player 2")
                    bot_dice = context.bot.send_dice(chat_id=player2_chat_id, emoji='🎲').dice.value
                    print(f"Player 2 dice value: {bot_dice}")
                    cursor.execute("UPDATE rooms SET player2_dice = ? WHERE id = ?", (bot_dice, room_id))

                    conn.commit()

                    cursor.execute("SELECT player1_dice, player2_dice FROM rooms WHERE id = ?", (room_id,))
                    player1_dice, player2_dice = cursor.fetchone()

                    if player1_dice != 0 and player2_dice != 0:
                        if player1_dice > player2_dice:
                            cursor.execute("UPDATE users SET balance = balance + ? WHERE chat_id = ?", (amount, player1_chat_id,))

                            cursor.execute("UPDATE users SET balance = balance - ? WHERE chat_id = ?", (amount, player2_chat_id,))

                            winner_id = player1_chat_id
                        elif player1_dice < player2_dice:
                            cursor.execute("UPDATE users SET balance = balance - ? WHERE chat_id = ?", (amount, player1_chat_id,))

                            cursor.execute("UPDATE users SET balance = balance + ? WHERE chat_id = ?", (amount, player2_chat_id,))

                            winner_id = player2_chat_id
                        else:
                            winner_id = None

                        conn.commit()

                        context.bot.send_message(player1_chat_id, f"Вы бросили {player1_dice}, противник бросил {player2_dice}.")
                        context.bot.send_message(player2_chat_id, f"Вы бросили {player2_dice}, противник бросил {player1_dice}.")

                        if winner_id:
                            context.bot.send_message(winner_id, "Вы выиграли игру!")

                        cursor.execute("UPDATE rooms SET status = 'ended' WHERE id = ?", (room_id,))
                        conn.commit()

                    else:
                        context.bot.send_message(chat_id, "Ожидание броска противника...")

                elif room_status == ROOM_STATUS_ENDED:
                    context.bot.send_message(chat_id, "Ожидание начала игры...")
            else:
                context.bot.send_message(chat_id, "Ожидание начала игры...")

    except Exception as e:
        logger.error(f"Error in dice_handler: {str(e)}")


def join_room1(update: Update, context: CallbackContext,bet_value):
    query = update.callback_query
    user_id = query.message.chat_id

    try:
        with connect_db() as conn:
            cursor = conn.cursor()

            # Retrieve the user's balance
            cursor.execute("SELECT balance FROM users WHERE chat_id = ?", (user_id,))
            user_balance = cursor.fetchone()[0]

            # Check if the user has enough balance to join the room
            if user_balance >= bet_value:
                # Deduct the bet amount from the user's balance
                new_balance = user_balance - bet_value

                # Update the user's balance in the database
                cursor.execute("UPDATE users SET balance = ? WHERE chat_id = ?", (new_balance, user_id))
                conn.commit()

                # Find available rooms with the chosen bet
                cursor.execute("SELECT id FROM rooms WHERE status = 'betted' AND Bet = ? AND player1_chat_id != ?", (bet_value, user_id))
                available_rooms = cursor.fetchall()

                if available_rooms:
                    # Connect the user to the first available room
                    room_id = available_rooms[0][0]
                    cursor.execute("UPDATE rooms SET player2_chat_id = ?, status = 'started' WHERE id = ?", (user_id, room_id))
                    conn.commit()

                    # Send a message about successful connection
                    query.edit_message_text(text=f"Вы успешно присоединились к комнате с ставкой {bet_value} PR. Игра началась!")

                    # Run the dice handler for the dice roll
                    dice_handler(update, context)
                else:
                    query.edit_message_text(text=f"Нет доступных комнат с выбранной ставкой {bet_value} PR.")
            else:
                query.edit_message_text(text=f"У вас недостаточно средств для присоединения к комнате с ставкой {bet_value} PR.")

    except Exception as e:
        logger.error(f"Error in join_room1: {str(e)}")

def join_room(update, context, page_number=1):
    with connect_db() as conn:
        query = update.callback_query
        user_id = query.message.chat_id
        all_buttons = []

        # Query rooms from the database based on the page number
        cursor = conn.cursor()
        cursor.execute("SELECT Bet, COUNT(*) FROM rooms WHERE status = 'betted' GROUP BY Bet")
        games_count = dict(cursor.fetchall())
        # Создайте строку с новым текстом, используя games_count
        new_text = "Выберите комнату:\n"
        for bet, count in games_count.items():
            if (bet == 100):
                button = InlineKeyboardButton(f"💰{bet} PR💰", callback_data=f"p{bet}")
            elif (bet == 1000):
                button = InlineKeyboardButton(f"💰{bet} PR💰", callback_data=f"p{bet}")
            elif (bet == 5000):
                button = InlineKeyboardButton(f"💰{bet} PR💰", callback_data=f"p{bet}")
            elif (bet == 10000):
                button = InlineKeyboardButton(f"💰{bet} PR💰", callback_data=f"p{bet}")

            all_buttons.append([button])
            new_text += f"💰{bet} PR💰 - 🎲{count} game🎲\n"

        all_buttons.append([
            InlineKeyboardButton("🏠Главное Меню", callback_data="menu")
        ])
        # Создайте новую разметку
        new_markup = InlineKeyboardMarkup(all_buttons)

        # Получите текущий текст и разметку
        current_text = query.message.text
        current_markup = query.message.reply_markup

        # Проверьте, отличается ли новый текст или разметка от текущих
        if new_text != current_text or new_markup != current_markup:
            query.edit_message_text(text=new_text, reply_markup=new_markup)






def main():
    updater = Updater(TOKEN)
    dp = updater.dispatcher

    # Обработка команды /start
    dp.add_handler(CommandHandler("start", start))
    #dp.add_handler(CallbackQueryHandler(button_click))
        # Обработка нажатий на инлайн-кнопки
    dp.add_handler(CallbackQueryHandler(button))
    dp.add_handler(MessageHandler(Filters.dice, dice_handler))
    dp.add_handler(CallbackQueryHandler(join_room))

    # Запуск бота
    updater.start_polling()
    updater.idle()
    delete_all_rooms()  # Удалить все записи из таблицы 'rooms'

if __name__ == '__main__':
    main()
