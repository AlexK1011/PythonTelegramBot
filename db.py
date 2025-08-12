import sqlite3
from contextlib import closing

DB_PATH = "channels.db"


def get_connection():
    """Создает соединение с включенными внешними ключами"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with closing(get_connection()) as conn:
        c = conn.cursor()

        c.execute('''
                  CREATE TABLE IF NOT EXISTS users
                  (
                      id INTEGER PRIMARY KEY
                  )
                  ''')

        c.execute('''
                  CREATE TABLE IF NOT EXISTS channels
                  (
                      id       INTEGER PRIMARY KEY,
                      username TEXT NOT NULL UNIQUE,
                      title    TEXT NOT NULL
                  )
                  ''')

        c.execute('''
                  CREATE TABLE IF NOT EXISTS subscriptions
                  (
                      user_id    INTEGER,
                      channel_id INTEGER,
                      added_at   TEXT DEFAULT CURRENT_TIMESTAMP,
                      PRIMARY KEY (user_id, channel_id),
                      FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                      FOREIGN KEY (channel_id) REFERENCES channels (id) ON DELETE CASCADE
                  )
                  ''')

        c.execute('''
                  CREATE TABLE IF NOT EXISTS last_posts
                  (
                      channel_id      INTEGER PRIMARY KEY,
                      last_message_id INTEGER,
                      last_check_time TEXT DEFAULT CURRENT_TIMESTAMP,
                      FOREIGN KEY (channel_id) REFERENCES channels (id) ON DELETE CASCADE
                  )
                  ''')

        c.execute('''
                  CREATE TABLE IF NOT EXISTS settings
                  (
                      user_id INTEGER,
                      setting TEXT,
                      value   TEXT,
                      PRIMARY KEY (user_id, setting),
                      FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                  )
                  ''')

        conn.commit()


def ensure_user_exists(conn, user_id):
    """Гарантирует, что пользователь существует в базе"""
    conn.execute(
        "INSERT OR IGNORE INTO users (id) VALUES (?)",
        (user_id,)
    )


def add_channel(user_id, channel_id, title, username):
    with closing(get_connection()) as conn:
        ensure_user_exists(conn, user_id)
        c = conn.cursor()

        c.execute(
            "INSERT OR IGNORE INTO channels (id, username, title) VALUES (?, ?, ?)",
            (channel_id, username, title)
        )

        c.execute(
            """INSERT OR IGNORE INTO subscriptions
                   (user_id, channel_id)
               VALUES (?, ?)""",
            (user_id, channel_id)
        )

        c.execute(
            """INSERT OR IGNORE INTO last_posts
                   (channel_id, last_message_id)
               VALUES (?, NULL)""",
            (channel_id,)
        )

        conn.commit()


def get_channels(user_id):
    with closing(get_connection()) as conn:
        c = conn.cursor()
        c.execute(
            """SELECT channels.id, channels.username, channels.title
               FROM subscriptions
                        JOIN channels ON subscriptions.channel_id = channels.id
               WHERE subscriptions.user_id = ?
               ORDER BY subscriptions.added_at""",
            (user_id,)
        )
        return c.fetchall()


def channel_exists(user_id, channel_id):
    with closing(get_connection()) as conn:
        c = conn.cursor()
        c.execute(
            """SELECT 1
               FROM subscriptions
               WHERE user_id = ?
                 AND channel_id = ?""",
            (user_id, channel_id)
        )
        exists = c.fetchone() is not None
        return exists


def delete_channel(user_id, channel_id):
    with closing(get_connection()) as conn:
        c = conn.cursor()

        c.execute(
            """DELETE
               FROM subscriptions
               WHERE user_id = ?
                 AND channel_id = ?""",
            (user_id, channel_id)
        )

        c.execute('''
                  DELETE
                  FROM channels
                  WHERE id = ?
                    AND NOT EXISTS (SELECT 1
                                    FROM subscriptions
                                    WHERE channel_id = ?)
                  ''', (channel_id, channel_id))

        c.execute('''
                  DELETE
                  FROM last_posts
                  WHERE channel_id = ?
                    AND NOT EXISTS (SELECT 1
                                    FROM channels
                                    WHERE id = ?)
                  ''', (channel_id, channel_id))

        conn.commit()


def get_unique_channels():
    with closing(get_connection()) as conn:
        c = conn.cursor()
        c.execute(
            "SELECT DISTINCT id, title, username FROM channels ORDER BY id"
        )

        return c.fetchall()


def get_users_for_channel(channel_id):
    with closing(get_connection()) as conn:
        c = conn.cursor()
        c.execute(
            "SELECT user_id FROM subscriptions WHERE channel_id = ?",
            (channel_id,)
        )
        users = [row[0] for row in c.fetchall()]
        return users


def get_last_post_id(channel_id):
    with closing(get_connection()) as conn:
        c = conn.cursor()
        c.execute(
            "SELECT last_message_id FROM last_posts WHERE channel_id = ?",
            (channel_id,)
        )
        result = c.fetchone()
        conn.close()
        return result[0] if result else None


def set_last_post_id(channel_id, message_id):
    with closing(get_connection()) as conn:
        c = conn.cursor()
        c.execute(
            '''INSERT OR
               REPLACE INTO last_posts
                   (channel_id, last_message_id, last_check_time)
               VALUES (?, ?, CURRENT_TIMESTAMP)''',
            (channel_id, message_id)
        )
        conn.commit()


def set_settings(user_id, setting, value):
    with closing(get_connection()) as conn:
        c = conn.cursor()

        ensure_user_exists(conn, user_id)

        c.execute(
            '''INSERT OR
               REPLACE INTO settings (user_id, setting, value)
               VALUES (?, ?, ?)''',
            (user_id, setting, str(value))
        )
        conn.commit()


def get_settings(user_id):
    default_settings = {
        'delay': 3600,
        'min_forward_rate': 1.0,
        'ai_enabled': 0,
        'system_prompt': ""
    }

    with closing(get_connection()) as conn:
        c = conn.cursor()

        c.execute(
            "SELECT setting, value FROM settings WHERE user_id = ?",
            (user_id,)
        )
        settings_data = c.fetchall()

    result = {}
    for setting, value in settings_data:
        if setting == 'delay':
            result[setting] = int(value) if value.isdigit() else default_settings[setting]
        elif setting == 'min_forward_rate':
            try:
                result[setting] = float(value)
            except ValueError:
                result[setting] = default_settings[setting]
        elif setting == 'ai_enabled':
            result[setting] = 1 if value == '1' else 0
        else:
            result[setting] = value

    for key, default_value in default_settings.items():
        if key not in result:
            result[key] = default_value

    return result
