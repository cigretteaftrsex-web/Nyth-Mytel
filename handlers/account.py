"""
Account Handler - AccountsActivity + DashboardActivity profile section ကို ပြန်ရေး
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from api.client import get_customer, get_account_detail, update_customer
from session.manager import get_session

logger = logging.getLogger(__name__)


def _get_account(update, context):
    user = update.effective_user
    session = get_session(user.id)
    return session, session.get_current_account()


async def account_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_account(update, context)


async def show_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session, account = _get_account(update, context)
    msg_obj = update.message or update.callback_query.message

    if not account or not account.is_logged_in():
        await msg_obj.reply_text("⚠️ Login မဝင်ရသေးပါ။ /start နှိပ်ပါ")
        return

    loading = await msg_obj.reply_text("⏳ Account info ရယူနေသည်...")

    try:
        # Fetch customer profile
        cust_result = await get_customer(account.access_token)
        cust_body = cust_result.get("body", {})
        cust_data = cust_body.get("data") or cust_body or {}

        full_name = ""
        gender = ""
        birth_date = ""
        email = ""
        avatar_url = ""
        if isinstance(cust_data, dict):
            full_name = cust_data.get("fullName") or cust_data.get("name") or account.full_name
            gender = cust_data.get("gender") or ""
            birth_date = cust_data.get("birthDate") or ""
            email = cust_data.get("email") or ""
            avatar_url = cust_data.get("avatarUrl") or cust_data.get("avatar") or account.avatar_url

        # Fetch account detail (balance, data, etc.)
        detail_text = ""
        try:
            detail_result = await get_account_detail(
                account.phone, account.access_token, account.device_id
            )
            detail_body = detail_result.get("body", {})
            detail_data = detail_body.get("data") or detail_body or {}
            if isinstance(detail_data, dict):
                balance = detail_data.get("balance") or detail_data.get("mainBalance") or 0
                data_mb = detail_data.get("dataBalance") or detail_data.get("dataUsage") or 0
                plan = detail_data.get("plan") or detail_data.get("packageName") or ""
                detail_text = (
                    f"\n\n📊 *Account Detail*\n"
                    f"💵 Balance: {balance}\n"
                    f"📶 Data: {data_mb}\n"
                    + (f"📦 Plan: {plan}\n" if plan else "")
                )
        except Exception as e:
            logger.warning(f"Account detail warning: {e}")

        # All accounts list
        all_accounts = session.get_accounts()
        accounts_info = ""
        if len(all_accounts) > 1:
            accounts_info = f"\n\n📋 *Saved Accounts ({len(all_accounts)})*\n"
            for acc in all_accounts:
                mark = "✅ " if acc.phone == account.phone else "   "
                accounts_info += f"{mark}{acc.phone} - {acc.full_name or '(no name)'}\n"

        text = (
            f"👤 *Account Info*\n\n"
            f"📱 Phone: `{account.phone}`\n"
            f"🙍 Name: *{full_name or '(not set)'}*\n"
            f"🚻 Gender: {gender.capitalize() or 'N/A'}\n"
            f"🎂 Birth Date: {birth_date or 'N/A'}\n"
            f"📧 Email: {email or 'N/A'}\n"
            f"🆔 UUID: `{account.uuid[:20] + '...' if len(account.uuid) > 20 else account.uuid or 'N/A'}`"
            + detail_text
            + accounts_info
        )

        buttons = [
            [
                InlineKeyboardButton("✏️ Edit Profile", callback_data="acc_edit"),
                InlineKeyboardButton("🔄 Refresh", callback_data="acc_refresh"),
            ],
            [InlineKeyboardButton("🗑️ Logout This Account", callback_data="acc_logout")],
            [InlineKeyboardButton("🏠 Dashboard", callback_data="acc_dashboard")],
        ]
        await loading.edit_text(text, parse_mode="Markdown",
                                reply_markup=InlineKeyboardMarkup(buttons))

    except Exception as e:
        logger.error(f"Account show error: {e}")
        await loading.edit_text("❌ Account info ရယူ မရပါ")


async def handle_account_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "acc_refresh":
        await show_account(update, context)
    elif data == "acc_edit":
        await show_edit_profile(update, context)
    elif data == "acc_logout":
        await do_logout(update, context)
    elif data == "acc_dashboard":
        from handlers.dashboard import show_dashboard
        await show_dashboard(update, context)
    elif data.startswith("acc_gender_"):
        await handle_gender_select(update, context)


async def show_edit_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    buttons = [
        [
            InlineKeyboardButton("👦 Male", callback_data="acc_gender_male"),
            InlineKeyboardButton("👧 Female", callback_data="acc_gender_female"),
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="acc_refresh")],
    ]
    await query.message.reply_text(
        "✏️ *Profile Edit*\nGender ရွေးပါ:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def handle_gender_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    gender = query.data.replace("acc_gender_", "")
    session, account = _get_account(update, context)

    if not account or not account.is_logged_in():
        return

    msg = await query.message.reply_text(f"⏳ Updating gender to {gender}...")
    try:
        result = await update_customer(account.access_token, gender=gender)
        status = result.get("status", 0)
        if status in (200, 201):
            await msg.edit_text(f"✅ Gender updated to {gender}!")
        else:
            body = result.get("body", {})
            err = body.get("message") or "မသိသော error"
            await msg.edit_text(f"❌ Update မအောင်မြင်ပါ: {err}")
    except Exception as e:
        logger.error(f"Update profile error: {e}")
        await msg.edit_text("❌ Update လုပ်မရပါ")


async def do_logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    buttons = [
        [
            InlineKeyboardButton("✅ Logout", callback_data="acc_logout_confirm"),
            InlineKeyboardButton("❌ Cancel", callback_data="acc_refresh"),
        ]
    ]
    await query.message.reply_text(
        "⚠️ Logout လုပ်မည်လား?",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def update_profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✏️ Profile update:\n/account ကို သုံးပြီး Edit Profile နှိပ်ပါ"
    )


async def handle_profile_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass
