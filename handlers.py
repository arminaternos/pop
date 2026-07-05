import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import ContextTypes
from config import DELETE_TIME
from database import (
    connect,
    get_menu,
    get_children,
    get_root_menus,
    get_content,
    is_paid,
    is_admin,
    add_menu,
    delete_menu,
    set_menu_price,
    add_content,
    add_user,
    add_payment,
    set_payment_success
)

logger = logging.getLogger(__name__)


# ========================= START =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        add_user(user.id, user.username, user.full_name)

        rows = get_root_menus()
        if not rows:
            await update.message.reply_text("⛔ منویی وجود ندارد. لطفاً با ادمین تماس بگیرید.")
            return

        keyboard = [
            [InlineKeyboardButton(title, callback_data=cb)]
            for title, cb in rows
        ]
        await update.message.reply_text(
            "📌 منوی اصلی",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error in start: {e}")
        await update.message.reply_text("❌ خطا در بارگذاری منو. لطفاً دوباره تلاش کنید.")


# ========================= SINGLE CALLBACK HANDLER =========================
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    # ----- دکمه‌های ادمین (با پیشوند admin_) -----
    if data.startswith("admin_"):
        if not is_admin(user_id):
            await query.message.reply_text("⛔ دسترسی ندارید.")
            return
        await admin_buttons_handler(query, context, data)
        return

    # ----- دکمه بازگشت -----
    if data == "back":
        await show_root_menu(query)
        return

    # ----- منوی معمولی -----
    menu = get_menu(data)
    if not menu:
        await query.answer("نامعتبر", show_alert=True)
        return

    menu_id, title, paid, price = menu

    # بررسی زیرمنوها
    children = get_children(menu_id)
    if children:
        keyboard = [
            [InlineKeyboardButton(t, callback_data=c)]
            for t, c in children
        ]
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back")])
        await query.edit_message_text(
            title,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # محتوا
    content = get_content(menu_id)
    if not content:
        await query.answer("محتوا یافت نشد", show_alert=True)
        return

    channel_id, message_id = content

    # بررسی پرداخت
    if paid and not is_paid(user_id, menu_id):
        await query.message.reply_text(
            f"💳 این محتوا پولی است\n💰 قیمت: {price} Stars\n\nبرای دسترسی باید پرداخت کنید."
        )
        await send_invoice(query, context, menu_id, price, user_id)
        return

    # ارسال محتوا
    try:
        sent = await context.bot.copy_message(
            chat_id=query.message.chat.id,
            from_chat_id=channel_id,
            message_id=message_id
        )

        # حذف خودکار
        context.job_queue.run_once(
            lambda ctx: ctx.bot.delete_message(
                chat_id=sent.chat.id,
                message_id=sent.message_id
            ),
            DELETE_TIME
        )
    except Exception as e:
        logger.error(f"Error sending content: {e}")
        await query.message.reply_text("❌ خطا در ارسال محتوا.")


# ========================= SHOW ROOT MENU =========================
async def show_root_menu(query):
    rows = get_root_menus()
    if not rows:
        await query.edit_message_text("⛔ منویی وجود ندارد.")
        return
    keyboard = [
        [InlineKeyboardButton(title, callback_data=cb)]
        for title, cb in rows
    ]
    await query.edit_message_text(
        "📌 منوی اصلی",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ========================= SEND INVOICE =========================
async def send_invoice(query, context, menu_id, price, user_id):
    try:
        await context.bot.send_invoice(
            chat_id=user_id,
            title="خرید محتوا",
            description="دسترسی به محتوای انتخابی",
            payload=f"menu_{menu_id}_{user_id}",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice("Access", price)]
        )
    except Exception as e:
        logger.error(f"Error sending invoice: {e}")
        await query.message.reply_text("❌ خطا در ارسال فاکتور.")


# ========================= PRE-CHECKOUT =========================
async def pre_checkout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    await query.answer(ok=True)


# ========================= SUCCESSFUL PAYMENT =========================
async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user_id = message.from_user.id
    payload = message.successful_payment.invoice_payload
    parts = payload.split("_")
    if len(parts) == 3 and parts[0] == "menu":
        menu_id = int(parts[1])
        set_payment_success(user_id, menu_id)
        await message.reply_text("✅ پرداخت موفق! در حال ارسال محتوا...")

        content = get_content(menu_id)
        if content:
            channel_id, message_id = content
            try:
                sent = await context.bot.copy_message(
                    chat_id=user_id,
                    from_chat_id=channel_id,
                    message_id=message_id
                )
                context.job_queue.run_once(
                    lambda ctx: ctx.bot.delete_message(
                        chat_id=sent.chat.id,
                        message_id=sent.message_id
                    ),
                    DELETE_TIME
                )
            except Exception as e:
                logger.error(f"Error sending content after payment: {e}")
                await message.reply_text("❌ خطا در ارسال محتوا.")
        else:
            await message.reply_text("⚠️ محتوا یافت نشد، با ادمین تماس بگیرید.")


# ========================= ADMIN PANEL =========================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ دسترسی ندارید.")
        return

    keyboard = [
        [InlineKeyboardButton("➕ افزودن منو", callback_data="admin_add_menu")],
        [InlineKeyboardButton("📁 افزودن فایل به منو", callback_data="admin_add_file")],
        [InlineKeyboardButton("💰 تنظیم قیمت منو", callback_data="admin_set_price")],
        [InlineKeyboardButton("🗂 لیست منوها (حذف)", callback_data="admin_list_menus")]
    ]
    await update.message.reply_text(
        "🛠 پنل ادمین",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ========================= ADMIN BUTTONS HANDLER =========================
async def admin_buttons_handler(query, context, data):
    if data == "admin_add_menu":
        context.user_data["step"] = "menu_title"
        await query.message.reply_text("✏️ اسم منو رو بفرست:")
        return

    if data == "admin_add_file":
        context.user_data["step"] = "file_menu"
        await query.message.reply_text("🔑 کد منو (callback_key) رو بفرست:")
        return

    if data == "admin_set_price":
        context.user_data["step"] = "set_price_select_menu"
        await query.message.reply_text("🔑 کد منو (callback_key) رو بفرست:\n(برای رایگان کردن، قیمت 0 را وارد کن)")
        return

    if data == "admin_list_menus":
        conn = connect()
        cur = conn.cursor()
        cur.execute("SELECT title, callback_key FROM menus")
        rows = cur.fetchall()
        conn.close()
        if not rows:
            await query.message.reply_text("📭 هیچ منویی وجود ندارد.")
            return
        keyboard = []
        for t, c in rows:
            # نمایش قیمت و وضعیت پرداخت
            menu = get_menu(c)
            if menu:
                _, _, paid, price = menu
                status = "💰" if paid else "🆓"
                label = f"{status} {t} ({c})"
            else:
                label = f"❓ {t} ({c})"
            keyboard.append([InlineKeyboardButton(f"❌ {label}", callback_data=f"del_menu:{c}")])
        await query.message.reply_text(
            "🗂 لیست منوها (برای حذف کلیک کنید):",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if data.startswith("del_menu:"):
        callback = data.split(":")[1]
        try:
            delete_menu(callback)
            await query.message.reply_text(f"🗑 منو `{callback}` و زیرمنوهایش حذف شدند.", parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Error deleting menu: {e}")
            await query.message.reply_text("❌ خطا در حذف منو.")


# ========================= TEXT HANDLER (مراحل ادمین) =========================
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ شما ادمین نیستید.")
        return

    step = context.user_data.get("step")
    text = update.message.text.strip()

    # ----- مرحله ۱: عنوان منو -----
    if step == "menu_title":
        context.user_data["menu_title"] = text
        context.user_data["step"] = "menu_callback"
        await update.message.reply_text("🔑 callback_key رو بفرست:")
        return

    # ----- مرحله ۲: callback_key منو -----
    if step == "menu_callback":
        title = context.user_data.get("menu_title")
        try:
            add_menu(title, text, parent_id=None, is_paid=0, price=0)
            context.user_data.clear()
            await update.message.reply_text("✅ منو ساخته شد.")
        except Exception as e:
            logger.error(f"Error adding menu: {e}")
            await update.message.reply_text("❌ خطا در ساخت منو. احتمالاً callback_key تکراری است.")
        return

    # ----- مرحله انتخاب منو برای اتصال فایل -----
    if step == "file_menu":
        menu = get_menu(text)
        if not menu:
            await update.message.reply_text("❌ منو با این callback_key یافت نشد.")
            return
        context.user_data["file_menu_id"] = menu[0]
        context.user_data["step"] = "file_wait"
        await update.message.reply_text("📌 حالا پیام مورد نظر را از کانال **فوروارد** کنید.")
        return

    # ----- مرحله دریافت فوروارد از کانال -----
    if step == "file_wait":
        # بررسی اینکه آیا پیام فورواردی است یا نه
        if not update.message.forward_from_chat:
            await update.message.reply_text("❌ لطفاً یک پیام فورواردی از کانال ارسال کنید.")
            return

        menu_id = context.user_data.get("file_menu_id")
        if not menu_id:
            await update.message.reply_text("❌ خطا در شناسایی منو، دوباره تلاش کنید.")
            context.user_data.clear()
            return

        channel_id = update.message.forward_from_chat.id
        message_id = update.message.forward_from_message_id
        caption = update.message.caption or ""

        try:
            add_content(menu_id, channel_id, message_id, caption)
            context.user_data.clear()
            await update.message.reply_text("✅ فایل با موفقیت به منو متصل شد.")
        except Exception as e:
            logger.error(f"Error adding content: {e}")
            await update.message.reply_text("❌ خطا در اتصال فایل.")
        return

    # ----- مرحله انتخاب منو برای تنظیم قیمت -----
    if step == "set_price_select_menu":
        menu = get_menu(text)
        if not menu:
            await update.message.reply_text("❌ منو با این callback_key یافت نشد.")
            return
        context.user_data["price_menu_id"] = menu[0]
        context.user_data["step"] = "set_price"
        await update.message.reply_text("💰 حالا قیمت (تعداد Stars) را وارد کنید:\n(برای رایگان کردن، عدد 0 را وارد کنید)")
        return

    # ----- مرحله دریافت قیمت -----
    if step == "set_price":
        try:
            price = int(text)
            if price < 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text("❌ لطفاً یک عدد معتبر (۰ یا بیشتر) وارد کنید.")
            return

        menu_id = context.user_data.get("price_menu_id")
        if not menu_id:
            await update.message.reply_text("❌ خطا در شناسایی منو.")
            context.user_data.clear()
            return

        try:
            set_menu_price(menu_id, price)
            context.user_data.clear()
            if price == 0:
                await update.message.reply_text("🆓 منو **رایگان** شد.", parse_mode="Markdown")
            else:
                await update.message.reply_text(f"💰 قیمت منو به {price} Stars تنظیم شد.")
        except Exception as e:
            logger.error(f"Error setting price: {e}")
            await update.message.reply_text("❌ خطا در تنظیم قیمت.")
        return

    # اگر مرحله ناشناخته
    await update.message.reply_text("⚠️ دستور نامشخص. لطفاً از دکمه‌های پنل ادمین استفاده کنید.")