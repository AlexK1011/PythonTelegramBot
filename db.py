import sqlite3



DB_PATH = "channels.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Существующая таблица каналов
    c.execute('''
              CREATE TABLE IF NOT EXISTS channels
              (
                  id       INTEGER,
                  user_id  INTEGER,
                  title    TEXT,
                  username TEXT,
                  added_at TEXT DEFAULT CURRENT_TIMESTAMP,
                  PRIMARY KEY (id, user_id)
              )
              ''')

    # Новая таблица для отслеживания последних постов
    c.execute('''
              CREATE TABLE IF NOT EXISTS last_posts
              (
                  channel_id      INTEGER PRIMARY KEY,
                  last_message_id INTEGER,
                  last_check_time TEXT DEFAULT CURRENT_TIMESTAMP
              )
              ''')

    conn.commit()
    conn.close()


def add_channel(user_id, channel_id, title, username):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT OR IGNORE INTO channels (id, user_id, title, username) VALUES (?, ?, ?, ?)",
        (channel_id, user_id, title, username)
    )

    # Создаем запись в last_posts (если её еще нет)
    c.execute('''
              INSERT OR IGNORE INTO last_posts (channel_id, last_message_id, last_check_time)
              VALUES (?, NULL, CURRENT_TIMESTAMP)
              ''', (channel_id,))

    conn.commit()
    conn.close()

def get_channels(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT id, title FROM channels WHERE user_id = ? ORDER BY added_at ASC;",
        (user_id,)
    )
    channels = c.fetchall()
    conn.close()
    return channels

def channel_exists(user_id, channel_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT 1 FROM channels WHERE user_id = ? AND id = ?",
        (user_id, channel_id)
    )
    exists = c.fetchone() is not None
    conn.close()
    return exists

def clear_channels(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM channels WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def delete_channel(user_id, channel_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "DELETE FROM channels WHERE user_id = ? AND id = ?",
        (user_id, channel_id)
    )
    # Также удаляем запись о последнем посте, если больше нет пользователей для этого канала
    c.execute('''
        DELETE FROM last_posts 
        WHERE channel_id = ? 
        AND NOT EXISTS (
            SELECT 1 FROM channels WHERE id = ?
        )
    ''', (channel_id, channel_id))
    conn.commit()
    conn.close()




def get_unique_channels():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT DISTINCT id, title, username FROM channels ORDER BY id")
    channels = c.fetchall()
    conn.close()
    return channels

def get_users_for_channel(channel_id):
    """Получить всех пользователей, которые подписаны на конкретный канал"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id FROM channels WHERE id = ?", (channel_id,))
    users = [row[0] for row in c.fetchall()]
    conn.close()
    return users

def get_last_post_id(channel_id):
    """Получить ID последнего обработанного поста для канала"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT last_message_id FROM last_posts WHERE channel_id = ?",
        (channel_id,)
    )
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def set_last_post_id(channel_id, message_id):
    """Сохранить ID последнего обработанного поста для канала"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO last_posts (channel_id, last_message_id, last_check_time)
        VALUES (?, ?, CURRENT_TIMESTAMP)
    ''', (channel_id, message_id))
    conn.commit()
    conn.close()

