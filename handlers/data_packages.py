"""
Data Packages Handler - DataPackagesActivity ကို ပြန်ရေး
VAS packages: list, detail, register
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from api.client import get_vas_packages, get_vas_package_detail, register_vas_package
from session.manager import get_session

logger = logging.getLogger(__name__)


def _get_account(update, context):
    user = update.effective_user
    session = get_session(user.id)
    return session, session.get_current_account()


async def data_packages_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_data_packages(update, context)


async def show_data_packages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session, account = _get_account(update, context)
    msg_obj = update.message or update.callback_query.message

    if not account or not account.is_logged_in():
        await msg_obj.reply_text("⚠️ Login မဝင်ရသေးပါ။ /start နှိပ်ပါ")
        return

    loading = await msg_obj.reply_text("⏳ Data packages ရယူနေသည်...")

    try:
        result = await get_vas_packages(account.phone, account.access_token, account.device_id)
        body = result.get("body", {})
        data = body.get("data") or body or {}

        packs = []
        if isinstance(data, dict):
            packs = data.get("packages") or data.get("items") or data.get("content") or []
        elif isinstance(data, list):
            packs = data

        if not packs:
            await loading.edit_text(
                "📦 *Data Packages*\n\nPackages မရှိပါ",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Refresh", callback_data="data_refresh")],
                    [InlineKeyboardButton("🏠 Dashboard", callback_data="data_back")],
                ])
            )
            return

        # Store pack IDs in session
        pack_map = {}
        buttons = []
        for pack in packs[:12]:
            if not isinstance(pack, dict):
                continue
            pack_id = pack.get("packageId") or pack.get("id") or pack.get("code") or ""
            name = pack.get("packageName") or pack.get("name") or pack_id
            price = pack.get("price") or pack.get("fee") or ""
            validity = pack.get("validity") or pack.get("duration") or ""
            data_size = pack.get("dataSize") or pack.get("quota") or pack.get("data") or ""

            if pack_id:
                pack_map[pack_id] = pack
                label = f"📦 {name}"
                if price:
                    label += f" ({price} Ks)"
                buttons.append([InlineKeyboardButton(label, callback_data=f"data_detail_{pack_id}")])

        session.set_pending("data_packs", pack_map)
        buttons.append([
            InlineKeyboardButton("🔄 Refresh", callback_data="data_refresh"),
            InlineKeyboardButton("🏠 Dashboard", callback_data="data_back"),
        ])

        await loading.edit_text(
            f"📦 *Data Packages*\n📱 {account.phone}\n\nPackage ရွေးပါ:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    except Exception as e:
        logger.error(f"Data packages error: {e}")
        await loading.edit_text("❌ Data packages ရယူ မရပါ")


async def handle_data_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    session, account = _get_account(update, context)

    if not account or not account.is_logged_in():
        await query.message.reply_text("⚠️ Login မဝင်ရသေးပါ")
        return

    if data == "data_refresh":
        await show_data_packages(update, context)

    elif data == "data_back":
        from handlers.dashboard import show_dashboard
        await show_dashboard(update, context)

    elif data.startswith("data_detail_"):
        pack_id = data.replace("data_detail_", "")
        await show_pack_detail(update, context, pack_id)

    elif data.startswith("data_buy_"):
        pack_id = data.replace("data_buy_", "")
        await do_register_package(update, context, pack_id)

    elif data.startswith("data_confirm_"):
        pack_id = data.replace("data_confirm_", "")
        await do_register_confirm(update, context, pack_id)


async def show_pack_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, pack_id: str):
    query = update.callback_query
    session, account = _get_account(update, context)

    msg = await query.message.reply_text("⏳ Package detail ရယူနေသည်...")

    try:
        result = await get_vas_package_detail(
            pack_id, account.phone, account.access_token, account.device_id
        )
        body = result.get("body", {})
        data = body.get("data") or body or {}

        if not isinstance(data, dict):
            await msg.edit_text("❌ Package detail ရရှိမှု မအောင်မြင်ပါ")
            return

        name = data.get("packageName") or data.get("name") or pack_id
        price = data.get("price") or data.get("fee") or "N/A"
        validity = data.get("validity") or data.get("duration") or "N/A"
        data_size = data.get("dataSize") or data.get("quota") or data.get("data") or "N/A"
        desc = data.get("description") or data.get("detail") or ""

        text = (
            f"📦 *{name}*\n\n"
            f"💵 Price: {price} Ks\n"
            f"📅 Validity: {validity}\n"
            f"📶 Data: {data_size}\n"
            + (f"\n📝 {desc}" if desc else "")
        )

        buttons = [
            [InlineKeyboardButton(f"✅ Buy - {price} Ks", callback_data=f"data_confirm_{pack_id}")],
            [InlineKeyboardButton("🔙 Back to List", callback_data="data_refresh")],
        ]
        await msg.edit_text(text, parse_mode="Markdown",
                            reply_markup=InlineKeyboardMarkup(buttons))

    except Exception as e:
        logger.error(f"Pack detail error: {e}")
        await msg.edit_text("❌ Package detail ရယူ မရပါ")


async def do_register_package(update: Update, context: ContextTypes.DEFAULT_TYPE, pack_id: str):
    query = update.callback_query
    session, account = _get_account(update, context)
    pack_map = session.get_pending("data_packs") or {}
    pack = pack_map.get(pack_id, {})
    name = pack.get("packageName") or pack.get("name") or pack_id
    price = pack.get("price") or pack.get("fee") or "?"

    buttons = [
        [
            InlineKeyboardButton("✅ Confirm Buy", callback_data=f"data_confirm_{pack_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data="data_refresh"),
        ]
    ]
    await query.message.reply_text(
        f"📦 *{name}* - {price} Ks\nဝယ်ယူမည်လား?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def do_register_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, pack_id: str):
    query = update.callback_query
    session, account = _get_account(update, context)

    msg = await query.message.reply_text("⏳ Package ဝယ်ယူနေသည်...")
    try:
        result = await register_vas_package(pack_id, account.phone, account.access_token)
        body = result.get("body", {})
        status = result.get("status", 0)

        if status in (200, 201):
            await msg.edit_text("✅ Package ဝယ်ယူမှု အောင်မြင်ပါသည်! 🎉")
        else:
            err = body.get("message") or body.get("responseMessage") or "မသိသော error"
            await msg.edit_text(f"❌ ဝယ်ယူမှု မအောင်မြင်ပါ: {err}")
    except Exception as e:
        logger.error(f"Register package error: {e}")
        await msg.edit_text("❌ Package ဝယ်ယူ မရပါ")
