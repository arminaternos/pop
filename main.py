from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from config import BOT_TOKEN
import database

from handlers import start, button_handler, channel_post


def main():

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(
    MessageHandler(filters.UpdateType.CHANNEL_POST, channel_post))

    # دریافت پیام‌های کانال
   

    print("🤖 Bot Started...")
from database import connect

conn = connect()
cur = conn.cursor()

cur.execute("""
INSERT INTO files (subcategory_id, message_id, caption)
VALUES (?, ?, ?)
""", (1, 3, "test file"))

conn.commit()
conn.close()
    app.run_polling()


if __name__ == "__main__":
    main()