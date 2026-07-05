import logging
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

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def error_handler(update, context):
    logger.error(msg="Exception:", exc_info=context.error)
    if update and update.effective_chat:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ خطایی رخ داد. لطفاً دوباره تلاش کن."
            )
        except:
            pass

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_error_handler(error_handler)
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    
    logger.info("Bot started!")
    app.run_polling()

if __name__ == "__main__":
    main()