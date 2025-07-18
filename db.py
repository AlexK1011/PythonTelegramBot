import sqlite3



DB_PATH = "channels.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY,
            title TEXT,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def add_channel(channel_id, title):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO channels (id, title) VALUES (?, ?)", (channel_id, title))
    conn.commit()
    conn.close()

def get_channels():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, title FROM channels ORDER BY added_at ASC;")
    channels = c.fetchall()
    conn.close()
    return channels

def channel_exists(channel_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT 1 FROM channels WHERE id = ?", (channel_id,))
    exists = c.fetchone() is not None
    conn.close()
    return exists

def clear_channels():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM channels")
    conn.commit()
    conn.close()

def delete_channel(channel_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM channels WHERE id = ?", (channel_id,))
    conn.commit()
    conn.close()