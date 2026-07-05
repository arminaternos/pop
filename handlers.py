from telegram import Update
from telegram.ext import ContextTypes

from keyboards import create_menu
from menus import MENU
from config import CHANNEL_ID, TEST_FILE_ID
from database import connect


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        MENU["main"]["title"],
        reply_markup=create_menu("main")
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    # اگر callback مربوط به یک منو باشد
    if data in MENU:
        await query.edit_message_text(
            MENU[data]["title"],
            reply_markup=create_menu(data)
        )
        return

    if data == "hf":
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT message_id FROM files
        WHERE subcategory_id = ?
        LIMIT 1
    """, (1,))  # فعلاً تستی

    row = cur.fetchone()
    conn.close()

    if row:
        await context.bot.copy_message(
            chat_id=query.message.chat.id,
            from_chat_id=CHANNEL_ID,
            message_id=row[0]
        )
    else:
        await query.answer("فایل پیدا نشد", show_alert=True)
        return

    await query.answer()
    return

    # دکمه بازگشت
    if data == "back":
        await query.edit_message_text(
            MENU["main"]["title"],
            reply_markup=create_menu("main")
        )
        return

    # بقیه دکمه‌ها
    await query.answer(
        "🚧 این بخش هنوز تکمیل نشده.",
        show_alert=True
    )


async def channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    post = update.channel_post

    print("CHANNEL ID:", post.chat.id)
    print("MESSAGE ID:", post.message_id)