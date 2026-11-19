"""
Auth Handlers - LoginActivity.java + OtpActivity.java ကို Telegram Bot မှာ ပြန်ရေး
Flow: Phone → check-account → OTP → validate-otp → save session
"""

import logging
import re
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from api.client import check_account as api_check_account, get_otp, validate_otp, register_request
from session.manager import get_session, Account, parse_token_response
from api.client import get_customer

logger = logging.getLogger(__name__)

# Conversation states
PHONE_INPUT = 1
OTP_INPUT = 2
REGISTER_OTP = 3

PHONE_RE = re.compile(r"^09\d{7,9}$")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point - ask for phone number"""
    user = update.effective_user
    session = get_session(user.id)

    # Check if adding account or first time
    is_add = context.args and "add_account" in context.args
    current = session.get_current_account()

    if current and current.is_logged_in() and not is_add:
        await update.message.reply_text(
            f"👋 မင်္ဂလာပါ *{current.full_name or current.phone}*!\n\n"
            f"📱 ဖုန်းနံပါတ်: `{current.phone}`\n\n"
            "အောက်ပါ command များကို သုံးနိုင်ပါသည်:\n"
            "• /dashboard - မင်္ဂလာ screen\n"
            "• /loyalty - Loyalty Points\n"
            "• /history - Points History\n"
            "• /exchange - Points Exchange\n"
            "• /dailyquest - Daily Quest\n"
            "• /dailyclaim - Claim Daily Reward\n"
            "• /datapackages - Data Packages\n"
            "• /myidgo - MyID GO Game\n"
            "• /account - Account Info\n"
            "• /addaccount - Add another account",
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "🔐 *ZenoMyID Bot*\n\n"
        "Mytel ဖုန်းနံပါတ်ကို ထည့်ပါ:\n"
        "_(ဥပမာ: 09xxxxxxxx)_\n\n"
        "ဖျက်ရန်: /cancel",
        parse_mode="Markdown",
    )

    # Mark if adding account
    session.set_pending("add_account", is_add)
    return PHONE_INPUT


async def handle_phone_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle phone number input"""
    user = update.effective_user
    session = get_session(user.id)
    phone = update.message.text.strip().replace(" ", "").replace("-", "")

    if not PHONE_RE.match(phone):
        await update.message.reply_text(
            "❌ မှန်ကန်သော Mytel နံပါတ် ထည့်ပါ\n"
            "_(09xxxxxxxx ပုံစံဖြင့်)_",
            parse_mode="Markdown",
        )
        return PHONE_INPUT

    msg = await update.message.reply_text("🔍 စစ်ဆေးနေသည်...")

    try:
        result = await api_check_account(phone)
        body = result.get("body", {})
        status_code = result.get("status", 0)

        # Save phone for later steps
        session.set_pending("phone", phone)
        session.set_pending("device_id", str(uuid.uuid4()))

        # Determine if registered or not
        # App checks if account exists; if not, goes to register flow
        response_code = body.get("responseCode") or body.get("code") or body.get("statusCode") or ""
        is_registered = _is_registered(body, status_code)

        if is_registered:
            # Registered → request OTP for login
            otp_result = await get_otp(phone)
            await msg.edit_text(
                f"📲 OTP ကို `{phone}` သို့ ပို့ပြီးပါပြီ!\n\n"
                "6-digit OTP ကို ထည့်ပါ:",
                parse_mode="Markdown",
            )
            session.set_pending("flow", "login")
            return OTP_INPUT
        else:
            # Not registered → register flow
            reg_result = await register_request(phone)
            await msg.edit_text(
                f"📲 မှတ်ပုံတင်ရန် OTP ကို `{phone}` သို့ ပို့ပြီးပါပြီ!\n\n"
                "6-digit OTP ကို ထည့်ပါ:",
                parse_mode="Markdown",
            )
            session.set_pending("flow", "register")
            return REGISTER_OTP

    except Exception as e:
        logger.error(f"check_account error: {e}")
        await msg.edit_text(
            "❌ ချိတ်ဆက်မှု မအောင်မြင်ပါ။ ထပ်မံ ကြိုးစားပါ:"
        )
        return PHONE_INPUT


def _is_registered(body: dict, status_code: int) -> bool:
    """Determine from API response if phone has MyID account"""
    if isinstance(body, dict):
        code = str(body.get("responseCode") or body.get("code") or "")
        message = str(body.get("message") or body.get("responseMessage") or "").lower()
        data = body.get("data") or {}
        # Common patterns
        if code in ("1000", "200", "0"):
            return True
        if "not found" in message or "not exist" in message or "register" in message:
            return False
        if isinstance(data, dict) and data.get("isRegistered") is not None:
            return bool(data["isRegistered"])
        # If status 200 without error, assume registered
        if status_code == 200 and not body.get("error"):
            return True
    return status_code == 200


async def handle_otp_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle OTP input for existing account login"""
    user = update.effective_user
    session = get_session(user.id)
    otp = update.message.text.strip().replace(" ", "")

    if not otp.isdigit() or len(otp) != 6:
        await update.message.reply_text(
            "❌ 6-digit OTP ကို ထည့်ပါ:"
        )
        return OTP_INPUT

    phone = session.get_pending("phone")
    device_id = session.get_pending("device_id") or str(uuid.uuid4())

    if not phone:
        await update.message.reply_text("⚠️ Session ကုန်ဆုံးပါပြီ။ /start ပြန်လုပ်ပါ")
        return ConversationHandler.END

    msg = await update.message.reply_text("⏳ Verifying...")

    try:
        result = await validate_otp(phone, otp, device_id)
        body = result.get("body", {})
        status = result.get("status", 0)

        if status not in (200, 201) and not _has_token(body):
            err_msg = body.get("message") or body.get("responseMessage") or "မသိသော error"
            await msg.edit_text(f"❌ OTP မမှန်ကန်ပါ: {err_msg}\nထပ်မံ ကြိုးစားပါ:")
            return OTP_INPUT

        # Extract tokens
        tokens = parse_token_response(body)
        access_token = tokens.get("access_token", "")

        if not access_token:
            await msg.edit_text("❌ Token ရရှိမှု မအောင်မြင်ပါ။ ထပ်မံ ကြိုးစားပါ:")
            return OTP_INPUT

        # Build account
        account = Account()
        account.phone = phone
        account.access_token = access_token
        account.refresh_token = tokens.get("refresh_token", "")
        account.uuid = tokens.get("uuid", "")
        account.mcuid = tokens.get("mcuid", "")
        account.tpt_sub = tokens.get("tpt_sub", "")
        account.device_id = device_id
        account.expiry = tokens.get("expiry", "")

        # Also parse raw_tpt_token (some responses include it)
        raw_tpt = body.get("rawTptToken") or (body.get("data") or {}).get("rawTptToken", "")
        account.raw_tpt_token = raw_tpt

        # Fetch customer profile
        try:
            cust_result = await get_customer(access_token)
            cust = cust_result.get("body", {})
            cust_data = cust.get("data") or cust or {}
            if isinstance(cust_data, dict):
                account.full_name = cust_data.get("fullName") or cust_data.get("name") or ""
                account.avatar_url = cust_data.get("avatarUrl") or cust_data.get("avatar") or ""
        except Exception as e:
            logger.warning(f"Profile fetch warning: {e}")

        session.save_account(account)
        session.set_current_phone(phone)
        session.clear_pending()

        await msg.edit_text(
            f"✅ *Login အောင်မြင်ပါသည်!*\n\n"
            f"👤 နာမည်: {account.full_name or '(မသိ)'}\n"
            f"📱 ဖုန်း: `{phone}`\n\n"
            "/dashboard ကို နှိပ်ပါ",
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    except Exception as e:
        logger.error(f"validate_otp error: {e}")
        await msg.edit_text("❌ ချိတ်ဆက်မှု error ဖြစ်ပါသည်။ ထပ်မံ ကြိုးစားပါ:")
        return OTP_INPUT


async def handle_register_otp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle OTP input for new account registration (same as login after register)"""
    # Registration OTP validation uses same validate-otp endpoint
    return await handle_otp_input(update, context)


def _has_token(body: dict) -> bool:
    if not isinstance(body, dict):
        return False
    if body.get("access_token") or body.get("accessToken"):
        return True
    data = body.get("data") or {}
    if isinstance(data, dict):
        return bool(data.get("access_token") or data.get("accessToken"))
    return False


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel conversation"""
    user = update.effective_user
    session = get_session(user.id)
    session.clear_pending()
    await update.message.reply_text("❌ ပယ်ဖျက်လိုက်ပါပြီ။")
    return ConversationHandler.END
