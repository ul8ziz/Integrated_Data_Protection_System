"""
TOTP verification (RFC 6238) for Google Authenticator–compatible apps.
"""
import logging
from datetime import datetime, timezone

import pyotp

logger = logging.getLogger(__name__)

# Google Authenticator default: SHA1, 6 digits, 30-second step.
# valid_window=2 accepts codes from ±2 intervals (~±60 s) to tolerate
# moderate clock drift between the server and the user's phone.
TOTP_VALID_WINDOW = 2


def verify_totp_code(secret_plain_base32: str, code: str) -> bool:
    """Return True if the 6-digit (or compatible) code is valid now.

    Always uses an explicit UTC timestamp so the result is independent
    of the server's local-timezone configuration.
    """
    cleaned = code.strip().replace(" ", "")
    if not cleaned.isdigit() or len(cleaned) < 6:
        return False
    totp = pyotp.TOTP(secret_plain_base32)
    now_utc = datetime.now(timezone.utc)
    result = totp.verify(cleaned, for_time=now_utc, valid_window=TOTP_VALID_WINDOW)
    if not result:
        expected = totp.at(now_utc)
        logger.warning(
            "TOTP mismatch: server_utc=%s, expected_code=%s…, given=%s…",
            now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            expected[:3] + "***",
            cleaned[:3] + "***",
        )
    return result


def random_base32_secret() -> str:
    return pyotp.random_base32()


def provisioning_uri(secret_plain_base32: str, account_label: str, issuer: str) -> str:
    totp = pyotp.TOTP(secret_plain_base32)
    return totp.provisioning_uri(name=account_label, issuer_name=issuer)
