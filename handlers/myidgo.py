"""
MyID GO Handler - MyIDGoActivity.java ကို Telegram Bot မှာ ပြန်ရေး
Game automation: start → reward → stop loop
"""

import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from api.client import (
    mygov_get_profile, mygov_get_leaderboard,
    mygov_get_reward_history, mygov_game_start,
    mygov_game_reward, mygov_game_stop,
    mygov_access_token_exchange,
)
from session.manager import get_session

logger = logging.getLogger(__name__)


def _get_account(update, context):
    user = update.effective_user
    session = get_session(user.id)
    return session, session.get_current_account()


async def myidgo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_myidgo(update, context)


async def show_myidgo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session, account = _get_account(update, context)
    msg_obj = update.message or update.callback_query.message

    if not account or not account.is_logged_in():
        await msg_obj.reply_text("⚠️ Login မဝင်ရသေးပါ။ /start နှိပ်ပါ")
        return

    # Check if game token exists
    game_token = account.game_token
    if not game_token:
        loading = await msg_obj.reply_text("⏳ MyID GO token ရယူနေသည်...")
        try:
            result = await mygov_access_token_exchange(
                account.access_token, account.phone,
                account.avatar_url, account.full_name
            )
            token = result.get("token") or _extract_token(result.get("body", {}))
            if token:
                session.update_account_field(account.phone, gameToken=token)
                account.game_token = token
                game_token = token
                await loading.edit_text("✅ Game token ရပါပြီ! MyID GO menu:")
            else:
                await loading.edit_text(
                    "❌ Game token ရယူ မရပါ\n"
                    "MyID GO ကို phone app မှ တစ်ကြိမ် login ဝင်ပြီး token ရယူပါ\n"
                    "သို့မဟုတ် game_token ကို manual ထည့်ပါ"
                )
                return
        except Exception as e:
            logger.error(f"MyIDGo token error: {e}")
            await loading.edit_text("❌ Game token ရယူ မရပါ")
            return
    else:
        loading = await msg_obj.reply_text("⏳ MyID GO profile ရယူနေသည်...")

    try:
        profile_result = await mygov_get_profile(game_token)
        profile_body = profile_result.get("body", {})
        profile_data = profile_body.get("data") or profile_body or {}

        player_name = ""
        balance = 0
        turns = 0
        if isinstance(profile_data, dict):
            player_name = (profile_data.get("name") or profile_data.get("username")
                           or profile_data.get("fullName") or account.full_name or "Player")
            balance = profile_data.get("balance") or profile_data.get("amount") or 0
            turns = (profile_data.get("turns") or profile_data.get("remaining_turns")
                     or profile_data.get("availableTurns") or 0)

        text = (
            f"🎮 *MyID GO*\n\n"
            f"👤 Player: *{player_name}*\n"
            f"📱 {account.phone}\n"
            f"💰 Balance: {balance}\n"
            f"🎯 Turns: {turns}\n"
        )

        buttons = [
            [
                InlineKeyboardButton("▶️ Start Game (1x)", callback_data="myidgo_play_1"),
                InlineKeyboardButton("🔁 Auto Play", callback_data="myidgo_auto"),
            ],
            [
                InlineKeyboardButton("🏆 Leaderboard", callback_data="myidgo_leaderboard"),
                InlineKeyboardButton("📋 History", callback_data="myidgo_history"),
            ],
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="myidgo_refresh"),
                InlineKeyboardButton("🏠 Dashboard", callback_data="myidgo_back"),
            ],
        ]
        await loading.edit_text(text, parse_mode="Markdown",
                                reply_markup=InlineKeyboardMarkup(buttons))

    except Exception as e:
        logger.error(f"MyIDGo profile error: {e}")
        await loading.edit_text("❌ MyID GO profile ရယူ မရပါ")


def _extract_token(body: dict) -> str:
    if not isinstance(body, dict):
        return ""
    return (body.get("token") or body.get("access_token")
            or (body.get("data") or {}).get("token", "") if isinstance(body.get("data"), dict) else "")


async def _play_one_round(game_token: str) -> dict:
    """Single game round: start → reward → stop"""
    logs = []
    try:
        start_result = await mygov_game_start(game_token)
        start_body = start_result.get("body", {})
        start_status = start_result.get("status", 0)

        if start_status not in (200, 201):
            msg = start_body.get("message") or start_body.get("error_desc") or "start failed"
            return {"success": False, "log": f"❌ Start failed: {msg}"}

        logs.append("✅ start success")

        # Try level reward (from MyIDGoActivity: "level X success")
        level_data = start_body.get("data") or start_body or {}
        level = level_data.get("level") or level_data.get("currentLevel") or 1
        logs.append(f"📊 level {level}")

        # Get reward
        reward_result = await mygov_game_reward(game_token, slot_index=0)
        reward_body = reward_result.get("body", {})
        reward_status = reward_result.get("status", 0)

        if reward_status in (200, 201):
            reward_data = reward_body.get("data") or reward_body or {}
            if isinstance(reward_data, dict):
                rewards = reward_data.get("rewards") or []
                if rewards:
                    for r in rewards:
                        if isinstance(r, dict):
                            rtype = r.get("reward_type") or r.get("type") or ""
                            rname = r.get("rewardName") or r.get("reward_name") or r.get("name") or ""
                            qty = r.get("quantity") or r.get("amount") or r.get("value") or 0
                            logs.append(f"🎁 {rname} x{qty}" if rname else f"🎁 {rtype} x{qty}")
                else:
                    logs.append("⚠️ no reward info returned for this round")
        else:
            msg = reward_body.get("message") or "reward fetch error"
            logs.append(f"⚠️ Reward: {msg}")

        # Stop game
        await mygov_game_stop(game_token)
        logs.append("🛑 stop success")

        return {"success": True, "log": "\n".join(logs)}

    except Exception as e:
        return {"success": False, "log": f"❌ error: {e}"}


async def handle_myidgo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    session, account = _get_account(update, context)

    if not account or not account.is_logged_in():
        await query.message.reply_text("⚠️ Login မဝင်ရသေးပါ")
        return

    game_token = account.game_token

    if data == "myidgo_refresh":
        await show_myidgo(update, context)

    elif data == "myidgo_back":
        from handlers.dashboard import show_dashboard
        await show_dashboard(update, context)

    elif data == "myidgo_play_1":
        if not game_token:
            await query.message.reply_text("❌ Game token မရှိပါ")
            return
        msg = await query.message.reply_text("🎮 Playing 1 round...")
        result = await _play_one_round(game_token)
        await msg.edit_text(
            f"🎮 *Round Result*\n\n{result['log']}",
            parse_mode="Markdown"
        )

    elif data == "myidgo_auto":
        if not game_token:
            await query.message.reply_text("❌ Game token မရှိပါ")
            return
        # Ask how many rounds
        buttons = [
            [
                InlineKeyboardButton("5x", callback_data="myidgo_auto_5"),
                InlineKeyboardButton("10x", callback_data="myidgo_auto_10"),
                InlineKeyboardButton("20x", callback_data="myidgo_auto_20"),
            ],
            [InlineKeyboardButton("❌ Cancel", callback_data="myidgo_refresh")],
        ]
        await query.message.reply_text(
            "🔁 *Auto Play*\nRound အရေအတွက် ရွေးပါ:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    elif data.startswith("myidgo_auto_"):
        rounds = int(data.replace("myidgo_auto_", ""))
        if not game_token:
            await query.message.reply_text("❌ Game token မရှိပါ")
            return
        msg = await query.message.reply_text(f"🔁 Auto playing {rounds} rounds...\n")
        all_logs = []
        success_count = 0
        for i in range(1, rounds + 1):
            result = await _play_one_round(game_token)
            if result["success"]:
                success_count += 1
            all_logs.append(f"*Round {i}/{rounds}*\n{result['log']}")
            # Update progress every 5 rounds
            if i % 5 == 0 or i == rounds:
                await msg.edit_text(
                    f"🔁 Auto Play Progress: {i}/{rounds}\n"
                    f"✅ Success: {success_count}\n\n"
                    + "\n\n".join(all_logs[-3:]),  # Show last 3 round logs
                    parse_mode="Markdown"
                )
            await asyncio.sleep(1)  # 1 second between rounds

        await query.message.reply_text(
            f"🏁 *Auto Play ပြီးပါပြီ!*\n\n"
            f"✅ {success_count}/{rounds} rounds အောင်မြင်ပါသည်",
            parse_mode="Markdown"
        )

    elif data == "myidgo_leaderboard":
        if not game_token:
            await query.message.reply_text("❌ Game token မရှိပါ")
            return
        msg = await query.message.reply_text("⏳ Leaderboard ရယူနေသည်...")
        try:
            result = await mygov_get_leaderboard(game_token)
            body = result.get("body", {})
            data_list = body.get("data") or body or []

            if isinstance(data_list, dict):
                data_list = data_list.get("items") or data_list.get("leaderboard") or []

            if not data_list:
                await msg.edit_text("🏆 Leaderboard data မရှိပါ")
                return

            lines = ["🏆 *Leaderboard*\n"]
            for i, entry in enumerate(data_list[:10], 1):
                if isinstance(entry, dict):
                    name = entry.get("name") or entry.get("playerName") or f"Player{i}"
                    score = entry.get("score") or entry.get("totalScore") or 0
                    lines.append(f"{i}. {name} — {score:,}")
            await msg.edit_text("\n".join(lines), parse_mode="Markdown")
        except Exception as e:
            await msg.edit_text(f"❌ Leaderboard ရယူ မရပါ: {e}")

    elif data == "myidgo_history":
        if not game_token:
            await query.message.reply_text("❌ Game token မရှိပါ")
            return
        msg = await query.message.reply_text("⏳ History ရယူနေသည်...")
        try:
            result = await mygov_get_reward_history(game_token)
            body = result.get("body", {})
            items = body.get("data") or body or []

            if isinstance(items, dict):
                items = items.get("items") or items.get("history") or []

            if not items:
                await msg.edit_text("📋 History မရှိပါ")
                return

            lines = ["📋 *Reward History*\n"]
            for item in items[:15]:
                if isinstance(item, dict):
                    date = str(item.get("created_at") or item.get("date") or "")[:16]
                    rtype = item.get("reward_type") or item.get("type") or ""
                    rname = item.get("reward_name") or item.get("rewardName") or item.get("name") or rtype
                    qty = item.get("quantity") or item.get("amount") or ""
                    lines.append(f"• {date} | {rname} {qty}")
            await msg.edit_text("\n".join(lines), parse_mode="Markdown")
        except Exception as e:
            await msg.edit_text(f"❌ History ရယူ မရပါ: {e}")
