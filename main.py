import random
import types
import pyodbc
import time
import datetime  # Импорт модуля datetime

import telebot as telebot
import threading

bot = telebot.TeleBot('')

titles = {}



# Обработчик команды /start
@bot.message_handler(commands=['start'])
def handle_start(message):
    bot.reply_to(message, "Привет! Я бот для управления беседой. Используйте команды /kick, /ban, /unban, /add.")

# Словарь для хранения замученных пользователей
muted_users = {}


# Функция для сохранения данных о замученных пользователях в базе данных
def save_muted_user(user_id, chat_id, admin_id, unmute_time=None):
    cursor.execute(
        "INSERT INTO MutedUsers (UserID, MutedAt, UnmutedAt, AdminID, ChatID) VALUES (?, GETDATE(), ?, ?, ?)", user_id,
        unmute_time, admin_id, chat_id)
    connection.commit()


# Обработчик команды /mute
@bot.message_handler(commands=['mute'])
def handle_mute(message):
    if is_administrator(message):
        if message.reply_to_message:
            user_id = message.reply_to_message.from_user.id
            chat_id = message.chat.id
            admin_id = message.from_user.id

            time_str = message.text.split(' ', 1)[1]
            time_value = int(time_str[:-1])
            time_unit = time_str[-1]
            time_units = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
            if time_unit in time_units:
                mute_time = time_value * time_units[time_unit]
                unmute_time = datetime.datetime.now() + datetime.timedelta(seconds=mute_time)

                # Записываем данные о замученном пользователе в базу данных
                save_muted_user(user_id, chat_id, admin_id, unmute_time)

                # Устанавливаем таймер для автоматического снятия мута
                threading.Timer(mute_time, handle_unmute_auto, args=[message]).start()

                bot.restrict_chat_member(chat_id, user_id, can_send_messages=False, can_send_media_messages=False,
                                         can_send_other_messages=False, can_add_web_page_previews=False)
                bot.reply_to(message, f"Пользователь {user_id} был замучен в беседе на {time_value} {time_unit}.")
            else:
                bot.reply_to(message, "Неправильный формат времени.")
        else:
            bot.reply_to(message, "Пожалуйста, ответьте на сообщение пользователя, которого вы хотите замутить.")
    else:
        bot.reply_to(message, "У вас нет прав на выполнение этой команды.")


# Функция для удаления данных о замученных пользователях из базы данных
def remove_muted_user(user_id, chat_id):
    cursor.execute("DELETE FROM MutedUsers WHERE UserID = ? AND ChatID = ?", user_id, chat_id)
    connection.commit()


# Обработчик команды /unmute
@bot.message_handler(commands=['unmute'])
def handle_unmute(message):
    if is_administrator(message):
        if message.reply_to_message:
            user_id = message.reply_to_message.from_user.id
            chat_id = message.chat.id

            # Убираем пользователя из списка замученных
            remove_muted_user(user_id, chat_id)
            bot.restrict_chat_member(chat_id, user_id, can_send_messages=True, can_send_media_messages=True,
                                     can_send_other_messages=True, can_add_web_page_previews=True)
            bot.reply_to(message, f"Пользователь {user_id} был размучен в беседе.")
        else:
            bot.reply_to(message, "Пожалуйста, ответьте на сообщение пользователя, которого вы хотите размутить.")
    else:
        bot.reply_to(message, "У вас нет прав на выполнение этой команды.")


# Функция для автоматического снятия мута по истечении времени
def handle_unmute_auto(message):
    user_id = message.reply_to_message.from_user.id
    chat_id = message.chat.id
    remove_muted_user(user_id, chat_id)
    bot.restrict_chat_member(chat_id, user_id, can_send_messages=True, can_send_media_messages=True,
                             can_send_other_messages=True, can_add_web_page_previews=True)
    bot.reply_to(message, f"Мут пользователя {user_id} был автоматически снят.")

# Функция для сохранения данных о кикнутых пользователях в базу данных
def save_kicked_user(user_id, chat_id, admin_id):
    cursor.execute(f"INSERT INTO KickedUsers (UserID, ChatID, AdminID) VALUES (?, ?, ?)", user_id, chat_id, admin_id)
    connection.commit()

# Обработчик команды /kick
@bot.message_handler(commands=['kick'])
def handle_kick(message):
    if is_administrator(message):
        if message.reply_to_message:
            user_id = message.reply_to_message.from_user.id
            chat_id = message.chat.id
            admin_id = message.from_user.id
            # Записываем данные о кикнутом пользователе в базу данных
            save_kicked_user(user_id, chat_id, admin_id)
            bot.kick_chat_member(chat_id, user_id)
            bot.reply_to(message, f"Пользователь {user_id} был кикнут из беседы.")
        else:
            bot.reply_to(message, "Пожалуйста, ответьте на сообщение пользователя, которого вы хотите кикнуть.")
    else:
        bot.reply_to(message, "У вас нет прав на выполнение этой команды.")

# Функция для сохранения данных о пользователях в базу данных
def save_user_data(user_id, chat_id, table):
    cursor.execute(f"IF NOT EXISTS (SELECT * FROM {table} WHERE UserID = ? AND ChatID = ?) INSERT INTO {table} (UserID, ChatID) VALUES (?, ?)", user_id, chat_id, user_id, chat_id)
    connection.commit()

# Обработчик команды /ban
@bot.message_handler(commands=['ban'])
def handle_ban(message):
    if is_administrator(message):
        if message.reply_to_message:
            user_id = message.reply_to_message.from_user.id
            chat_id = message.chat.id
            # Записываем данные о забаненном пользователе в базу данных
            save_user_data(user_id, chat_id, 'BannedUsers')
            bot.kick_chat_member(chat_id, user_id)
            bot.reply_to(message, f"Пользователь {user_id} был забанен в беседе.")
        else:
            bot.reply_to(message, "Пожалуйста, ответьте на сообщение пользователя, которого вы хотите забанить.")
    else:
        bot.reply_to(message, "У вас нет прав на выполнение этой команды.")

# Обработчик команды /unban
@bot.message_handler(commands=['unban'])
def handle_unban(message):
    if is_administrator(message):
        if message.reply_to_message:
            user_id = message.reply_to_message.from_user.id
            chat_id = message.chat.id
            # Удаляем данные о разбаненном пользователе из базы данных
            cursor.execute("DELETE FROM BannedUsers WHERE UserID = ? AND ChatID = ?", user_id, chat_id)
            connection.commit()
            bot.unban_chat_member(chat_id, user_id)
            bot.reply_to(message, f"Пользователь {user_id} был разбанен в беседе.")
        else:
            bot.reply_to(message, "Пожалуйста, ответьте на сообщение пользователя, которого вы хотите разбанить.")
    else:
        bot.reply_to(message, "У вас нет прав на выполнение этой команды.")

# Обработчик команды /add
@bot.message_handler(commands=['add'])
def handle_add(message):
    # Проверяем, является ли отправитель администратором беседы
    if is_administrator(message):
        # Проверяем, есть ли у сообщения упоминание пользователя, которого нужно вернуть в беседу
        if message.reply_to_message:
            user_id = message.reply_to_message.from_user.id
            bot.unban_chat_member(message.chat.id, user_id)
            bot.reply_to(message, f"Пользователь {user_id} был возвращен в беседу.")
        else:
            bot.reply_to(message,
                         "Пожалуйста, ответьте на сообщение пользователя, которого вы хотите вернуть в беседу.")
    else:
        bot.reply_to(message, "У вас нет прав на выполнение этой команды.")

# Функция для сохранения титула пользователя в базе данных
def save_user_title(user_id, title, chat_id):
    cursor.execute(f"IF NOT EXISTS (SELECT * FROM UserTitles WHERE UserID = ? AND ChatID = ?) INSERT INTO UserTitles (UserID, Title, ChatID) VALUES (?, ?, ?) ELSE UPDATE UserTitles SET Title = ? WHERE UserID = ? AND ChatID = ?", user_id, chat_id, user_id, title, chat_id, title, user_id, chat_id)

    connection.commit()

# Функция для извлечения титула пользователя из базы данных
def get_user_title(user_id, chat_id):
    cursor.execute("SELECT Title FROM UserTitles WHERE UserID = ? AND ChatID = ?", user_id, chat_id)
    row = cursor.fetchone()
    return row[0] if row else None

# Обработчик команды /set_title
@bot.message_handler(commands=['set_title'])
def handle_set_title(message):
    if is_administrator(message):
        if message.reply_to_message:
            text_parts = message.text.split(maxsplit=1)
            if len(text_parts) > 1:
                user_id = message.reply_to_message.from_user.id
                chat_id = message.chat.id
                title = text_parts[1]
                # Сохраняем титул пользователя в базе данных
                save_user_title(user_id, title, chat_id)
                bot.reply_to(message, f"Титул '{title}' установлен для пользователя с ID {user_id}.")
            else:
                bot.reply_to(message, "Пожалуйста, укажите титул.")
        else:
            bot.reply_to(message, "Пожалуйста, ответьте на сообщение пользователя, которому хотите установить титул.")
    else:
        bot.reply_to(message, "У вас нет прав на выполнение этой команды.")

# Функция для удаления титула пользователя из базы данных
def remove_user_title(user_id, chat_id):
    cursor.execute("DELETE FROM UserTitles WHERE UserID = ? AND ChatID = ?", user_id, chat_id)
    connection.commit()

# Обработчик команды /remove_title
@bot.message_handler(commands=['remove_title'])
def handle_remove_title(message):
    if is_administrator(message):
        if message.reply_to_message:
            user_id = message.reply_to_message.from_user.id
            chat_id = message.chat.id
            if get_user_title(user_id, chat_id):
                # Удаляем титул пользователя из базы данных
                remove_user_title(user_id, chat_id)
                bot.reply_to(message, f"Титул пользователя с ID {user_id} удален.")
            else:
                bot.reply_to(message, "У пользователя нет титула.")
        else:
            bot.reply_to(message, "Пожалуйста, ответьте на сообщение пользователя.")
    else:
        bot.reply_to(message, "У вас нет прав на выполнение этой команды.")

# Обработчик команды /get_title
@bot.message_handler(commands=['get_title'])
def handle_get_title(message):
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        chat_id = message.chat.id
        title = get_user_title(user_id, chat_id)
        if title:
            bot.reply_to(message, f"Титул пользователя с ID {user_id}: '{title}'.")
        else:
            bot.reply_to(message, "У пользователя нет титула.")
    else:
        bot.reply_to(message, "Пожалуйста, ответьте на сообщение пользователя.")

connection = pyodbc.connect('ваша строка подключения')

# Создание курсора для выполнения SQL-запросов
cursor = connection.cursor()
# Функция для сохранения данных о коинах пользователя в базе данных
def save_coins(user_id, coins):
    cursor.execute("IF NOT EXISTS (SELECT * FROM UserCoins WHERE UserID = ?) INSERT INTO UserCoins (UserID, Coins) VALUES (?, ?) ELSE UPDATE UserCoins SET Coins = ? WHERE UserID = ?", user_id, user_id, coins, coins, user_id)
    connection.commit()

# Функция для извлечения данных о коинах пользователя из базы данных
def get_coins(user_id):
    cursor.execute("SELECT Coins FROM UserCoins WHERE UserID = ?", user_id)
    row = cursor.fetchone()
    return row[0] if row else None

# Функция для добавления коинов в кошелек пользователя
def add_coins(user_id, amount):
    current_coins = get_coins(user_id)
    if current_coins is not None:
        new_coins = current_coins + amount
        save_coins(user_id, new_coins)
    else:
        save_coins(user_id, amount)

last_mining_time = {}

# Функция для получения текущего баланса коинов пользователя
def get_wallet_balance(user_id):
    return get_coins(user_id)

# Функция для сохранения времени майнинга пользователя в базе данных
def save_last_mining_time(user_id, mining_time):
    cursor.execute("IF NOT EXISTS (SELECT * FROM MiningTime WHERE UserID = ?) INSERT INTO MiningTime (UserID, LastMiningTime) VALUES (?, ?) ELSE UPDATE MiningTime SET LastMiningTime = ? WHERE UserID = ?", user_id, user_id, mining_time, mining_time, user_id)
    connection.commit()

# Функция для извлечения времени майнинга пользователя из базы данных
def get_last_mining_time(user_id):
    cursor.execute("SELECT LastMiningTime FROM MiningTime WHERE UserID = ?", user_id)
    row = cursor.fetchone()
    return row[0] if row else None

# Обработчик команды /mine
@bot.message_handler(commands=['mine'])
def handle_mine(message):
    user_id = message.from_user.id
    current_time = datetime.datetime.now() # Получаем текущее время
    last_mining = get_last_mining_time(user_id)  # Получаем время последнего майнинга пользователя

    if last_mining is None or (current_time - last_mining).total_seconds() >= 3 * 3600:
        mined_coins = random.randint(5, 100)
        add_coins(user_id, mined_coins)
        save_last_mining_time(user_id, current_time)  # Сохраняем текущее время майнинга
        bot.reply_to(message, f"Вы успешно добыли {mined_coins} ZeroCoins!")
    else:
        bot.reply_to(message, "Вы уже добывали коины недавно. Попробуйте снова через некоторое время.")

# Обработчик команды /wallet
@bot.message_handler(commands=['wallet'])
def handle_wallet(message):
    user_id = message.from_user.id
    balance = get_wallet_balance(user_id)
    if balance is not None:
        bot.reply_to(message, f"Ваш текущий баланс: {balance} ZeroCoins")
    else:
        bot.reply_to(message, "У вас еще нет коинов. Начните добывать, используя команду /mine.")



# Функция для проверки, является ли отправитель администратором беседы
def is_administrator(message):
    # Получаем список администраторов беседы
    chat_admins = bot.get_chat_administrators(message.chat.id)
    # Получаем ID отправителя сообщения
    sender_id = message.from_user.id
    # Проверяем, является ли отправитель одним из администраторов
    for admin in chat_admins:
        if admin.user.id == sender_id:
            return True
    return False


# Запускаем бота
bot.polling()