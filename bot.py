"""
ZenoMyID Telegram Bot
Replicates ZenoMyID 4.0 Android App functionality as a Telegram Bot
"""

import os
import logging
import asyncio
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, CallbackQueryHandler,
    filters, ContextTypes
)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv

from handlers.auth import (
    start, check_account, handle_phone_input,
    handle_otp_input, handle_register_otp,
    cancel, PHONE_INPUT, OTP_INPUT, REGISTER_OTP
)
from handlers.dashboard import (
    dashboard_command, show_dashboard,
    handle_dashboard_callback
)
from handlers.loyalty import (
    loyalty_command, handle_loyalty_callback,
    points_history_command, exchange_command,
    handle_exchange_callback, extend_points_command
)
from handlers.account import (
    account_command, handle_account_callback,
    update_profile_command, handle_profile_update
)
from handlers.myidgo import (
    myidgo_command, handle_myidgo_callback
)
from handlers.daily_quest import (
    daily_quest_command, handle_daily_quest_callback,
    daily_claim_command
)
from handlers.data_packages import (
    data_packages_command, handle_data_callback
)

load_dotenv()
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception while handling an update:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "❌ တစ်ခုခု မှားယွင်းသွားပါသည်။ ထပ်မံ ကြိုးစားပါ။"
        )


def main() -> None:
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN ကို .env ဖိုင်တွင် သတ်မှတ်ပါ")

    application = Application.builder().token(BOT_TOKEN).build()

    # Auth conversation handler
    auth_conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("login", start),
            CommandHandler("addaccount", start),
        ],
        states={
            PHONE_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_phone_input)
            ],
            OTP_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_otp_input)
            ],
            REGISTER_OTP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_register_otp)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    # Main handlers
    application.add_handler(auth_conv)
    application.add_handler(CommandHandler("dashboard", dashboard_command))
    application.add_handler(CommandHandler("loyalty", loyalty_command))
    application.add_handler(CommandHandler("history", points_history_command))
    application.add_handler(CommandHandler("exchange", exchange_command))
    application.add_handler(CommandHandler("extend", extend_points_command))
    application.add_handler(CommandHandler("account", account_command))
    application.add_handler(CommandHandler("myidgo", myidgo_command))
    application.add_handler(CommandHandler("dailyquest", daily_quest_command))
    application.add_handler(CommandHandler("dailyclaim", daily_claim_command))
    application.add_handler(CommandHandler("datapackages", data_packages_command))

    # Callback query handlers
    application.add_handler(CallbackQueryHandler(handle_dashboard_callback, pattern="^dash_"))
    application.add_handler(CallbackQueryHandler(handle_loyalty_callback, pattern="^loyal_"))
    application.add_handler(CallbackQueryHandler(handle_exchange_callback, pattern="^exchange_"))
    application.add_handler(CallbackQueryHandler(handle_account_callback, pattern="^acc_"))
    application.add_handler(CallbackQueryHandler(handle_myidgo_callback, pattern="^myidgo_"))
    application.add_handler(CallbackQueryHandler(handle_daily_quest_callback, pattern="^dq_"))
    application.add_handler(CallbackQueryHandler(handle_data_callback, pattern="^data_"))

    application.add_error_handler(error_handler)

    logger.info("ZenoMyID Bot စတင်နေပါသည်...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
