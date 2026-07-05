import sqlite3
from datetime import datetime

DB_NAME = "bot.db"

def connect():
    """اتصال به دیتابیس"""
    return sqlite3.connect(DB_NAME)

def get_db():
    """همون connect - برای سازگاری"""
    return connect()

def init_db():
    """ساخت جداول دیتابیس"""
    db = get_db()
    c = db.cursor()
    
    # جدول کاربران
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            username TEXT,
            full_name TEXT,
            joined_at TEXT
        )
    ''')
    
    # جدول ادمین‌ها
    c.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE
        )
    ''')
    
    # جدول منوها
    c.execute('''
        CREATE TABLE IF NOT EXISTS menus (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            callback_key TEXT UNIQUE,
            parent_id INTEGER DEFAULT NULL,
            is_paid INTEGER DEFAULT 0,
            price INTEGER DEFAULT 0
        )
    ''')
    
    # جدول فایل‌های محتوا
    c.execute('''
        CREATE TABLE IF NOT EXISTS content_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            menu_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            message_id INTEGER NOT NULL,
            caption TEXT,
            created_at TEXT
        )
    ''')
    
    # جدول پرداخت‌ها
    c.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            menu_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )
    ''')
    
    db.commit()
    db.close()
    print("✅ دیتابیس ساخته شد.")

# ===== کاربران =====
def add_user(user_id, username, full_name):
    db = get_db()
    c = db.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, full_name, joined_at) VALUES (?,?,?,?)",
              (user_id, username, full_name, datetime.now().isoformat()))
    db.commit()
    db.close()

# ===== ادمین‌ها =====
def is_admin(user_id):
    db = get_db()
    c = db.cursor()
    c.execute("SELECT 1 FROM admins WHERE user_id=?", (user_id,))
    result = c.fetchone()
    db.close()
    return result is not None

def add_admin(user_id):
    db = get_db()
    c = db.cursor()
    c.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (user_id,))
    db.commit()
    db.close()
    print(f"✅ ادمین {user_id} اضافه شد.")

def get_all_admins():
    """دریافت لیست همه ادمین‌ها"""
    db = get_db()
    c = db.cursor()
    c.execute("SELECT user_id FROM admins")
    result = c.fetchall()
    db.close()
    return result

# ===== منوها =====
def add_menu(title, callback_key, parent_id=None):
    db = get_db()
    c = db.cursor()
    c.execute("INSERT INTO menus (title, callback_key, parent_id) VALUES (?,?,?)",
              (title, callback_key, parent_id))
    db.commit()
    db.close()

def get_menu(callback_key):
    db = get_db()
    c = db.cursor()
    c.execute("SELECT id, title, is_paid, price FROM menus WHERE callback_key=?", (callback_key,))
    result = c.fetchone()
    db.close()
    return result

def get_root_menus():
    db = get_db()
    c = db.cursor()
    c.execute("SELECT title, callback_key FROM menus WHERE parent_id IS NULL")
    result = c.fetchall()
    db.close()
    return result

def get_children(parent_id):
    db = get_db()
    c = db.cursor()
    c.execute("SELECT title, callback_key FROM menus WHERE parent_id=?", (parent_id,))
    result = c.fetchall()
    db.close()
    return result

def get_all_menus():
    """دریافت همه منوها (برای نمایش در لیست حذف)"""
    db = get_db()
    c = db.cursor()
    c.execute("SELECT title, callback_key FROM menus ORDER BY parent_id IS NULL DESC, id")
    result = c.fetchall()
    db.close()
    return result

def delete_menu(callback_key):
    db = get_db()
    c = db.cursor()
    # گرفتن id منو
    c.execute("SELECT id FROM menus WHERE callback_key=?", (callback_key,))
    row = c.fetchone()
    if row:
        menu_id = row[0]
        # حذف فایل‌های متصل
        c.execute("DELETE FROM content_files WHERE menu_id=?", (menu_id,))
        # حذف زیرمنوها (همه سطوح)
        c.execute("DELETE FROM menus WHERE parent_id=?", (menu_id,))
        # حذف خود منو
        c.execute("DELETE FROM menus WHERE id=?", (menu_id,))
        print(f"✅ منو {callback_key} حذف شد.")
    db.commit()
    db.close()

def set_price(menu_id, price):
    db = get_db()
    c = db.cursor()
    if price == 0:
        c.execute("UPDATE menus SET is_paid=0, price=0 WHERE id=?", (menu_id,))
    else:
        c.execute("UPDATE menus SET is_paid=1, price=? WHERE id=?", (price, menu_id))
    db.commit()
    db.close()

# ===== فایل‌های محتوا =====
def add_content(menu_id, channel_id, message_id, caption=""):
    db = get_db()
    c = db.cursor()
    c.execute("INSERT INTO content_files (menu_id, channel_id, message_id, caption, created_at) VALUES (?,?,?,?,?)",
              (menu_id, channel_id, message_id, caption, datetime.now().isoformat()))
    db.commit()
    db.close()

def get_content(menu_id):
    db = get_db()
    c = db.cursor()
    c.execute("SELECT channel_id, message_id FROM content_files WHERE menu_id=? LIMIT 1", (menu_id,))
    result = c.fetchone()
    db.close()
    return result

# ===== پرداخت‌ها =====
def add_payment(user_id, menu_id, amount):
    db = get_db()
    c = db.cursor()
    c.execute("INSERT INTO payments (user_id, menu_id, amount, status, created_at) VALUES (?,?,?,?,?)",
              (user_id, menu_id, amount, 'pending', datetime.now().isoformat()))
    db.commit()
    db.close()

def set_payment_success(user_id, menu_id):
    db = get_db()
    c = db.cursor()
    c.execute("UPDATE payments SET status='paid' WHERE user_id=? AND menu_id=?", (user_id, menu_id))
    db.commit()
    db.close()

def is_paid(user_id, menu_id):
    db = get_db()
    c = db.cursor()
    c.execute("SELECT 1 FROM payments WHERE user_id=? AND menu_id=? AND status='paid'", (user_id, menu_id))
    result = c.fetchone()
    db.close()
    return result is not None