"""
Session Manager - Android SessionManager.java + AccountManager.java ကို Python မှာ ပြန်ရေး
Multi-account support ပါဝင်သည်
"""

import json
import os
import uuid
import logging
from typing import Optional, Dict, List, Any
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

SESSIONS_FILE = DATA_DIR / "sessions.json"


def _load_all() -> Dict[str, Any]:
    """Load all user data from file"""
    if SESSIONS_FILE.exists():
        try:
            with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Session load error: {e}")
    return {}


def _save_all(data: Dict[str, Any]) -> None:
    """Save all user data to file"""
    try:
        with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Session save error: {e}")


def _user_key(telegram_id: int) -> str:
    return str(telegram_id)


# ── Account Model ─────────────────────────────────────────────────────────────

class Account:
    """Mirrors AccountManager$Account.java fields exactly"""
    def __init__(self, data: Dict[str, Any] = None):
        d = data or {}
        self.phone: str = d.get("phone", "")
        self.full_name: str = d.get("fullName", "")
        self.avatar_url: str = d.get("avatarUrl", "")
        self.access_token: str = d.get("accessToken", "")
        self.refresh_token: str = d.get("refreshToken", "")
        self.game_token: str = d.get("gameToken", "")          # MyIDGo token
        self.raw_tpt_token: str = d.get("rawTptToken", "")
        self.uuid: str = d.get("uuid", "")
        self.mcuid: str = d.get("mcuid", "")
        self.tpt_sub: str = d.get("tptSub", "")
        self.device_id: str = d.get("deviceId", str(uuid.uuid4()))
        self.sc_game_token: str = d.get("scGameToken", "")     # SoftClimbers token
        self.kong_token: str = d.get("kongToken", "")          # KongIsland token
        self.expiry: str = d.get("expiry", "")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phone": self.phone,
            "fullName": self.full_name,
            "avatarUrl": self.avatar_url,
            "accessToken": self.access_token,
            "refreshToken": self.refresh_token,
            "gameToken": self.game_token,
            "rawTptToken": self.raw_tpt_token,
            "uuid": self.uuid,
            "mcuid": self.mcuid,
            "tptSub": self.tpt_sub,
            "deviceId": self.device_id,
            "scGameToken": self.sc_game_token,
            "kongToken": self.kong_token,
            "expiry": self.expiry,
        }

    def is_logged_in(self) -> bool:
        return bool(self.access_token and self.phone)

    def __repr__(self):
        return f"Account(phone={self.phone}, name={self.full_name})"


# ── User Session ──────────────────────────────────────────────────────────────

class UserSession:
    """
    Per-telegram-user session. Supports multiple MyID accounts.
    Mirrors AccountManager.java's multi-account logic.
    """
    def __init__(self, telegram_id: int):
        self.telegram_id = telegram_id
        self._data = self._load()

    def _load(self) -> Dict[str, Any]:
        all_data = _load_all()
        key = _user_key(self.telegram_id)
        return all_data.get(key, {"accounts": {}, "current_phone": ""})

    def _save(self) -> None:
        all_data = _load_all()
        key = _user_key(self.telegram_id)
        all_data[key] = self._data
        _save_all(all_data)

    # ── Accounts ─────────────────────────────────────────────────────────────

    def get_accounts(self) -> List[Account]:
        accounts_dict: Dict[str, Any] = self._data.get("accounts", {})
        return [Account(v) for v in accounts_dict.values()]

    def get_account(self, phone: str) -> Optional[Account]:
        accounts_dict = self._data.get("accounts", {})
        d = accounts_dict.get(phone)
        return Account(d) if d else None

    def get_current_account(self) -> Optional[Account]:
        phone = self._data.get("current_phone", "")
        if not phone:
            # Return first account if any
            accounts = self.get_accounts()
            if accounts:
                self._data["current_phone"] = accounts[0].phone
                self._save()
                return accounts[0]
            return None
        return self.get_account(phone)

    def set_current_phone(self, phone: str) -> None:
        self._data["current_phone"] = phone
        self._save()

    def save_account(self, account: Account) -> None:
        if not self._data.get("accounts"):
            self._data["accounts"] = {}
        self._data["accounts"][account.phone] = account.to_dict()
        # Set as current if first or only account
        if not self._data.get("current_phone"):
            self._data["current_phone"] = account.phone
        self._save()
        logger.info(f"Account saved: {account.phone} for user {self.telegram_id}")

    def remove_account(self, phone: str) -> None:
        accounts = self._data.get("accounts", {})
        if phone in accounts:
            del accounts[phone]
        if self._data.get("current_phone") == phone:
            remaining = list(accounts.keys())
            self._data["current_phone"] = remaining[0] if remaining else ""
        self._save()

    def update_account_field(self, phone: str, **kwargs) -> None:
        """Update specific fields of an account"""
        accounts = self._data.get("accounts", {})
        if phone in accounts:
            accounts[phone].update(kwargs)
            self._save()

    def has_accounts(self) -> bool:
        return bool(self._data.get("accounts"))

    # ── Pending state (for conversations) ─────────────────────────────────

    def set_pending(self, key: str, value: Any) -> None:
        if "pending" not in self._data:
            self._data["pending"] = {}
        self._data["pending"][key] = value
        self._save()

    def get_pending(self, key: str, default=None) -> Any:
        return self._data.get("pending", {}).get(key, default)

    def clear_pending(self) -> None:
        self._data["pending"] = {}
        self._save()


def get_session(telegram_id: int) -> UserSession:
    """Get or create session for a user"""
    return UserSession(telegram_id)


def parse_token_response(resp_body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse validate-otp API response to extract token fields.
    Handles multiple response shapes from the Mytel API.
    """
    result = {}

    # Top level
    for key in ("access_token", "accessToken"):
        if resp_body.get(key):
            result["access_token"] = resp_body[key]
            break

    for key in ("refresh_token", "refreshToken"):
        if resp_body.get(key):
            result["refresh_token"] = resp_body[key]
            break

    # Nested under "data"
    data = resp_body.get("data") or {}
    if isinstance(data, dict):
        for key in ("access_token", "accessToken"):
            if data.get(key) and not result.get("access_token"):
                result["access_token"] = data[key]
        for key in ("refresh_token", "refreshToken"):
            if data.get(key) and not result.get("refresh_token"):
                result["refresh_token"] = data[key]
        for key in ("uuid", "sub"):
            if data.get(key):
                result["uuid"] = data[key]
                break
        for key in ("mcuid",):
            if data.get(key):
                result["mcuid"] = data[key]
        for key in ("tpt_sub", "tptSub"):
            if data.get(key):
                result["tpt_sub"] = data[key]
                break
        # expiry
        for key in ("expiry", "exp"):
            if data.get(key):
                result["expiry"] = str(data[key])
                break

    # JWT decode for sub/mcuid if available
    if result.get("access_token") and not result.get("uuid"):
        try:
            import base64, json as _json
            parts = result["access_token"].split(".")
            if len(parts) >= 2:
                payload_b64 = parts[1] + "=="
                payload = _json.loads(base64.urlsafe_b64decode(payload_b64))
                result.setdefault("uuid", payload.get("sub", ""))
                result.setdefault("mcuid", payload.get("mcuid", ""))
                result.setdefault("tpt_sub", payload.get("tpt_sub", ""))
                result.setdefault("expiry", str(payload.get("exp", "")))
        except Exception:
            pass

    return result
