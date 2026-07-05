import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, PreCheckoutQueryHandler
from config import BOT_TOKEN
from handlers import *
from database import init_db

logging.basicConfig(level=logging.INFO)

async def error_handler(update, context):
    logging.error(f"Error: {context.error}")
    if update and update.effective_chat:
        await context.bot.send_message(update.effective_chat.id, "❌ خطا!")

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_error_handler(error_handler)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(CallbackQueryHandler(admin_buttons))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    
    print("✅ بات روشن شد!")
    app.run_polling()

if __name__ == "__main__":
    main()