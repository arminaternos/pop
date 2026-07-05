from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    PreCheckoutQueryHandler,
)
from config import BOT_TOKEN
from handlers import (
    start,
    callback_handler,
    admin_panel,
    text_handler,
    pre_checkout_handler,
    successful_payment_handler,
)
from database import init_db


def main():
    # ایجاد دیتابیس (در صورت عدم وجود)
    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    # دستورات
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))

    # دکمه‌ها (همه در یک هندلر)
    app.add_handler(CallbackQueryHandler(callback_handler))

    # پرداخت
    app.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))

    # متن (برای مراحل ادمین)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    # (اختیاری) اگر نیاز به دریافت پست‌های کانال دارید، این خط را فعال کنید
    # app.add_handler(MessageHandler(filters.UpdateType.CHANNEL_POST, channel_post_handler))

    print("🤖 Bot Started...")
    app.run_polling()


if __name__ == "__main__":
    main()