"""
TOTP verification (RFC 6238) for Google Authenticator–compatible apps.
"""
import pyotp

# Google Authenticator default: SHA1, 6 digits, 30-second step
TOTP_VALID_WINDOW = 1  # allow ±1 interval for clock skew


def verify_totp_code(secret_plain_base32: str, code: str) -> bool:
    """Return True if the 6-digit (or compatible) code is valid now."""
    cleaned = code.strip().replace(" ", "")
    if not cleaned.isdigit() or len(cleaned) < 6:
        return False
    totp = pyotp.TOTP(secret_plain_base32)
    return totp.verify(cleaned, valid_window=TOTP_VALID_WINDOW)


def random_base32_secret() -> str:
    return pyotp.random_base32()


def provisioning_uri(secret_plain_base32: str, account_label: str, issuer: str) -> str:
    totp = pyotp.TOTP(secret_plain_base32)
    return totp.provisioning_uri(name=account_label, issuer_name=issuer)
