"""
Regression tests for phone formats that policies depend on.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.services.presidio_service import PresidioService


def _has_phone_value(entities, needle: str) -> bool:
    for e in entities or []:
        if e.get("entity_type") == "PHONE_NUMBER" and needle in str(e.get("value", "")):
            return True
    return False


def test_detects_local_hyphenated_phone():
    svc = PresidioService()
    text = "Phone: 771-771-117"
    entities = svc.analyze(text)
    assert _has_phone_value(entities, "771-771-117")


def test_detects_local_spaced_phone():
    svc = PresidioService()
    text = "Phone: 771 771 117"
    entities = svc.analyze(text)
    assert _has_phone_value(entities, "771 771 117")

