"""
Automated checks that policy actions apply consistently to the same engine
used by text/file analysis and email (apply_policy_with_entities).

Run from repo root:
  cd backend && python -m pytest test_policy_apply_analysis_email.py -v
Or:
  cd backend && python test_policy_apply_analysis_email.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

# Ensure backend package is importable
sys.path.insert(0, str(Path(__file__).parent))

import pytest

from app.services.policy_service import PolicyService
from app.services.email_monitoring_service import (
    attachment_contents_from_encrypted_full_text,
)


def _fake_policy(pid: str, name: str, action: str, entity_types: list):
    return SimpleNamespace(
        id=pid,
        name=name,
        action=action,
        entity_types=entity_types,
        severity="medium",
        enabled=True,
    )


@pytest.mark.asyncio
async def test_encrypt_policy_replaces_all_matching_spans():
    svc = PolicyService()
    text = "Contact a@example.com or phone +966501234567"
    entities = [
        {
            "entity_type": "EMAIL_ADDRESS",
            "start": 8,
            "end": 21,
            "score": 0.9,
            "value": "a@example.com",
        },
        {
            "entity_type": "PHONE_NUMBER",
            "start": 31,
            "end": 44,
            "score": 0.85,
            "value": "+966501234567",
        },
    ]
    policies = [
        _fake_policy("1", "Encrypt PII", "encrypt", ["EMAIL_ADDRESS", "PHONE_NUMBER"]),
    ]

    async def noop(*_a, **_k):
        return None

    with mock.patch.object(svc, "get_active_policies", mock.AsyncMock(return_value=policies)):
        with mock.patch.object(svc, "_create_alert", mock.AsyncMock(return_value=None)):
            with mock.patch.object(svc, "_log_event", noop):
                with mock.patch.object(svc, "_store_detected_entity", noop):
                    with mock.patch.object(svc.mydlp, "block_data_transfer", return_value=False):
                        result = await svc.apply_policy_with_entities(
                            detected_entities=list(entities),
                            text=text,
                            user=None,
                        )

    assert result["policies_matched"] is True
    assert result["encrypted_text"] is not None
    enc = result["encrypted_text"]
    assert "a@example.com" not in enc
    assert "+966501234567" not in enc
    assert enc.startswith("Contact ")
    # Fernet tokens from this service typically start with gAAAAA
    assert "gAAAAA" in enc


@pytest.mark.asyncio
async def test_anonymize_policy_replaces_with_placeholders():
    svc = PolicyService()
    text = "Email me at user@test.com today"
    entities = [
        {
            "entity_type": "EMAIL_ADDRESS",
            "start": 12,
            "end": 25,
            "score": 0.9,
            "value": "user@test.com",
        },
    ]
    policies = [_fake_policy("2", "Mask emails", "anonymize", ["EMAIL_ADDRESS"])]

    async def noop(*_a, **_k):
        return None

    with mock.patch.object(svc, "get_active_policies", mock.AsyncMock(return_value=policies)):
        with mock.patch.object(svc, "_create_alert", mock.AsyncMock(return_value=None)):
            with mock.patch.object(svc, "_log_event", noop):
                with mock.patch.object(svc, "_store_detected_entity", noop):
                    result = await svc.apply_policy_with_entities(
                        detected_entities=list(entities),
                        text=text,
                        user=None,
                    )

    assert result["policies_matched"] is True
    assert result["masked_text"] is not None
    assert "user@test.com" not in result["masked_text"]
    assert "[EMAIL_ADDRESS]" in result["masked_text"]


@pytest.mark.asyncio
async def test_per_user_policy_assignment_filters_policies():
    svc = PolicyService()
    p_encrypt = _fake_policy("e1", "Enc", "encrypt", ["EMAIL_ADDRESS"])
    p_alert = _fake_policy("a1", "Alert only", "alert", ["PHONE_NUMBER"])
    all_policies = [p_encrypt, p_alert]
    user = SimpleNamespace(assigned_policy_ids=["a1"])

    chain = mock.MagicMock()
    chain.to_list = mock.AsyncMock(return_value=all_policies)
    with mock.patch("app.services.policy_service.Policy.find", return_value=chain):
        out = await svc.get_active_policies(user=user)

    assert len(out) == 1
    assert out[0].id == "a1"


def test_attachment_slice_parsing_works_for_masked_full_text():
    """Same [Attachment:] parser used for encrypt applies to masked full_text."""
    rows = [{"filename": "note.txt", "content": "secret@x.com and 0500000000"}]
    masked_full = (
        "Subject line\n\n"
        "Body line\n\n"
        "[Attachment: note.txt]\n"
        "[EMAIL_ADDRESS] and [PHONE_NUMBER]"
    )
    out = attachment_contents_from_encrypted_full_text(masked_full, rows)
    assert out is not None
    assert len(out) == 1
    assert out[0]["filename"] == "note.txt"
    assert "[EMAIL_ADDRESS]" in out[0]["content"]
    assert "[PHONE_NUMBER]" in out[0]["content"]


def main():
    """Run without pytest if needed."""
    asyncio.run(test_encrypt_policy_replaces_all_matching_spans())
    asyncio.run(test_anonymize_policy_replaces_with_placeholders())
    asyncio.run(test_per_user_policy_assignment_filters_policies())
    test_attachment_slice_parsing_works_for_masked_full_text()
    print("All policy apply tests passed.")


if __name__ == "__main__":
    main()
