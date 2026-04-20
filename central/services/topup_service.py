"""Top-up code redemption and generation."""

from __future__ import annotations

import random
import string
from datetime import datetime, timezone

try:
    from ..database import log_event
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from database import log_event

try:
    from common.constants import EV_TOPUP, EV_TOPUP_FAILED
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from common.constants import EV_TOPUP, EV_TOPUP_FAILED

_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
_CODE_CHARS = string.ascii_uppercase + string.digits


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime(_TIMESTAMP_FORMAT)


def redeem_code(db, user_id: str, code: str) -> dict:
    """Credit user balance with the code's amount.

    Returns dict with keys: success (bool), amount (float|None),
    new_balance (float|None), error (str|None).
    """
    code = code.strip().upper()

    row = db.execute(
        "SELECT code, amount, is_redeemed FROM topup_codes WHERE code = ?",
        (code,),
    ).fetchone()

    if not row:
        _safe_log(user_id, EV_TOPUP_FAILED, {"user_id": user_id, "code": code, "reason": "invalid_code"})
        return {"success": False, "amount": None, "new_balance": None, "error": "invalid_code"}

    if row["is_redeemed"]:
        _safe_log(user_id, EV_TOPUP_FAILED, {"user_id": user_id, "code": code, "reason": "already_redeemed"})
        return {"success": False, "amount": None, "new_balance": None, "error": "already_redeemed"}

    amount = float(row["amount"])
    now = _utc_iso()

    db.execute(
        "UPDATE topup_codes SET is_redeemed = 1, redeemed_by = ?, redeemed_at = ? WHERE code = ?",
        (user_id, now, code),
    )
    db.execute(
        "UPDATE users SET balance = balance + ? WHERE user_id = ?",
        (amount, user_id),
    )
    db.commit()

    new_balance = float(
        db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)).fetchone()["balance"]
    )

    _safe_log(user_id, EV_TOPUP, {"user_id": user_id, "code": code, "amount": amount, "new_balance": new_balance})
    return {"success": True, "amount": amount, "new_balance": new_balance, "error": None}


def generate_codes(db, count: int, amount: float) -> list[str]:
    """Generate `count` random 8-character alphanumeric codes worth `amount` GTQ each."""
    codes = []
    while len(codes) < count:
        candidate = "".join(random.choices(_CODE_CHARS, k=8))
        existing = db.execute(
            "SELECT code FROM topup_codes WHERE code = ?", (candidate,)
        ).fetchone()
        if existing:
            continue
        db.execute(
            "INSERT INTO topup_codes (code, amount) VALUES (?, ?)",
            (candidate, amount),
        )
        codes.append(candidate)
    db.commit()
    return codes


def _safe_log(source: str, event_type: str, payload=None) -> None:
    try:
        log_event(source=source, event_type=event_type, payload=payload)
    except Exception:
        pass
