"""
Daily Quest Handler - DailyClaimActivity + Daily Quest screens ကို ပြန်ရေး
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from api.client import (
    get_daily_quest_main, post_daily_quest_claim, get_mini_quest_claim
)
from session.manager import get_session

logger = logging.getLogger(__name__)


def _get_account(update, context):
    user = update.effective_user
    session = get_session(user.id)
    return session, session.get_current_account()


async def daily_quest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_daily_quest(update, context)


async def show_daily_quest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session, account = _get_account(update, context)
    msg_obj = update.message or update.callback_query.message

    if not account or not account.is_logged_in():
        await msg_obj.reply_text("⚠️ Login မဝင်ရသေးပါ။ /start နှိပ်ပါ")
        return

    loading = await msg_obj.reply_text("⏳ Daily Quest ရယူနေသည်...")

    try:
        result = await get_daily_quest_main(account.phone, account.access_token)
        body = result.get("body", {})
        data = body.get("data") or body or {}

        if not isinstance(data, dict):
            await loading.edit_text("❌ Daily Quest data ရရှိမှု မအောင်မြင်ပါ")
            return

        # Daily claim status
        daily = data.get("dailyQuest") or data.get("daily") or {}
        daily_claimed = False
        daily_reward = ""
        daily_claimable = False
        if isinstance(daily, dict):
            daily_claimed = bool(daily.get("isClaimed") or daily.get("claimed"))
            daily_claimable = bool(daily.get("isClaimable") or daily.get("claimable")
                                   or not daily_claimed)
            rw = daily.get("reward") or {}
            if isinstance(rw, dict):
                daily_reward = f"{rw.get('name', '')} {rw.get('value', '')}"

        # Mini quests
        mini_quests = data.get("miniQuests") or data.get("quests") or []
        mini_lines = []
        claimable_minis = []
        if isinstance(mini_quests, list):
            for q in mini_quests:
                if not isinstance(q, dict):
                    continue
                name = q.get("name") or q.get("questName") or ""
                is_done = bool(q.get("isDone") or q.get("done") or q.get("isCompleted"))
                is_claimed = bool(q.get("isClaimed") or q.get("claimed"))
                claim_url = q.get("claimUrl") or q.get("url") or ""
                status = "✅" if is_claimed else ("🟡" if is_done else "⬜")
                mini_lines.append(f"{status} {name}")
                if is_done and not is_claimed and claim_url:
                    claimable_minis.append({"name": name, "url": claim_url})

        session.set_pending("claimable_minis", claimable_minis)

        daily_status = "✅ Claimed" if daily_claimed else ("🟢 Claimable!" if daily_claimable else "⬜ Not ready")
        mini_text = "\n".join(mini_lines[:10]) if mini_lines else "_(Quest မရှိပါ)_"

        text = (
            f"🏆 *Daily Quest*\n\n"
            f"📱 {account.phone}\n\n"
            f"📅 *Daily Claim*: {daily_status}\n"
            + (f"🎁 Reward: {daily_reward}\n" if daily_reward else "")
            + f"\n📋 *Mini Quests*:\n{mini_text}"
        )

        buttons = []
        if not daily_claimed and daily_claimable:
            buttons.append([InlineKeyboardButton("🎁 Claim Daily Reward!", callback_data="dq_claim_daily")])
        if claimable_minis:
            buttons.append([InlineKeyboardButton(
                f"🎯 Claim Mini Quests ({len(claimable_minis)})",
                callback_data="dq_claim_mini_all"
            )])
        buttons.append([
            InlineKeyboardButton("🔄 Refresh", callback_data="dq_refresh"),
            InlineKeyboardButton("🏠 Dashboard", callback_data="dq_back"),
        ])

        await loading.edit_text(text, parse_mode="Markdown",
                                reply_markup=InlineKeyboardMarkup(buttons))

    except Exception as e:
        logger.error(f"Daily quest error: {e}")
        await loading.edit_text("❌ Daily Quest ရယူ မရပါ")


async def daily_claim_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session, account = _get_account(update, context)
    msg_obj = update.message

    if not account or not account.is_logged_in():
        await msg_obj.reply_text("⚠️ Login မဝင်ရသေးပါ။ /start နှိပ်ပါ")
        return

    msg = await msg_obj.reply_text("⏳ Daily reward claim လုပ်နေသည်...")
    await _do_daily_claim(msg, account)


async def _do_daily_claim(msg_obj, account):
    try:
        result = await post_daily_quest_claim(account.phone, account.access_token)
        body = result.get("body", {})
        status = result.get("status", 0)

        if status in (200, 201):
            data = body.get("data") or body or {}
            reward_text = ""
            if isinstance(data, dict):
                reward = data.get("reward") or {}
                if isinstance(reward, dict):
                    reward_text = f"\n🎁 {reward.get('name', '')} {reward.get('value', '')}"
            await msg_obj.edit_text(
                f"✅ *Daily Claim အောင်မြင်ပါသည်!*" + reward_text,
                parse_mode="Markdown"
            )
        else:
            err = body.get("message") or body.get("responseMessage") or "မသိသော error"
            await msg_obj.edit_text(f"❌ Daily Claim မအောင်မြင်ပါ: {err}")
    except Exception as e:
        logger.error(f"Daily claim error: {e}")
        await msg_obj.edit_text("❌ Daily Claim လုပ်မရပါ")


async def handle_daily_quest_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    session, account = _get_account(update, context)

    if not account or not account.is_logged_in():
        await query.message.reply_text("⚠️ Login မဝင်ရသေးပါ")
        return

    if data == "dq_refresh":
        await show_daily_quest(update, context)

    elif data == "dq_back":
        from handlers.dashboard import show_dashboard
        await show_dashboard(update, context)

    elif data == "dq_claim_daily":
        msg = await query.message.reply_text("⏳ Daily reward claim လုပ်နေသည်...")
        await _do_daily_claim(msg, account)

    elif data == "dq_claim_mini_all":
        claimable = session.get_pending("claimable_minis") or []
        if not claimable:
            await query.message.reply_text("🎯 Claimable mini quests မရှိပါ")
            return

        msg = await query.message.reply_text(
            f"⏳ Mini quests {len(claimable)} ခု claim လုပ်နေသည်..."
        )
        results = []
        for q in claimable:
            try:
                # Replace {msisdn} placeholder with actual phone
                url = q["url"].replace("{msisdn}", account.phone)
                res = await get_mini_quest_claim(url, account.access_token)
                status = res.get("status", 0)
                if status in (200, 201):
                    results.append(f"✅ {q['name']}")
                else:
                    body = res.get("body", {})
                    err = body.get("message") or "error"
                    results.append(f"❌ {q['name']}: {err}")
            except Exception as e:
                results.append(f"❌ {q['name']}: {e}")

        await msg.edit_text(
            "🎯 *Mini Quest Claim Results*\n\n" + "\n".join(results),
            parse_mode="Markdown"
        )
