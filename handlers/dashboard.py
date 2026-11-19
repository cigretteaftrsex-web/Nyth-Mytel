"""
Dashboard Handler - DashboardActivity.java ကို Telegram Bot မှာ ပြန်ရေး
Main screen: profile, loyalty tier, quick actions
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from api.client import get_customer, get_loyalty_inquiry, get_account_detail
from session.manager import get_session

logger = logging.getLogger(__name__)

TIER_EMOJI = {
    "platinum": "💎",
    "diamond": "💎",
    "ruby": "❤️",
    "gold": "🥇",
    "silver": "🥈",
    "swarovski": "✨",
    "bronze": "🥉",
}


def _require_login(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        session = get_session(user.id)
        account = session.get_current_account()
        if not account or not account.is_logged_in():
            msg = update.message or update.callback_query.message
            await msg.reply_text("⚠️ Login မဝင်ရသေးပါ။ /start နှိပ်ပါ")
            return
        return await func(update, context)
    return wrapper


async def dashboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_dashboard(update, context)


async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    session = get_session(user.id)
    account = session.get_current_account()

    if not account or not account.is_logged_in():
        msg = update.message or update.callback_query.message
        await msg.reply_text("⚠️ Login မဝင်ရသေးပါ။ /start နှိပ်ပါ")
        return

    msg_obj = update.message or update.callback_query.message
    loading = await msg_obj.reply_text("⏳ Loading...")

    try:
        # Fetch customer profile
        cust_result = await get_customer(account.access_token)
        cust_body = cust_result.get("body", {})
        cust_data = cust_body.get("data") or cust_body or {}

        full_name = ""
        avatar_url = ""
        gender = "male"
        birth_date = ""
        if isinstance(cust_data, dict):
            full_name = cust_data.get("fullName") or cust_data.get("name") or account.full_name
            avatar_url = cust_data.get("avatarUrl") or cust_data.get("avatar") or account.avatar_url
            gender = cust_data.get("gender") or "male"
            birth_date = cust_data.get("birthDate") or ""

        # Update session
        if full_name:
            session.update_account_field(account.phone, fullName=full_name, avatarUrl=avatar_url)

        # Fetch loyalty inquiry
        loyalty_text = ""
        try:
            loy_result = await get_loyalty_inquiry(
                account.phone, account.access_token, account.device_id
            )
            loy_body = loy_result.get("body", {})
            loy_data = loy_body.get("data") or loy_body or {}
            if isinstance(loy_data, dict):
                points = loy_data.get("totalPoint") or loy_data.get("points") or loy_data.get("balance") or 0
                tier = str(loy_data.get("membershipTier") or loy_data.get("tier") or "").lower()
                tier_emoji = TIER_EMOJI.get(tier, "🏅")
                expiry = loy_data.get("expiredDate") or loy_data.get("expiryDate") or ""
                loyalty_text = (
                    f"\n\n💰 *Loyalty Points*\n"
                    f"{tier_emoji} Tier: {tier.capitalize() or 'N/A'}\n"
                    f"⭐ Points: *{points:,}*\n"
                    f"📅 Expiry: {expiry or 'N/A'}"
                )
        except Exception as e:
            logger.warning(f"Loyalty fetch warning: {e}")
            loyalty_text = "\n\n💰 Loyalty: _(fetch error)_"

        # Accounts list for switching
        all_accounts = session.get_accounts()
        text = (
            f"🏠 *Dashboard*\n\n"
            f"👤 *{full_name or account.phone}*\n"
            f"📱 {account.phone}\n"
            f"🚻 {gender.capitalize()}"
            + (f" | 🎂 {birth_date}" if birth_date else "")
            + loyalty_text
        )

        buttons = [
            [
                InlineKeyboardButton("💰 Loyalty", callback_data="dash_loyalty"),
                InlineKeyboardButton("📋 History", callback_data="dash_history"),
            ],
            [
                InlineKeyboardButton("🔄 Exchange", callback_data="dash_exchange"),
                InlineKeyboardButton("⏳ Extend", callback_data="dash_extend"),
            ],
            [
                InlineKeyboardButton("🎮 MyID GO", callback_data="dash_myidgo"),
                InlineKeyboardButton("🏆 Daily Quest", callback_data="dash_dq"),
            ],
            [
                InlineKeyboardButton("📦 Data Packages", callback_data="dash_data"),
                InlineKeyboardButton("👤 Account", callback_data="dash_account"),
            ],
            [InlineKeyboardButton("🔄 Refresh", callback_data="dash_refresh")],
        ]
        # Add account switch buttons if multiple
        if len(all_accounts) > 1:
            switch_btns = []
            for acc in all_accounts:
                label = f"{'✅ ' if acc.phone == account.phone else ''}{acc.phone[-4:]}"
                switch_btns.append(
                    InlineKeyboardButton(label, callback_data=f"dash_switch_{acc.phone}")
                )
            buttons.append(switch_btns)
        buttons.append([InlineKeyboardButton("➕ Add Account", callback_data="dash_addacc")])

        markup = InlineKeyboardMarkup(buttons)
        await loading.edit_text(text, parse_mode="Markdown", reply_markup=markup)

    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        await loading.edit_text("❌ Dashboard ဖွင့်မရပါ။ ထပ်မံ ကြိုးစားပါ")


async def handle_dashboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = update.effective_user
    session = get_session(user.id)

    if data == "dash_refresh":
        await show_dashboard(update, context)

    elif data == "dash_loyalty":
        from handlers.loyalty import show_loyalty
        await show_loyalty(update, context)

    elif data == "dash_history":
        from handlers.loyalty import show_points_history
        await show_points_history(update, context)

    elif data == "dash_exchange":
        from handlers.loyalty import show_exchange
        await show_exchange(update, context)

    elif data == "dash_extend":
        from handlers.loyalty import do_extend_points
        await do_extend_points(update, context)

    elif data == "dash_myidgo":
        from handlers.myidgo import show_myidgo
        await show_myidgo(update, context)

    elif data == "dash_dq":
        from handlers.daily_quest import show_daily_quest
        await show_daily_quest(update, context)

    elif data == "dash_data":
        from handlers.data_packages import show_data_packages
        await show_data_packages(update, context)

    elif data == "dash_account":
        from handlers.account import show_account
        await show_account(update, context)

    elif data == "dash_addacc":
        await query.message.reply_text("ထည့်ရန် /addaccount လုပ်ပါ")

    elif data.startswith("dash_switch_"):
        phone = data.replace("dash_switch_", "")
        session.set_current_phone(phone)
        await show_dashboard(update, context)
