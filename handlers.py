import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import ContextTypes
from config import DELETE_TIME
from database import *

logger = logging.getLogger(__name__)
async def delete_message_job(context):
    job = context.job

    try:
        await context.bot.delete_message(
            chat_id=job.data["chat_id"],
            message_id=job.data["message_id"]
        )
    except Exception:
        pass
def extract_ids_from_link(link):
    """استخراج channel_id و message_id از لینک تلگرام"""
    pattern = r'https?://t\.me/c/(\d+)/(\d+)'
    match = re.search(pattern, link)
    if not match:
        return None, None
        
    internal_id = match.group(1)
        
    message_id = int(match.group(2))
    
    channel_id = int(f"-100{internal_id}")
    
    return channel_id, message_id

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id, user.username, user.full_name)
    
    menus = get_root_menus()
    if not menus:
        await update.message.reply_text("⛔ منویی وجود ندارد. از /admin استفاده کن.")
        return
    
    keyboard = [[InlineKeyboardButton(title, callback_data=cb)] for title, cb in menus]
    await update.message.reply_text("📌 منوی اصلی", reply_markup=InlineKeyboardMarkup(keyboard))

async def main_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    
    print(f"🔘 دکمه: {data}")
    
    if data.startswith(("admin_", "parent_", "del_", "file_")):
        if not is_admin(user_id):
            await query.message.reply_text("⛔ دسترسی ندارید.")
            return
        await admin_handler(query, context, data)
        return
    
    if data == "back":
        menus = get_root_menus()
        if not menus:
            await query.edit_message_text("⛔ منویی وجود ندارد.")
            return
        keyboard = [[InlineKeyboardButton(title, callback_data=cb)] for title, cb in menus]
        await query.edit_message_text("📌 منوی اصلی", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    menu = get_menu(data)
    if not menu:
        await query.answer("نامعتبر", show_alert=True)
        return
    
    menu_id, title, paid_flag, parent_id, price = menu
    children = get_children(menu_id)
    
    if children:
        keyboard = [[InlineKeyboardButton(t, callback_data=c)] for t, c in children]
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back")])
        await query.edit_message_text(title, reply_markup=InlineKeyboardMarkup(keyboard))
        return
        
    if paid_flag and not is_paid(user_id, menu_id):
        await query.message.reply_text(f"💳 قیمت: {price} Stars")
        await context.bot.send_invoice(
            chat_id=user_id,
            title="خرید محتوا",
            description="دسترسی به محتوای انتخابی",
            payload=f"menu_{menu_id}_{user_id}",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice("Access", price)]
        )
        return
        
    contents = get_content(menu_id)
    if not contents:
        await query.answer("محتوا یافت نشد", show_alert=True)
        return
    
    for channel_id, message_id in contents:
        try:
            sent = await context.bot.copy_message(
                chat_id=query.message.chat.id,
                from_chat_id=channel_id,
                message_id=message_id
            )
            context.job_queue.run_once(
                delete_message_job,
                DELETE_TIME,
                data={
                    "chat_id": sent.chat.id,
                    "message_id": sent.message_id
                }
            )
        except Exception as e:
            logger.exception(e)
        
    
    
  

async def admin_handler(query, context, data):
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        await query.message.reply_text("⛔ دسترسی ندارید.")
        return
    
    print(f"🔧 ادمین: {data}")
    
    if data == "admin_add_menu":
        context.user_data["step"] = "menu_title"
        await query.message.reply_text("✏️ اسم منو رو بفرست:")
        return
    
    if data == "admin_add_submenu":
        all_menus = get_all_menus()
        if not all_menus:
            await query.message.reply_text("❌ اول یه منوی اصلی بساز.")
            return
        
        keyboard = []
        for title, cb, parent_id in all_menus:
            if parent_id is None:
                icon = "📁"
            else:
                menu = get_menu(cb)
                if menu:
                    menu_id = menu[0]
                    children = get_children(menu_id)
                    icon = "📂" if children else "📄"
            keyboard.append([InlineKeyboardButton(f"{icon} {title}", callback_data=f"parent_{cb}")])
        
        await query.message.reply_text(
            "زیر کدوم منو باشه؟\n📁=اصلی 📂=زیرمنو 📄=نهایی",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    if data.startswith("parent_"):
        parent_cb = data[7:]
        context.user_data["parent_key"] = parent_cb
        context.user_data["step"] = "submenu_title"
        await query.message.reply_text("✏️ اسم زیرمنو رو بفرست:")
        return
    
    if data == "admin_add_file":
        db = get_db()
        c = db.cursor()
        c.execute("SELECT title, callback_key FROM menus WHERE parent_id IS NOT NULL")
        submenus = c.fetchall()
        db.close()
        
        if not submenus:
            await query.message.reply_text("❌ هیچ زیرمنویی وجود نداره. اول یه زیرمنو بساز.")
            return
        
        keyboard = [[InlineKeyboardButton(f"📄 {title}", callback_data=f"file_{cb}")] for title, cb in submenus]
        await query.message.reply_text(
            "فایل رو به کدوم زیرمنو وصل کنم؟",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    if data.startswith("file_"):
        cb = data[5:]
        context.user_data["file_menu_key"] = cb
        context.user_data["step"] = "file_wait_link"
        await query.message.reply_text(
            "📌 لینک پیام رو بفرست.\n\n"
            "روی پیام کلیک کن → Copy Message Link\n"
            "مثلاً: `https://t.me/c/123456789/123`",
            parse_mode="Markdown"
        )
        return
    
    if data == "admin_set_price":
        context.user_data["step"] = "set_price_menu"
        await query.message.reply_text("🔑 کد منو رو بفرست:")
        return
    
    if data == "admin_delete_menu":
        all_menus = get_all_menus()
        if not all_menus:
            await query.message.reply_text("📭 منویی وجود ندارد.")
            return
        
        keyboard = []
        for title, cb, parent_id in all_menus:
            if parent_id is None:
                icon = "📁"
            else:
                menu = get_menu(cb)
                if menu:
                    menu_id = menu[0]
                    children = get_children(menu_id)
                    icon = "📂" if children else "📄"
            keyboard.append([InlineKeyboardButton(f"{icon} {title}", callback_data=f"del_{cb}")])
        
        await query.message.reply_text("منو رو برای حذف انتخاب کن:", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    if data.startswith("del_"):
        cb = data[4:]
        delete_menu(cb)
        await query.message.reply_text(f"✅ منو حذف شد.")
        return

async def pre_checkout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)

async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user_id = msg.from_user.id
    payload = msg.successful_payment.invoice_payload
    parts = payload.split("_")
    if len(parts) == 3:
        menu_id = int(parts[1])
        set_payment_success(user_id, menu_id)
        await msg.reply_text("✅ پرداخت موفق!")
        
        contents = get_content(menu_id)
        if contents:
            
            for channel_id, message_id in contents:
                sent = await context.bot.copy_message(
                    chat_id=user_id,
                    from_chat_id=channel_id,
                    message_id=message_id
                )
                context.job_queue.run_once(
                    delete_message_job,
                    DELETE_TIME,
                    data={
                        "chat_id": sent.chat.id,
                        "message_id": sent.message_id
                    }
                )

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ دسترسی ندارید.")
        return
    
    keyboard = [
        [InlineKeyboardButton("➕ افزودن منو", callback_data="admin_add_menu")],
        [InlineKeyboardButton("➕ افزودن زیرمنو", callback_data="admin_add_submenu")],
        [InlineKeyboardButton("📁 افزودن فایل به زیرمنو", callback_data="admin_add_file")],
        [InlineKeyboardButton("💰 تنظیم قیمت", callback_data="admin_set_price")],
        [InlineKeyboardButton("🗑 حذف منو", callback_data="admin_delete_menu")],
    ]
    await update.message.reply_text("🛠 پنل ادمین", reply_markup=InlineKeyboardMarkup(keyboard))

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return
    
    step = context.user_data.get("step")
    text = update.message.text.strip()
    
    print(f"📝 مرحله: {step} | متن: {text}")
    
    if step == "menu_title":
        context.user_data["menu_title"] = text
        context.user_data["step"] = "menu_callback"
        await update.message.reply_text("🔑 callback_key رو بفرست:")
        return
    
    if step == "menu_callback":
        title = context.user_data.get("menu_title")
        add_menu(title, text)
        context.user_data.clear()
        await update.message.reply_text("✅ منو ساخته شد.")
        return
    
    if step == "submenu_title":
        context.user_data["submenu_title"] = text
        context.user_data["step"] = "submenu_callback"
        await update.message.reply_text("🔑 callback_key رو بفرست:")
        return
    
    if step == "submenu_callback":
        title = context.user_data.get("submenu_title")
        parent_key = context.user_data.get("parent_key")
        parent_menu = get_menu(parent_key)
        if not parent_menu:
            await update.message.reply_text("❌ منوی والد پیدا نشد.")
            context.user_data.clear()
            return
        parent_id = parent_menu[0]
        add_menu(title, text, parent_id)
        context.user_data.clear()
        await update.message.reply_text("✅ زیرمنو ساخته شد.")
        return
    
    # ===== فقط لینک =====
    if step == "file_wait_link":
        channel_id, message_id = extract_ids_from_link(text)
        
        if not channel_id or not message_id:
            await update.message.reply_text(
                "❌ لینک معتبر نیست.\n"
                "لینک باید به این شکل باشه:\n"
                "`https://t.me/c/123456789/123`",
                parse_mode="Markdown"
            )
            return
        
        menu_key = context.user_data.get("file_menu_key")
        if not menu_key:
            await update.message.reply_text("❌ خطا: منو پیدا نشد.")
            context.user_data.clear()
            return
        
        menu = get_menu(menu_key)
        if not menu:
            await update.message.reply_text("❌ منو پیدا نشد.")
            context.user_data.clear()
            return
        
        menu_id = menu[0]
        
        db = get_db()
        c = db.cursor()
        c.execute("SELECT parent_id FROM menus WHERE id=?", (menu_id,))
        parent_row = c.fetchone()
        db.close()
        
        if not parent_row or parent_row[0] is None:
            await update.message.reply_text("❌ فقط زیرمنوها میتونن فایل داشته باشن.")
            context.user_data.clear()
            return
        
        add_content(menu_id, channel_id, message_id, "")
        
        try:
            await context.bot.copy_message(
                chat_id=update.effective_chat.id,
                from_chat_id=channel_id,
                message_id=message_id
            )
        except Exception as e:
            await update.message.reply_text(f"خطا:\n{e}")
            return
            
        context.user_data.clear()
        await update.message.reply_text(
            f"✅ فایل با موفقیت به زیرمنو متصل شد.\n\n"
            f"Channel ID: `{channel_id}`\n"
            f"Message ID: `{message_id}`",
            parse_mode="Markdown"
        )
        return
    
    if step == "set_price_menu":
        menu = get_menu(text)
        if not menu:
            await update.message.reply_text("❌ منو پیدا نشد.")
            return
        context.user_data["price_menu_id"] = menu[0]
        context.user_data["step"] = "set_price_value"
        await update.message.reply_text("💰 قیمت (Stars) رو وارد کن:\n(0 = رایگان)")
        return
    
    if step == "set_price_value":
        try:
            price = int(text)
            if price < 0:
                raise ValueError
        except:
            await update.message.reply_text("❌ عدد معتبر بفرست.")
            return
        menu_id = context.user_data.get("price_menu_id")
        set_price(menu_id, price)
        context.user_data.clear()
        if price == 0:
            await update.message.reply_text("✅ منو رایگان شد.")
        else:
            await update.message.reply_text(f"✅ قیمت {price} Stars شد.")
        return