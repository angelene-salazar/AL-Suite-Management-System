import hashlib
import os
import binascii
from typing import Tuple
import re


PBKDF2_ROUNDS = 100_000

def hash_password(password: str, salt: bytes = None) -> Tuple[str, str]:
    if salt is None:
        salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ROUNDS)
    return binascii.hexlify(salt).decode(), binascii.hexlify(dk).decode()

def verify_password(password: str, salt_hex: str, hash_hex: str) -> bool:
    salt = binascii.unhexlify(salt_hex)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ROUNDS)
    return binascii.hexlify(dk).decode() == hash_hex

def try_int_or_zero(text: str) -> int:
    """Safely converts a string to an integer, returning 0 on failure."""
    try:
        return int(text)
    except (ValueError, TypeError):
        # Catches error if input is empty, non-numeric, or incorrect type
        return 0

def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Checks if password meets requirements:
    - Min 8 chars
    - 1 Uppercase
    - 1 Lowercase
    - 1 Number
    Returns (True, "OK") or (False, "Error Message").
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number."
    return True, "OK"

