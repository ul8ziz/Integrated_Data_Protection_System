"""Quick regression check for presidio entity fixes (run from backend: python scripts/_test_presidio_fix.py)"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.presidio_service import PresidioService

SAMPLE = """Name: Ahmed Al-Qahtani
Phone: +966-50-123-4567
Email: ahmed.qahtani@example.com
Address: King Fahd Street, Riyadh, Saudi Arabia
Organization: Saudi National Bank

Date: 15/01/2024
Location: Riyadh, Saudi Arabia

IP Address: 192.168.1.1

Credit Card: 4532-1234-5678-9012

IBAN: SA03 8000 0000 6080 1016 7519

US SSN: 123-45-6789

VAT ID: 300123456700003
Tax Number: SA123456789012345

Stock Symbol: AAPL
Stock Market: 2222.SR
ISIN: US0378331005

Revenue: 250000 USD
Profit: 50000 SAR

<script>alert('XSS attack')</script>

SELECT * FROM users WHERE username='admin' OR '1'='1';
"""


def main():
    s = PresidioService()
    out = s.analyze(SAMPLE)
    types = [e["entity_type"] for e in out]
    vals = {e["entity_type"]: e.get("value") for e in out}

    # False positive CC inside IBAN must not appear
    bad_cc = [e for e in out if e["entity_type"] == "CREDIT_CARD" and "8000" in str(e.get("value", ""))]
    assert not bad_cc, f"CC false positive from IBAN: {bad_cc}"

    ibans = [e for e in out if e["entity_type"] == "IBAN_CODE"]
    assert ibans, "IBAN_CODE should be detected"
    assert any("SA0380000000608010167519" in str(e.get("value", "")).replace(" ", "") for e in ibans)

    assert "STOCK" in types
    assert any("2222" in str(e.get("value", "")) for e in out if e["entity_type"] == "STOCK")

    assert "MALICIOUS_SCRIPT" in types
    assert any(
        e["entity_type"] == "MALICIOUS_SCRIPT" and "SELECT" in str(e.get("value", ""))
        for e in out
    )

    locs = [e for e in out if e["entity_type"] == "LOCATION"]
    riyadh = [e for e in locs if "riyadh" in e.get("value", "").lower()]
    assert len(riyadh) <= 1, f"Duplicate LOCATION Riyadh: {len(riyadh)}"

    assert "PERSON" in types
    assert "ADDRESS" in types
    assert "ORGANIZATION" in types

    print("OK:", len(out), "entities")
    for e in sorted(out, key=lambda x: x["start"]):
        print(f"  {e['entity_type']}: {e.get('value', '')[:60]!r}")


if __name__ == "__main__":
    main()
