import sqlite3


conn = sqlite3.connect("bot.db")
cursor = conn.cursor()


cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT
)
""")


conn.commit()
conn.close()