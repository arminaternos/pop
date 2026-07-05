import sqlite3
from datetime import datetime

DB_NAME = "bot.db"


def connect():
    return sqlite3.connect(DB_NAME)


def init_db():
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        username TEXT,
        full_name TEXT,
        joined_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS menus (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        callback_key TEXT UNIQUE,
        parent_id INTEGER,
        is_paid INTEGER DEFAULT 0,
        price INTEGER DEFAULT 0
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS content_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        menu_id INTEGER NOT NULL,
        channel_id INTEGER NOT NULL,
        message_id INTEGER NOT NULL,
        caption TEXT,
        created_at TEXT,
        is_active INTEGER DEFAULT 1
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        menu_id INTEGER NOT NULL,
        amount INTEGER NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at TEXT
    )
    """)

    conn.commit()
    conn.close()


def add_user(user_id, username, full_name):
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
    INSERT OR IGNORE INTO users (user_id, username, full_name, joined_at)
    VALUES (?, ?, ?, ?)
    """, (user_id, username, full_name, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def is_admin(user_id):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM admins WHERE user_id=?", (user_id,))
    res = cur.fetchone()
    conn.close()
    return res is not None


def add_admin(user_id):
    conn = connect()
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()


def add_menu(title, callback_key, parent_id=None, is_paid=0, price=0):
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO menus (title, callback_key, parent_id, is_paid, price)
    VALUES (?, ?, ?, ?, ?)
    """, (title, callback_key, parent_id, is_paid, price))
    conn.commit()
    conn.close()


def get_menu(callback_key):
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
    SELECT id, title, is_paid, price
    FROM menus
    WHERE callback_key=?
    """, (callback_key,))
    row = cur.fetchone()
    conn.close()
    return row


def get_children(parent_id):
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
    SELECT title, callback_key
    FROM menus
    WHERE parent_id=?
    """, (parent_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_root_menus():
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
    SELECT title, callback_key
    FROM menus
    WHERE parent_id IS NULL
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


def get_all_menus():
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT title, callback_key FROM menus")
    rows = cur.fetchall()
    conn.close()
    return rows


def delete_menu(callback_key):
    conn = connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM menus WHERE callback_key=?", (callback_key,))
    conn.commit()
    conn.close()


def set_menu_price(menu_id, price):
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
    UPDATE menus
    SET is_paid=1, price=?
    WHERE id=?
    """, (price, menu_id))
    conn.commit()
    conn.close()


def add_content(menu_id, channel_id, message_id, caption=""):
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO content_files (menu_id, channel_id, message_id, caption, created_at)
    VALUES (?, ?, ?, ?, ?)
    """, (menu_id, channel_id, message_id, caption, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_content(menu_id):
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
    SELECT channel_id, message_id
    FROM content_files
    WHERE menu_id=?
    LIMIT 1
    """, (menu_id,))
    row = cur.fetchone()
    conn.close()
    return row


def add_payment(user_id, menu_id, amount):
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO payments (user_id, menu_id, amount, status, created_at)
    VALUES (?, ?, ?, 'pending', ?)
    """, (user_id, menu_id, amount, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def set_payment_success(user_id, menu_id):
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
    UPDATE payments
    SET status='paid'
    WHERE user_id=? AND menu_id=?
    """, (user_id, menu_id))
    conn.commit()
    conn.close()


def is_paid(user_id, menu_id):
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
    SELECT 1 FROM payments
    WHERE user_id=? AND menu_id=? AND status='paid'
    """, (user_id, menu_id))
    res = cur.fetchone()
    conn.close()
    return res is not None