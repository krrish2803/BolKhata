import re
import time
from typing import Dict, Tuple
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError

_hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)

DISALLOWED_TRIVIAL_PINS = {
    "1234", "0000", "1111", "2222", "3333", "4444", "5555", "6666", "7777", "8888", "9999",
    "4321", "0123", "3210", "1212", "6969", "2580", "1357", "2468"
}

# Login rate limiting & lockout tracker:
# Key -> {"attempts": int, "lockout_until": float, "last_attempt": float}
_LOGIN_TRACKER: Dict[str, Dict[str, float]] = {}

LOCKOUT_THRESHOLD = 5
LOCKOUT_DURATION_SECONDS = 900  # 15 minutes lockout after 5 failed attempts

async def check_login_rate_limit(key: str, db=None) -> Tuple[bool, int]:
    """
    Checks if a key (phone or IP) is locked out.
    If database is available, syncs with auth_lockouts collection with TTL index.
    Returns (is_locked_out, remaining_seconds_locked).
    """
    now = time.time()
    
    # Check MongoDB collection if available
    if db is not None:
        try:
            doc = await db.auth_lockouts.find_one({"key": key})
            if doc and "lockout_until" in doc:
                lockout_until = doc["lockout_until"]
                if lockout_until > now:
                    return True, int(lockout_until - now)
        except Exception:
            pass

    # Fallback to in-memory tracker
    record = _LOGIN_TRACKER.get(key)
    if not record:
        return False, 0
    
    lockout_until = record.get("lockout_until", 0)
    if lockout_until > now:
        return True, int(lockout_until - now)
    
    # Reset expired lockout
    if lockout_until > 0 and lockout_until <= now:
        record["attempts"] = 0
        record["lockout_until"] = 0
        
    return False, 0

async def record_failed_login(key: str, db=None) -> Tuple[bool, int]:
    """
    Records a failed login attempt for a key (phone or IP).
    Locks out after 5 failures.
    Persists to MongoDB auth_lockouts with TTL if db is provided.
    Returns (is_now_locked_out, remaining_seconds).
    """
    now = time.time()
    record = _LOGIN_TRACKER.get(key)
    if not record:
        record = {"attempts": 0, "lockout_until": 0, "last_attempt": now}
        _LOGIN_TRACKER[key] = record

    if record.get("lockout_until", 0) > now:
        return True, int(record["lockout_until"] - now)

    if now - record.get("last_attempt", now) > 1800:
        record["attempts"] = 0

    record["attempts"] = record.get("attempts", 0) + 1
    record["last_attempt"] = now

    if record["attempts"] >= LOCKOUT_THRESHOLD:
        lockout_until = now + LOCKOUT_DURATION_SECONDS
        record["lockout_until"] = lockout_until
        
        # Persist to Mongo auth_lockouts with expiresAt for TTL auto-removal
        if db is not None:
            try:
                from datetime import datetime, timezone, timedelta
                expires_dt = datetime.now(timezone.utc) + timedelta(seconds=LOCKOUT_DURATION_SECONDS)
                await db.auth_lockouts.update_one(
                    {"key": key},
                    {"$set": {
                        "key": key,
                        "lockout_until": lockout_until,
                        "expiresAt": expires_dt,
                        "attempts": record["attempts"]
                    }},
                    upsert=True
                )
            except Exception:
                pass

        return True, LOCKOUT_DURATION_SECONDS

    return False, 0

async def reset_login_attempts(key: str, db=None) -> None:
    """Clear attempts on successful login."""
    if key in _LOGIN_TRACKER:
        _LOGIN_TRACKER[key] = {"attempts": 0, "lockout_until": 0, "last_attempt": time.time()}
    if db is not None:
        try:
            await db.auth_lockouts.delete_one({"key": key})
        except Exception:
            pass

def reset_all_login_trackers() -> None:
    """Helper for testing in-memory tracker."""
    _LOGIN_TRACKER.clear()

async def reset_all_login_trackers_async(db=None) -> None:
    """Helper for testing async."""
    _LOGIN_TRACKER.clear()
    if db is not None:
        try:
            await db.auth_lockouts.delete_many({})
        except Exception:
            pass

def is_trivial_pin(pin: str) -> bool:
    """
    Rejects trivial PINs (1234, 0000, repeated or sequential digits) for new real accounts.
    """
    if not pin or not isinstance(pin, str):
        return True
    
    clean = pin.strip()
    if len(clean) != 4 or not clean.isdigit():
        return True
    
    if clean in DISALLOWED_TRIVIAL_PINS:
        return True
    
    # Check all digits identical (e.g. 1111, 2222)
    if len(set(clean)) == 1:
        return True
    
    # Check sequential ascending (e.g. 1234, 2345, 6789)
    digits = [int(d) for d in clean]
    if all(digits[i] + 1 == digits[i+1] for i in range(3)):
        return True
        
    # Check sequential descending (e.g. 4321, 9876, 5432)
    digits = [int(d) for d in clean]
    if all(digits[i] - 1 == digits[i+1] for i in range(3)):
        return True
        
    return False

def hash_pin(pin: str) -> str:
    """Hash PIN using Argon2id."""
    return _hasher.hash(pin)

def verify_pin(stored_hash: str, pin: str) -> bool:
    """Verify PIN against Argon2id hash with constant-time security."""
    try:
        return _hasher.verify(stored_hash, pin)
    except (VerifyMismatchError, InvalidHashError):
        return False
    except Exception:
        return False

def mask_phone_for_logs(phone: str) -> str:
    """Never log full phone numbers; mask to +91 ******1234."""
    if not phone:
        return "[EMPTY]"
    clean = re.sub(r'\D', '', str(phone))
    if len(clean) >= 4:
        return f"+91 ******{clean[-4:]}"
    return "******"

