import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import ContextTypes
from config import DELETE_TIME
from database import *

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id, user.username, user.full_name)
    
    menus = get_root_menus()
    if not menus:
        await update.message.reply_text("⛔ منویی وجود ندارد. از /admin استفاده کن.")
        return
    
    keyboard = [[InlineKeyboardButton(title, callback_data=cb)] for title, cb in menus]
    await update.message.reply_text("📌 منوی اصلی", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    
    # برگشت به منوی اصلی
    if data == "back":
        menus = get_root_menus()
        if not menus:
            await query.edit_message_text("⛔ منویی وجود ندارد.")
            return
        keyboard = [[InlineKeyboardButton(title, callback_data=cb)] for title, cb in menus]
        await query.edit_message_text("📌 منوی اصلی", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    # منوی معمولی
    menu = get_menu(data)
    if not menu:
        await query.answer("نامعتبر", show_alert=True)
        return
    
    menu_id, title, is_paid, price = menu
    
    # زیرمنوها رو چک کن
    children = get_children(menu_id)
    if children:
        keyboard = [[InlineKeyboardButton(t, callback_data=c)] for t, c in children]
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back")])
        await query.edit_message_text(title, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    # محتوا
    content = get_content(menu_id)
    if not content:
        await query.answer("محتوا یافت نشد", show_alert=True)
        return
    
    channel_id, message_id = content
    
    # پرداخت
    if is_paid and not is_paid(user_id, menu_id):
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
    
    # ارسال محتوا
    try:
        sent = await context.bot.copy_message(
            chat_id=query.message.chat.id,
            from_chat_id=channel_id,
            message_id=message_id
        )
        context.job_queue.run_once(
            lambda ctx: ctx.bot.delete_message(chat_id=sent.chat.id, message_id=sent.message_id),
            DELETE_TIME
        )
    except Exception as e:
        logger.error(f"خطا: {e}")
        await query.message.reply_text("❌ خطا در ارسال محتوا.")

# پرداخت
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
        
        content = get_content(menu_id)
        if content:
            channel_id, message_id = content
            sent = await context.bot.copy_message(
                chat_id=user_id,
                from_chat_id=channel_id,
                message_id=message_id
            )
            context.job_queue.run_once(
                lambda ctx: ctx.bot.delete_message(chat_id=sent.chat.id, message_id=sent.message_id),
                DELETE_TIME
            )

# پنل ادمین
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ دسترسی ندارید.")
        return
    
    keyboard = [
        [InlineKeyboardButton("➕ افزودن منو", callback_data="admin_add_menu")],
        [InlineKeyboardButton("➕ افزودن زیرمنو", callback_data="admin_add_submenu")],
        [InlineKeyboardButton("📁 افزودن فایل", callback_data="admin_add_file")],
        [InlineKeyboardButton("💰 تنظیم قیمت", callback_data="admin_set_price")],
        [InlineKeyboardButton("🗑 حذف منو", callback_data="admin_delete_menu")],
    ]
    await update.message.reply_text("🛠 پنل ادمین", reply_markup=InlineKeyboardMarkup(keyboard))

# دکمه‌های ادمین
async def admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        await query.message.reply_text("⛔ دسترسی ندارید.")
        return
    
    # افزودن منو
    if data == "admin_add_menu":
        context.user_data["step"] = "menu_title"
        await query.message.reply_text("✏️ اسم منو رو بفرست:")
        return
    
    # افزودن زیرمنو
    if data == "admin_add_submenu":
        menus = get_root_menus()
        if not menus:
            await query.message.reply_text("❌ اول یه منوی اصلی بساز.")
            return
        keyboard = [[InlineKeyboardButton(t, callback_data=f"parent_{c}")] for t, c in menus]
        await query.message.reply_text("زیر کدوم منو باشه؟", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    if data.startswith("parent_"):
        parent_cb = data[7:]
        context.user_data["parent_key"] = parent_cb
        context.user_data["step"] = "submenu_title"
        await query.message.reply_text("✏️ اسم زیرمنو رو بفرست:")
        return
    
    # افزودن فایل
    if data == "admin_add_file":
        context.user_data["step"] = "file_menu"
        await query.message.reply_text("🔑 کد منو رو بفرست:")
        return
    
    # تنظیم قیمت
    if data == "admin_set_price":
        context.user_data["step"] = "set_price_menu"
        await query.message.reply_text("🔑 کد منو رو بفرست:")
        return
    
    # حذف منو
    if data == "admin_delete_menu":
        all_menus = get_all_menus()
        if not all_menus:
            await query.message.reply_text("📭 منویی وجود ندارد.")
            return
        
        keyboard = []
        for title, cb, parent_id in all_menus:
            icon = "📁" if parent_id is None else "📄"
            keyboard.append([InlineKeyboardButton(f"{icon} {title}", callback_data=f"del_{cb}")])
        
        await query.message.reply_text("منو رو برای حذف انتخاب کن:", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    if data.startswith("del_"):
        cb = data[4:]
        delete_menu(cb)
        await query.message.reply_text(f"✅ منو حذف شد.")
        return

# دریافت متن از کاربر
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return
    
    step = context.user_data.get("step")
    text = update.message.text.strip()
    
    # ساخت منو
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
    
    # ساخت زیرمنو
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
    
    # اتصال فایل
    if step == "file_menu":
        menu = get_menu(text)
        if not menu:
            await update.message.reply_text("❌ منو پیدا نشد.")
            return
        context.user_data["file_menu_id"] = menu[0]
        context.user_data["step"] = "file_wait"
        await update.message.reply_text("📌 پیام رو از کانال فوروارد کن:")
        return
    
    if step == "file_wait":
        if not update.message.forward_from_chat:
            await update.message.reply_text("❌ یه پیام فورواردی بفرست.")
            return
        menu_id = context.user_data.get("file_menu_id")
        channel_id = update.message.forward_from_chat.id
        message_id = update.message.forward_from_message_id
        add_content(menu_id, channel_id, message_id, update.message.caption or "")
        context.user_data.clear()
        await update.message.reply_text("✅ فایل متصل شد.")
        return
    
    # تنظیم قیمت
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