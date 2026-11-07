import base64
import hashlib
import hmac
import secrets
import struct
import time

def generate_totp_secret() -> str:
    """Generate a secure 32-character Base32 secret for TOTP."""
    random_bytes = secrets.token_bytes(20)
    return base64.b32encode(random_bytes).decode('ascii').rstrip('=')

def _hotp(secret: str, counter: int) -> int:
    """Compute HMAC-based One-Time Password for a specific counter."""
    # Ensure correct padding
    padded_secret = secret + '=' * ((8 - len(secret) % 8) % 8)
    key = base64.b32decode(padded_secret.upper())
    msg = struct.pack('>Q', counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0f
    code = struct.unpack('>I', digest[offset:offset + 4])[0] & 0x7fffffff
    return code % 1_000_000

def generate_totp_code(secret: str, for_time: float = None) -> str:
    """Generate standard 6-digit TOTP code for current or specified timestamp."""
    if for_time is None:
        for_time = time.time()
    counter = int(for_time // 30)
    code = _hotp(secret, counter)
    return f"{code:06d}"

def verify_totp_code(secret: str, code: str, drift: int = 1) -> bool:
    """
    Verify 6-digit code against secret, allowing for clock drift of `drift` 30s intervals
    (default: -30s, 0s, +30s).
    """
    if not secret or not code:
        return False
    code_str = str(code).strip()
    if not code_str.isdigit() or len(code_str) != 6:
        return False

    current_counter = int(time.time() // 30)
    for offset in range(-drift, drift + 1):
        expected = f"{_hotp(secret, current_counter + offset):06d}"
        if hmac.compare_digest(expected, code_str):
            return True
    return False

def get_totp_uri(secret: str, email: str, issuer: str = "DigitalEqubEthiopia") -> str:
    """Return standard otpauth URI for authenticator app enrollment."""
    return f"otpauth://totp/{issuer}:{email}?secret={secret}&issuer={issuer}&algorithm=SHA1&digits=6&period=30"

