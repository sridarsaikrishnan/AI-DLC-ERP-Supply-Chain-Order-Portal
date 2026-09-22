"""TotpService — MFA via TOTP (P-U1-2, pyotp)."""

from __future__ import annotations

import pyotp


def verify_totp(secret: str, code: str) -> bool:
    if not secret or not code:
        return False
    return pyotp.TOTP(secret).verify(code, valid_window=1)


def provision_secret() -> str:
    """Generate a new TOTP secret (used when enrolling a user)."""
    return pyotp.random_base32()
