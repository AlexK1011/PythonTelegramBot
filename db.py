import sqlite3



DB_PATH = "channels.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER,
            user_id INTEGER,
            title TEXT,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id, user_id)
        )
    ''')
    conn.commit()
    conn.close()

def add_channel(user_id, channel_id, title):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT OR IGNORE INTO channels (id, user_id, title) VALUES (?, ?, ?)",
        (channel_id, user_id, title)
    )
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
    conn.commit()
    conn.close()