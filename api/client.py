"""
API Client - ZenoMyID App's ApiClient.java ကို တိတိကျကျ Python မှာ ပြန်ရေးထားသည်
Base URL: https://apis.mytel.com.mm
"""

import aiohttp
import asyncio
import time
import uuid
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

BASE_URL = "https://apis.mytel.com.mm"
QUEST_BASE = "https://apis.mytel.com.mm/daily-quest-v3/api/v3/daily-quest"
MYGOV_BASE = "https://pubapi-mygov2.mtgmm.co/v1/engine"

DEFAULT_HEADERS = {
    "user-agent": "okhttp/4.12.0",
    "accept-language": "my",
}

STANDARD_HEADERS = {
    "user-agent": "okhttp/4.12.0",
    "version": "2.0.16",
    "revision": "300",
    "client_type": "1",
    "local_code": "95",
    "language_code": "en",
    "country_code": "MM",
}

TIMEOUT = aiohttp.ClientTimeout(total=30, connect=30)


def _fmt_phone_plus95(phone: str) -> str:
    """Convert 09xxxxxxxx -> +95xxxxxxxxx"""
    p = phone.strip()
    if p.startswith("0"):
        p = p[1:]
    return f"+95{p}"


def _fmt_phone_pct(phone: str) -> str:
    """Convert 09xxxxxxxx -> %2B95xxxxxxxxx (URL encoded)"""
    p = phone.strip()
    if p.startswith("0"):
        p = p[1:]
    return f"%2B95{p}"


def _fmt_phone_bare(phone: str) -> str:
    """Convert 09xxxxxxxx -> 9xxxxxxxxx (no leading 0)"""
    p = phone.strip()
    if p.startswith("0"):
        p = p[1:]
    return p


def _make_session() -> aiohttp.ClientSession:
    connector = aiohttp.TCPConnector(ssl=False)
    return aiohttp.ClientSession(connector=connector, timeout=TIMEOUT)


async def check_account(phone: str) -> Dict[str, Any]:
    """Check if phone number has MyID account"""
    url = f"{BASE_URL}/myid/authen/v1.0/v2/login/action/check-account?phoneNumber={phone}"
    headers = {
        "accept-language": "en",
        "user-agent": "okhttp/4.12.0",
    }
    async with _make_session() as session:
        async with session.get(url, headers=headers) as resp:
            return {"status": resp.status, "body": await resp.json(content_type=None)}


async def get_otp(phone: str) -> Dict[str, Any]:
    """Request OTP for phone number"""
    url = f"{BASE_URL}/myid/authen/v1.0/login/method/otp/get-otp?phoneNumber={phone}"
    headers = {
        "accept-language": "my",
        "user-agent": "okhttp/4.12.0",
    }
    async with _make_session() as session:
        async with session.get(url, headers=headers) as resp:
            return {"status": resp.status, "body": await resp.json(content_type=None)}


async def register_request(phone: str) -> Dict[str, Any]:
    """Register new MyID account request"""
    url = f"{BASE_URL}/myid/authen/v1.0/v2/register/request"
    payload = {"msisdn": phone}
    headers = {
        "accept-language": "my",
        "content-type": "application/json; charset=UTF-8",
        "user-agent": "okhttp/4.12.0",
    }
    async with _make_session() as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            return {"status": resp.status, "body": await resp.json(content_type=None)}


async def validate_otp(phone: str, otp: str, device_id: str) -> Dict[str, Any]:
    """Validate OTP and get access token"""
    url = f"{BASE_URL}/myid/authen/v1.0/login/method/otp/validate-otp"
    payload = {
        "appVersion": "2.0.16",
        "buildVersionApp": "300",
        "deviceId": device_id,
        "imei": device_id,
        "os": "ANDROID Redmi Redmi K30 5G",
        "osApp": "ANDROID",
        "password": otp,
        "phoneNumber": phone,
        "version": "12",
    }
    headers = {
        "accept-language": "en",
        "user-agent": "okhttp/4.12.0",
        "content-type": "application/json; charset=UTF-8",
    }
    async with _make_session() as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            return {"status": resp.status, "body": await resp.json(content_type=None)}


async def get_customer(access_token: str) -> Dict[str, Any]:
    """Get customer profile data"""
    url = f"{BASE_URL}/cpm/v1.0/api/customer"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "user-agent": "okhttp/4.12.0",
    }
    async with _make_session() as session:
        async with session.get(url, headers=headers) as resp:
            return {"status": resp.status, "body": await resp.json(content_type=None)}


async def update_customer(
    access_token: str,
    birth_date: Optional[str] = None,
    gender: Optional[str] = None,
    full_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Update customer profile"""
    url = f"{BASE_URL}/cpm/v1.0/api/customer"
    payload = {
        "birthDate": birth_date or "",
        "gender": gender or "male",
        "fullName": full_name or "",
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "*/*",
        "user-agent": "MyID/17232 CFNetwork/3860.700.1 Darwin/25.6.0",
    }
    async with _make_session() as session:
        async with session.put(url, json=payload, headers=headers) as resp:
            return {"status": resp.status, "body": await resp.json(content_type=None)}


async def get_loyalty_inquiry(
    phone: str, access_token: str, device_id: str
) -> Dict[str, Any]:
    """Get loyalty points inquiry"""
    bare_phone = _fmt_phone_bare(phone)
    url = f"{BASE_URL}/loyalty/api/v3.1/customer/inquiry?phoneNo={bare_phone}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "device_id": device_id,
        "client_type": "1",
        "local_code": "95",
        "version": "2.0.16",
        "revision": "300",
        "session_token": "",
        "language_code": "en",
        "country_code": "VN",
        "user_id": "0",
        "Accept-Language": "EN",
        "msisdn": "",
        "user-agent": "Dalvik/2.1.0 (Linux; U; Android 12; Redmi K30 5G Build/SKQ1.211006.001)",
    }
    async with _make_session() as session:
        async with session.get(url, headers=headers) as resp:
            return {"status": resp.status, "body": await resp.json(content_type=None)}


async def get_loyalty_csm(
    access_token: str, device_id: str
) -> Dict[str, Any]:
    """Get loyalty CSM data"""
    url = f"{BASE_URL}/csm/v1.0/api/loyalty"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "session_token": "",
        "device_id": device_id,
        "client_type": "1",
        "local_code": "95",
        "version": "2.0.16",
        "revision": "300",
        "language_code": "en",
        "country_code": "VN",
        "user_id": "0",
        "msisdn": "",
        "user-agent": "Dalvik/2.1.0 (Linux; U; Android 12; Redmi K30 5G Build/SKQ1.211006.001)",
    }
    async with _make_session() as session:
        async with session.get(url, headers=headers) as resp:
            return {"status": resp.status, "body": await resp.json(content_type=None)}


async def get_points_history(
    phone: str, history_type: str, access_token: str, device_id: str
) -> Dict[str, Any]:
    """Get loyalty points history"""
    pct_phone = _fmt_phone_pct(phone)
    url = (
        f"{BASE_URL}/loyalty/api/v3.1/history"
        f"?phoneNo={pct_phone}&type={history_type}&page=0&size=50"
    )
    plus_phone = _fmt_phone_plus95(phone)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "device_id": device_id,
        "client_type": "1",
        "local_code": "95",
        "version": "2.0.16",
        "revision": "300",
        "language_code": "my",
        "country_code": "MM",
        "msisdn": plus_phone,
        "user-agent": "okhttp/4.12.0",
    }
    async with _make_session() as session:
        async with session.get(url, headers=headers) as resp:
            return {"status": resp.status, "body": await resp.json(content_type=None)}


async def get_packs(
    phone: str, access_token: str, device_id: str
) -> Dict[str, Any]:
    """Get available loyalty packs for exchange"""
    bare_phone = _fmt_phone_bare(phone)
    url = f"{BASE_URL}/loyalty/api/v3.1/pack?phoneNo={bare_phone}"
    plus_phone = _fmt_phone_plus95(phone)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "device_id": device_id,
        "client_type": "1",
        "local_code": "95",
        "version": "2.0.16",
        "revision": "300",
        "language_code": "en",
        "country_code": "MM",
        "msisdn": plus_phone,
        "user-agent": "okhttp/4.12.0",
    }
    async with _make_session() as session:
        async with session.get(url, headers=headers) as resp:
            return {"status": resp.status, "body": await resp.json(content_type=None)}


async def exchange_pack(
    phone: str,
    reward_code: str,
    access_token: str,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Exchange loyalty points for a pack"""
    if not request_id:
        request_id = str(uuid.uuid4())
    plus_phone = _fmt_phone_plus95(phone)
    request_time = int(time.time() * 1000)
    payload = {
        "requestId": request_id,
        "requestTime": request_time,
        "msisdn": plus_phone,
        "rewardCode": reward_code,
    }
    url = f"{BASE_URL}/loyalty/api/v3.1/pack/exchange"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "accept-language": "EN",
        "content-type": "application/json; charset=utf-8",
        "user-agent": "okhttp/4.12.0",
    }
    async with _make_session() as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            return {"status": resp.status, "body": await resp.json(content_type=None)}


async def extend_points(
    phone: str,
    access_token: str,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Extend loyalty points expiry"""
    if not request_id:
        request_id = str(uuid.uuid4())
    request_time = int(time.time() * 1000)
    payload = {
        "requestTime": str(request_time),
        "msisdn": phone,
        "requestId": request_id,
    }
    url = f"{BASE_URL}/loyalty/api/v3.1/exchanged/extend"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept-Language": "my",
        "content-type": "application/json",
        "user-agent": "okhttp/4.12.0",
    }
    async with _make_session() as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            return {"status": resp.status, "body": await resp.json(content_type=None)}


async def get_account_detail(
    phone: str, access_token: str, device_id: str
) -> Dict[str, Any]:
    """Get detailed account info"""
    pct_phone = _fmt_phone_pct(phone)
    url = (
        f"{BASE_URL}/account-detail/api/v1.2/individual/account-main"
        f"?isdn={pct_phone}&language=en"
    )
    plus_phone = _fmt_phone_plus95(phone)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "device_id": device_id,
        "client_type": "1",
        "local_code": "95",
        "msisdn": plus_phone,
        "version": "2.0.16",
        "revision": "300",
        "language_code": "en",
        "country_code": "MM",
        "user-agent": "okhttp/4.12.0",
    }
    async with _make_session() as session:
        async with session.get(url, headers=headers) as resp:
            return {"status": resp.status, "body": await resp.json(content_type=None)}


async def get_vas_packages(
    phone: str, access_token: str, device_id: str
) -> Dict[str, Any]:
    """Get VAS (data) packages"""
    pct_phone = _fmt_phone_pct(phone)
    url = (
        f"{BASE_URL}/csm/v1.0/api/vas-package/special-packs"
        f"?msisdn={pct_phone}&language=en"
    )
    plus_phone = _fmt_phone_plus95(phone)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "device_id": device_id,
        "client_type": "1",
        "local_code": "95",
        "version": "2.0.16",
        "revision": "300",
        "language_code": "en",
        "country_code": "MM",
        "msisdn": plus_phone,
        "user-agent": "okhttp/4.12.0",
    }
    async with _make_session() as session:
        async with session.get(url, headers=headers) as resp:
            return {"status": resp.status, "body": await resp.json(content_type=None)}


async def get_vas_package_detail(
    pack_id: str, phone: str, access_token: str, device_id: str
) -> Dict[str, Any]:
    """Get VAS package detail"""
    pct_phone = _fmt_phone_pct(phone)
    url = (
        f"{BASE_URL}/csm/v1.0/api/vas-package/{pack_id}"
        f"?msisdn={pct_phone}&language=mu"
    )
    plus_phone = _fmt_phone_plus95(phone)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "device_id": device_id,
        "client_type": "1",
        "local_code": "95",
        "version": "2.0.16",
        "revision": "300",
        "language_code": "my",
        "languageCode": "my",
        "accept-language": "my",
        "Accept-Language": "my",
        "country_code": "MM",
        "msisdn": plus_phone,
        "user-agent": "okhttp/4.12.0",
    }
    async with _make_session() as session:
        async with session.get(url, headers=headers) as resp:
            return {"status": resp.status, "body": await resp.json(content_type=None)}


async def register_vas_package(
    pack_id: str, phone: str, access_token: str
) -> Dict[str, Any]:
    """Register (buy) a VAS package"""
    plus_phone = _fmt_phone_plus95(phone)
    url = f"{BASE_URL}/csm/v1.0/api/vas-package/{pack_id}/register"
    payload = {"msisdn": plus_phone, "isRenew": False}
    headers = {
        "Authorization": f"Bearer {access_token}",
        "content-type": "application/json; charset=utf-8",
        "user-agent": "okhttp/4.12.0",
    }
    async with _make_session() as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            return {"status": resp.status, "body": await resp.json(content_type=None)}


async def get_daily_quest_main(phone: str, access_token: str) -> Dict[str, Any]:
    """Get Daily Quest main screen data"""
    bare_phone = _fmt_phone_bare(phone)
    url = (
        f"{QUEST_BASE}/main-screen"
        f"?clientType=Android&Platform=myid&msisdn={bare_phone}&revision=16300"
    )
    headers = {
        "Authorization": f"Bearer {access_token}",
        "country_code": "MM",
        "countryCode": "MM",
        "language_code": "my",
        "languageCode": "my",
        "accept-language": "my",
        "Accept-Language": "my",
        "countrycode": "MM",
        "languagecode": "my",
        "user-agent": "okhttp/4.12.0",
    }
    async with _make_session() as session:
        async with session.get(url, headers=headers) as resp:
            return {"status": resp.status, "body": await resp.json(content_type=None)}


async def post_daily_quest_claim(phone: str, access_token: str) -> Dict[str, Any]:
    """Claim daily quest reward"""
    pct_phone = phone.replace("%2B", "+")
    bare = pct_phone.lstrip("0+95")
    msisdn_full = f"+95{bare}" if not pct_phone.startswith("+") else pct_phone
    # Use the format: {"msisdn":"+959xxxxxxxx","platform":"myid","clientType":"Android","revision":16300}
    url = f"{QUEST_BASE}/daily-claim"
    payload = {
        "msisdn": msisdn_full,
        "platform": "myid",
        "clientType": "Android",
        "revision": 16300,
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
        "country_code": "MM",
        "countryCode": "MM",
        "language_code": "my",
        "languageCode": "my",
        "accept-language": "my",
        "Accept-Language": "my",
        "countrycode": "MM",
        "languagecode": "my",
        "content-type": "application/json",
        "user-agent": "okhttp/4.12.0",
    }
    async with _make_session() as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            return {"status": resp.status, "body": await resp.json(content_type=None)}


async def get_mini_quest_claim(url: str, access_token: str) -> Dict[str, Any]:
    """Claim mini quest reward (URL with {msisdn} replaced)"""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "country_code": "MM",
        "countryCode": "MM",
        "language_code": "my",
        "languageCode": "my",
        "accept-language": "my",
        "Accept-Language": "my",
        "countrycode": "MM",
        "languagecode": "my",
        "user-agent": "okhttp/4.12.0",
    }
    async with _make_session() as session:
        async with session.get(url, headers=headers) as resp:
            return {"status": resp.status, "body": await resp.json(content_type=None)}


# ── MyID GO (mygov2 game engine) ────────────────────────────────────────────

async def mygov_get_profile(game_token: str) -> Dict[str, Any]:
    """Get MyIDGo player profile"""
    url = f"{MYGOV_BASE}/user/profile"
    headers = {
        "Authorization": f"Bearer {game_token}",
        "Accept": "application/json",
        "User-Agent": "MyID/1.0.300 (Android)",
    }
    async with _make_session() as session:
        async with session.get(url, headers=headers) as resp:
            return {"status": resp.status, "body": await resp.json(content_type=None)}


async def mygov_get_leaderboard(game_token: str) -> Dict[str, Any]:
    """Get MyIDGo current leaderboard"""
    url = f"{MYGOV_BASE}/game/leaderboard/current"
    headers = {
        "Authorization": f"Bearer {game_token}",
        "Accept": "application/json",
        "User-Agent": "MyID/1.0.300 (Android)",
    }
    async with _make_session() as session:
        async with session.get(url, headers=headers) as resp:
            return {"status": resp.status, "body": await resp.json(content_type=None)}


async def mygov_get_reward_history(game_token: str) -> Dict[str, Any]:
    """Get MyIDGo reward history"""
    url = f"{MYGOV_BASE}/game/reward/history?limit=30"
    headers = {
        "Authorization": f"Bearer {game_token}",
        "Accept": "application/json",
        "User-Agent": "MyID/1.0.300 (Android)",
    }
    async with _make_session() as session:
        async with session.get(url, headers=headers) as resp:
            return {"status": resp.status, "body": await resp.json(content_type=None)}


async def mygov_game_start(game_token: str) -> Dict[str, Any]:
    """Start a MyIDGo game round"""
    url = f"{MYGOV_BASE}/game/start"
    headers = {
        "Authorization": f"Bearer {game_token}",
        "Accept": "application/json",
        "content-type": "application/json",
        "User-Agent": "MyID/1.0.300 (Android)",
    }
    async with _make_session() as session:
        async with session.post(url, json={}, headers=headers) as resp:
            return {"status": resp.status, "body": await resp.json(content_type=None)}


async def mygov_game_reward(game_token: str, slot_index: int = 0) -> Dict[str, Any]:
    """Get reward for a game round slot"""
    url = f"{MYGOV_BASE}/game/reward?slot_index={slot_index}"
    headers = {
        "Authorization": f"Bearer {game_token}",
        "Accept": "application/json",
        "content-type": "application/json",
        "User-Agent": "MyID/1.0.300 (Android)",
    }
    async with _make_session() as session:
        async with session.post(url, json={}, headers=headers) as resp:
            return {"status": resp.status, "body": await resp.json(content_type=None)}


async def mygov_game_stop(game_token: str) -> Dict[str, Any]:
    """Stop MyIDGo game session"""
    url = f"{MYGOV_BASE}/game/stop"
    headers = {
        "Authorization": f"Bearer {game_token}",
        "Accept": "application/json",
        "content-type": "application/json",
        "User-Agent": "MyID/1.0.300 (Android)",
    }
    async with _make_session() as session:
        async with session.post(url, json={}, headers=headers) as resp:
            return {"status": resp.status, "body": await resp.json(content_type=None)}


async def mygov_access_token_exchange(
    access_token: str,
    phone: str,
    avatar_url: str = "",
    fullname: str = "",
) -> Dict[str, Any]:
    """Exchange MyID access token for MyIDGo game token via bootstrap"""
    plus_phone = _fmt_phone_plus95(phone)
    url = f"{MYGOV_BASE}/game/start"  # redirects handled by game engine
    # The app uses bootstrap.html then captures the Location redirect with access-token header
    # We replicate that by hitting the profile endpoint with access-token header
    profile_url = f"{MYGOV_BASE}/user/profile"
    headers = {
        "access-token": access_token,
        "phone-number": plus_phone,
        "avatar": avatar_url,
        "fullname": fullname,
        "Accept": "text/html,application/json",
        "User-Agent": "MyID/1.0.300 (Android)",
    }
    async with _make_session() as session:
        async with session.get(profile_url, headers=headers) as resp:
            body = await resp.json(content_type=None)
            # Extract token from body
            token = None
            if isinstance(body, dict):
                token = (
                    body.get("token")
                    or body.get("access_token")
                    or body.get("data", {}).get("token") if isinstance(body.get("data"), dict) else None
                )
            return {"status": resp.status, "body": body, "token": token}
