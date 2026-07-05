import sqlite3
from datetime import datetime

DB_NAME = "bot.db"

def get_db():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    # users
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        username TEXT,
        full_name TEXT,
        joined_at TEXT
    )''')
    
    # admins
    c.execute('''CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE
    )''')
    
    # menus
    c.execute('''CREATE TABLE IF NOT EXISTS menus (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        callback_key TEXT UNIQUE,
        parent_id INTEGER,
        is_paid INTEGER DEFAULT 0,
        price INTEGER DEFAULT 0
    )''')
    
    # content_files
    c.execute('''CREATE TABLE IF NOT EXISTS content_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        menu_id INTEGER NOT NULL,
        channel_id INTEGER NOT NULL,
        message_id INTEGER NOT NULL,
        caption TEXT,
        created_at TEXT
    )''')
    
    # payments
    c.execute('''CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        menu_id INTEGER NOT NULL,
        amount INTEGER NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at TEXT
    )''')
    
    conn.commit()
    conn.close()

# ========== USERS ==========
def add_user(user_id, username, full_name):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, full_name, joined_at) VALUES (?,?,?,?)",
              (user_id, username, full_name, datetime.now().isoformat()))
    conn.commit()
    conn.close()

# ========== ADMINS ==========
def is_admin(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT 1 FROM admins WHERE user_id=?", (user_id,))
    res = c.fetchone()
    conn.close()
    return res is not None

def add_admin(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

# ========== MENUS ==========
def add_menu(title, callback_key, parent_id=None, is_paid=0, price=0):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO menus (title, callback_key, parent_id, is_paid, price) VALUES (?,?,?,?,?)",
              (title, callback_key, parent_id, is_paid, price))
    conn.commit()
    conn.close()

def get_menu(callback_key):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, title, is_paid, price FROM menus WHERE callback_key=?", (callback_key,))
    row = c.fetchone()
    conn.close()
    return row

def get_children(parent_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT title, callback_key FROM menus WHERE parent_id=?", (parent_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_root_menus():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT title, callback_key FROM menus WHERE parent_id IS NULL")
    rows = c.fetchall()
    conn.close()
    return rows

def delete_menu_by_callback(callback_key):
    """حذف منو و همه زیرمنوها و فایل‌های مرتبط"""
    conn = get_db()
    c = conn.cursor()
    # پیدا کردن ID منو
    c.execute("SELECT id FROM menus WHERE callback_key=?", (callback_key,))
    row = c.fetchone()
    if row:
        menu_id = row[0]
        # حذف زیرمنوها
        c.execute("DELETE FROM menus WHERE parent_id=?", (menu_id,))
        # حذف خود منو
        c.execute("DELETE FROM menus WHERE id=?", (menu_id,))
        # حذف فایل‌های متصل
        c.execute("DELETE FROM content_files WHERE menu_id=?", (menu_id,))
    conn.commit()
    conn.close()

def set_price(menu_id, price):
    conn = get_db()
    c = conn.cursor()
    if price == 0:
        c.execute("UPDATE menus SET is_paid=0, price=0 WHERE id=?", (menu_id,))
    else:
        c.execute("UPDATE menus SET is_paid=1, price=? WHERE id=?", (price, menu_id))
    conn.commit()
    conn.close()

# ========== CONTENT ==========
def add_content(menu_id, channel_id, message_id, caption=""):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO content_files (menu_id, channel_id, message_id, caption, created_at) VALUES (?,?,?,?,?)",
              (menu_id, channel_id, message_id, caption, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_content(menu_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT channel_id, message_id FROM content_files WHERE menu_id=? LIMIT 1", (menu_id,))
    row = c.fetchone()
    conn.close()
    return row

# ========== PAYMENTS ==========
def add_payment(user_id, menu_id, amount):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO payments (user_id, menu_id, amount, status, created_at) VALUES (?,?,?,?,?)",
              (user_id, menu_id, amount, 'pending', datetime.now().isoformat()))
    conn.commit()
    conn.close()

def set_payment_success(user_id, menu_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE payments SET status='paid' WHERE user_id=? AND menu_id=?", (user_id, menu_id))
    conn.commit()
    conn.close()

def is_paid(user_id, menu_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT 1 FROM payments WHERE user_id=? AND menu_id=? AND status='paid'", (user_id, menu_id))
    res = c.fetchone()
    conn.close()
    return res is not None