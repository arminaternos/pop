from database import init_db, add_admin, is_admin

init_db()
USER_ID = 7494085511
add_admin(USER_ID)

if is_admin(USER_ID):
    print(f"✅ ادمین {USER_ID} شدی!")
else:
    print("❌ خطا!")