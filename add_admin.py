import sqlite3
from database import init_db, add_admin, is_admin

# اول مطمئن بشیم دیتابیس ساخته شده
print("📦 مرحله 1: ساخت دیتابیس...")
init_db()
print("✅ دیتابیس ساخته شد.")

# حالا ادمین رو اضافه کن
USER_ID = 7494085511  # آیدی خودت
print(f"📦 مرحله 2: اضافه کردن ادمین {USER_ID}...")
add_admin(USER_ID)
print("✅ ادمین اضافه شد!")

# چک کن ببین واقعاً اضافه شده یا نه
print("📦 مرحله 3: چک کردن ادمین...")
if is_admin(USER_ID):
    print("✅ تأیید شد! تو ادمین هستی.")
else:
    print("❌ مشکلی وجود داره، ادمین نشدی!")

# لیست همه ادمین‌ها رو نشون بده
print("\n📋 لیست همه ادمین‌ها:")
conn = sqlite3.connect("bot.db")
c = conn.cursor()
c.execute("SELECT user_id FROM admins")
admins = c.fetchall()
for admin in admins:
    print(f"- {admin[0]}")
conn.close()