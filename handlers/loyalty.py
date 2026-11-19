"""
Loyalty Handler - PointsExchangeActivity, PointsHistoryActivity, PointsExtendDialog ကို ပြန်ရေး
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from api.client import (
    get_loyalty_inquiry, get_loyalty_csm,
    get_points_history, get_packs, exchange_pack, extend_points
)
from session.manager import get_session

logger = logging.getLogger(__name__)

TIER_EMOJI = {"platinum": "💎", "diamond": "💎", "ruby": "❤️", "gold": "🥇",
              "silver": "🥈", "swarovski": "✨", "bronze": "🥉"}


def _get_account(update, context):
    user = update.effective_user
    session = get_session(user.id)
    account = session.get_current_account()
    return session, account


async def loyalty_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_loyalty(update, context)


async def show_loyalty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session, account = _get_account(update, context)
    msg_obj = update.message or update.callback_query.message

    if not account or not account.is_logged_in():
        await msg_obj.reply_text("⚠️ Login မဝင်ရသေးပါ။ /start နှိပ်ပါ")
        return

    loading = await msg_obj.reply_text("⏳ Loyalty Points ရယူနေသည်...")

    try:
        result = await get_loyalty_inquiry(account.phone, account.access_token, account.device_id)
        body = result.get("body", {})
        data = body.get("data") or body or {}

        if not isinstance(data, dict):
            await loading.edit_text("❌ Data ရရှိမှု မအောင်မြင်ပါ")
            return

        points = data.get("totalPoint") or data.get("points") or data.get("balance") or 0
        tier = str(data.get("membershipTier") or data.get("tier") or "").lower()
        tier_emoji = TIER_EMOJI.get(tier, "🏅")
        expiry = data.get("expiredDate") or data.get("expiryDate") or "N/A"
        earn_points = data.get("earnPoint") or data.get("earnedPoints") or 0
        redeem_points = data.get("redeemPoint") or data.get("redeemedPoints") or 0
        expire_points = data.get("expirePoint") or 0

        text = (
            f"💰 *Loyalty Points*\n\n"
            f"📱 {account.phone}\n"
            f"{tier_emoji} Tier: *{tier.capitalize() or 'N/A'}*\n\n"
            f"⭐ Total Points: *{points:,}*\n"
            f"📈 Earned: {earn_points:,}\n"
            f"📉 Redeemed: {redeem_points:,}\n"
            f"⚠️ About to expire: {expire_points:,}\n"
            f"📅 Expiry Date: {expiry}"
        )

        buttons = [
            [
                InlineKeyboardButton("📋 History", callback_data="loyal_history"),
                InlineKeyboardButton("🔄 Exchange", callback_data="loyal_exchange"),
            ],
            [
                InlineKeyboardButton("⏳ Extend Expiry", callback_data="loyal_extend"),
                InlineKeyboardButton("🔄 Refresh", callback_data="loyal_refresh"),
            ],
            [InlineKeyboardButton("🏠 Dashboard", callback_data="loyal_back")],
        ]
        await loading.edit_text(text, parse_mode="Markdown",
                                reply_markup=InlineKeyboardMarkup(buttons))

    except Exception as e:
        logger.error(f"Loyalty error: {e}")
        await loading.edit_text("❌ Loyalty Points ရယူ မရပါ")


async def points_history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_points_history(update, context)


async def show_points_history(update: Update, context: ContextTypes.DEFAULT_TYPE, history_type: str = "all"):
    session, account = _get_account(update, context)
    msg_obj = update.message or update.callback_query.message

    if not account or not account.is_logged_in():
        await msg_obj.reply_text("⚠️ Login မဝင်ရသေးပါ။ /start နှိပ်ပါ")
        return

    loading = await msg_obj.reply_text("⏳ History ရယူနေသည်...")

    try:
        result = await get_points_history(
            account.phone, history_type, account.access_token, account.device_id
        )
        body = result.get("body", {})
        data = body.get("data") or body or {}

        items = []
        if isinstance(data, dict):
            items = data.get("content") or data.get("history") or data.get("items") or []
        elif isinstance(data, list):
            items = data

        if not items:
            await loading.edit_text(
                "📋 *Points History*\n\nHistory မရှိသေးပါ",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="loyal_back_loyalty")]
                ])
            )
            return

        lines = ["📋 *Points History* (နောက်ဆုံး 50)\n"]
        for item in items[:20]:
            if not isinstance(item, dict):
                continue
            date = item.get("transactionDate") or item.get("date") or item.get("createdAt") or ""
            pts = item.get("points") or item.get("point") or 0
            desc = item.get("description") or item.get("type") or item.get("transactionType") or ""
            sign = "+" if int(pts) >= 0 else ""
            lines.append(f"• {date[:10] if date else '?'} | {sign}{pts} pts | {desc}")

        if len(items) > 20:
            lines.append(f"\n_...နှင့် {len(items)-20} ကြိမ် ထပ်ရှိသေးသည်_")

        buttons = [
            [
                InlineKeyboardButton("📥 Earn", callback_data="loyal_hist_earn"),
                InlineKeyboardButton("📤 Redeem", callback_data="loyal_hist_redeem"),
                InlineKeyboardButton("📋 All", callback_data="loyal_hist_all"),
            ],
            [InlineKeyboardButton("🔙 Back", callback_data="loyal_back_loyalty")],
        ]
        await loading.edit_text(
            "\n".join(lines),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    except Exception as e:
        logger.error(f"History error: {e}")
        await loading.edit_text("❌ History ရယူ မရပါ")


async def exchange_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_exchange(update, context)


async def show_exchange(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session, account = _get_account(update, context)
    msg_obj = update.message or update.callback_query.message

    if not account or not account.is_logged_in():
        await msg_obj.reply_text("⚠️ Login မဝင်ရသေးပါ။ /start နှိပ်ပါ")
        return

    loading = await msg_obj.reply_text("⏳ Packs ရယူနေသည်...")

    try:
        result = await get_packs(account.phone, account.access_token, account.device_id)
        body = result.get("body", {})
        data = body.get("data") or body or {}

        packs = []
        if isinstance(data, dict):
            packs = data.get("packs") or data.get("items") or data.get("content") or []
        elif isinstance(data, list):
            packs = data

        if not packs:
            await loading.edit_text(
                "🎁 *Exchange Packs*\n\nPacks မရှိပါ",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="loyal_back_loyalty")]
                ])
            )
            return

        # Store packs in session for callback
        pack_map = {}
        buttons = []
        for pack in packs[:10]:
            if not isinstance(pack, dict):
                continue
            code = pack.get("rewardCode") or pack.get("code") or pack.get("packCode") or ""
            name = pack.get("rewardName") or pack.get("name") or pack.get("packName") or code
            pts = pack.get("points") or pack.get("point") or pack.get("requiredPoints") or 0
            if code:
                pack_map[code] = pack
                buttons.append([
                    InlineKeyboardButton(
                        f"🎁 {name} ({pts} pts)",
                        callback_data=f"exchange_{code}"
                    )
                ])

        session.set_pending("packs", pack_map)
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="loyal_back_loyalty")])

        await loading.edit_text(
            "🎁 *Exchange Packs*\nPoints နှင့် လဲလှယ်ရန် Pack ရွေးပါ:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    except Exception as e:
        logger.error(f"Exchange list error: {e}")
        await loading.edit_text("❌ Packs ရယူ မရပါ")


async def extend_points_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await do_extend_points(update, context)


async def do_extend_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session, account = _get_account(update, context)
    msg_obj = update.message or update.callback_query.message

    if not account or not account.is_logged_in():
        await msg_obj.reply_text("⚠️ Login မဝင်ရသေးပါ။ /start နှိပ်ပါ")
        return

    # Confirm dialog
    buttons = [
        [
            InlineKeyboardButton("✅ ဟုတ်ကဲ့ Extend လုပ်မည်", callback_data="loyal_extend_confirm"),
            InlineKeyboardButton("❌ မလုပ်ပါ", callback_data="loyal_back_loyalty"),
        ]
    ]
    await msg_obj.reply_text(
        "⏳ *Points Extend*\n\nPoints ၏ Expiry ကို Extend လုပ်မည်လား?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def handle_loyalty_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "loyal_refresh":
        await show_loyalty(update, context)
    elif data == "loyal_history" or data == "loyal_hist_all":
        await show_points_history(update, context, "all")
    elif data == "loyal_hist_earn":
        await show_points_history(update, context, "earn")
    elif data == "loyal_hist_redeem":
        await show_points_history(update, context, "redeem")
    elif data == "loyal_exchange":
        await show_exchange(update, context)
    elif data == "loyal_extend":
        await do_extend_points(update, context)
    elif data == "loyal_extend_confirm":
        await _do_extend_confirm(update, context)
    elif data in ("loyal_back", "loyal_back_loyalty"):
        await show_loyalty(update, context)


async def _do_extend_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session, account = _get_account(update, context)

    if not account or not account.is_logged_in():
        await query.message.reply_text("⚠️ Login မဝင်ရသေးပါ")
        return

    msg = await query.message.reply_text("⏳ Extending...")
    try:
        result = await extend_points(account.phone, account.access_token)
        body = result.get("body", {})
        status = result.get("status", 0)

        if status in (200, 201):
            await msg.edit_text("✅ Points Extend အောင်မြင်ပါသည်!")
        else:
            err = body.get("message") or body.get("responseMessage") or "မသိသော error"
            await msg.edit_text(f"❌ Extend မအောင်မြင်ပါ: {err}")
    except Exception as e:
        logger.error(f"Extend error: {e}")
        await msg.edit_text("❌ Extend လုပ်မရပါ")


async def handle_exchange_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # Route confirm action
    if data.startswith("exchange_confirm_"):
        await handle_exchange_confirm(update, context)
        return

    reward_code = data.replace("exchange_", "")

    session, account = _get_account(update, context)
    if not account or not account.is_logged_in():
        await query.message.reply_text("⚠️ Login မဝင်ရသေးပါ")
        return

    packs = session.get_pending("packs") or {}
    pack = packs.get(reward_code, {})
    name = pack.get("rewardName") or pack.get("name") or reward_code
    pts = pack.get("points") or pack.get("requiredPoints") or "?"

    # Confirm
    buttons = [
        [
            InlineKeyboardButton(
                f"✅ Confirm Exchange",
                callback_data=f"exchange_confirm_{reward_code}"
            ),
            InlineKeyboardButton("❌ Cancel", callback_data="loyal_exchange"),
        ]
    ]
    await query.message.reply_text(
        f"🎁 *{name}*\n⭐ {pts} Points ကို Exchange လုပ်မည်လား?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def handle_exchange_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    reward_code = query.data.replace("exchange_confirm_", "")

    session, account = _get_account(update, context)
    if not account or not account.is_logged_in():
        return

    msg = await query.message.reply_text("⏳ Exchanging...")
    try:
        result = await exchange_pack(account.phone, reward_code, account.access_token)
        body = result.get("body", {})
        status = result.get("status", 0)

        if status in (200, 201):
            await msg.edit_text(f"✅ Exchange အောင်မြင်ပါသည်! 🎉")
        else:
            err = body.get("message") or body.get("responseMessage") or "မသိသော error"
            await msg.edit_text(f"❌ Exchange မအောင်မြင်ပါ: {err}")
    except Exception as e:
        logger.error(f"Exchange error: {e}")
        await msg.edit_text("❌ Exchange လုပ်မရပါ")
