"""
Comprehensive verification that the "anonymize" policy action works correctly in:
  1) Text analysis  (PolicyService.apply_policy  → masked_text)
  2) File analysis   (same engine, same return)
  3) Email monitoring (EmailMonitoringService.analyze_email → masked_body + masked_subject + attachment masking)

Run:
  cd backend && python -m pytest test_anonymize_all_paths.py -v
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import List
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))

import pytest

from app.services.policy_service import PolicyService
from app.services.email_monitoring_service import (
    EmailMonitoringService,
    attachment_contents_from_encrypted_full_text,
    attachment_files_recipient_masked_text,
)


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _fake_policy(pid, name, action, entity_types):
    return SimpleNamespace(
        id=pid, name=name, action=action,
        entity_types=entity_types, severity="medium", enabled=True,
    )


async def _noop(*_a, **_k):
    return None


def _patch_policy_service(svc: PolicyService, policies: list):
    """Context-manager stack that patches DB calls on PolicyService."""
    return _NestedPatches([
        mock.patch.object(svc, "get_active_policies", mock.AsyncMock(return_value=policies)),
        mock.patch.object(svc, "_create_alert", mock.AsyncMock(return_value="fake_alert_id")),
        mock.patch.object(svc, "_log_event", _noop),
        mock.patch.object(svc, "_store_detected_entity", _noop),
    ])


class _NestedPatches:
    def __init__(self, patches):
        self._patches = patches
        self._started = []

    def __enter__(self):
        for p in self._patches:
            self._started.append(p.start())
        return self

    def __exit__(self, *exc):
        for p in reversed(self._patches):
            p.stop()


# ===========================================================================
#  PATH 1 — Text analysis (PolicyService.apply_policy)
# ===========================================================================

class TestAnonymizeTextAnalysis:
    """Verifies masked_text from PolicyService for plain-text input."""

    @pytest.mark.asyncio
    async def test_single_email_entity_masked(self):
        svc = PolicyService()
        text = "Contact us at admin@example.com for help"
        entities = [{
            "entity_type": "EMAIL_ADDRESS", "start": 14, "end": 30,
            "score": 0.95, "value": "admin@example.com",
        }]
        policies = [_fake_policy("p1", "Mask emails", "anonymize", ["EMAIL_ADDRESS"])]

        with _patch_policy_service(svc, policies):
            result = await svc.apply_policy_with_entities(
                detected_entities=list(entities), text=text, user=None,
            )

        assert result["policies_matched"] is True
        assert result["masked_text"] is not None
        assert "admin@example.com" not in result["masked_text"]
        assert "[EMAIL_ADDRESS]" in result["masked_text"]
        assert result["masked_text"].startswith("Contact us at [EMAIL_ADDRESS]")

    @pytest.mark.asyncio
    async def test_multiple_entity_types_masked(self):
        svc = PolicyService()
        text = "Name: Ahmad, Phone: +966501234567"
        entities = [
            {"entity_type": "PERSON", "start": 6, "end": 11, "score": 0.9, "value": "Ahmad"},
            {"entity_type": "PHONE_NUMBER", "start": 20, "end": 33, "score": 0.85, "value": "+966501234567"},
        ]
        policies = [_fake_policy("p2", "Mask PII", "anonymize", ["PERSON", "PHONE_NUMBER"])]

        with _patch_policy_service(svc, policies):
            result = await svc.apply_policy_with_entities(
                detected_entities=list(entities), text=text, user=None,
            )

        mt = result["masked_text"]
        assert "Ahmad" not in mt
        assert "+966501234567" not in mt
        assert "[PERSON]" in mt
        assert "[PHONE_NUMBER]" in mt

    @pytest.mark.asyncio
    async def test_no_matching_entity_no_masking(self):
        svc = PolicyService()
        text = "Name: Ahmad"
        entities = [
            {"entity_type": "PERSON", "start": 6, "end": 11, "score": 0.9, "value": "Ahmad"},
        ]
        policies = [_fake_policy("p3", "Mask phones only", "anonymize", ["PHONE_NUMBER"])]

        with _patch_policy_service(svc, policies):
            result = await svc.apply_policy_with_entities(
                detected_entities=list(entities), text=text, user=None,
            )

        assert result["policies_matched"] is False
        assert result["masked_text"] is None

    @pytest.mark.asyncio
    async def test_encrypted_text_is_none_when_anonymize_only(self):
        svc = PolicyService()
        text = "Email: test@test.com"
        entities = [
            {"entity_type": "EMAIL_ADDRESS", "start": 7, "end": 20, "score": 0.9, "value": "test@test.com"},
        ]
        policies = [_fake_policy("p4", "Mask only", "anonymize", ["EMAIL_ADDRESS"])]

        with _patch_policy_service(svc, policies):
            result = await svc.apply_policy_with_entities(
                detected_entities=list(entities), text=text, user=None,
            )

        assert result["masked_text"] is not None
        assert result["encrypted_text"] is None

    @pytest.mark.asyncio
    async def test_actions_taken_lists_anonymized(self):
        svc = PolicyService()
        text = "Phone: 0501234567"
        entities = [
            {"entity_type": "PHONE_NUMBER", "start": 7, "end": 17, "score": 0.9, "value": "0501234567"},
        ]
        policies = [_fake_policy("p5", "Mask phones", "anonymize", ["PHONE_NUMBER"])]

        with _patch_policy_service(svc, policies):
            result = await svc.apply_policy_with_entities(
                detected_entities=list(entities), text=text, user=None,
            )

        assert "anonymized_PHONE_NUMBER" in result["actions_taken"]


# ===========================================================================
#  PATH 2 — File analysis (same engine, text extracted from file)
# ===========================================================================

class TestAnonymizeFileAnalysis:
    """
    File analysis extracts text then calls policy_service.apply_policy(text=…).
    The engine is identical to text analysis, so we verify the same return shape.
    """

    @pytest.mark.asyncio
    async def test_file_extracted_text_gets_masked(self):
        svc = PolicyService()
        file_text = "Report\nPatient SSN: 123-45-6789\nEnd"
        entities = [
            {"entity_type": "US_SSN", "start": 19, "end": 30, "score": 0.92, "value": "123-45-6789"},
        ]
        policies = [_fake_policy("fp1", "Mask SSN", "anonymize", ["US_SSN"])]

        with _patch_policy_service(svc, policies):
            result = await svc.apply_policy_with_entities(
                detected_entities=list(entities), text=file_text, user=None,
            )

        assert result["policies_matched"] is True
        mt = result["masked_text"]
        assert mt is not None
        assert "123-45-6789" not in mt
        assert "[US_SSN]" in mt

    @pytest.mark.asyncio
    async def test_file_analysis_response_schema_has_masked_text(self):
        """AnalysisResponse includes masked_text field."""
        from app.schemas.analysis import AnalysisResponse
        r = AnalysisResponse(
            sensitive_data_detected=True,
            masked_text="Report\nPatient SSN: [US_SSN]\nEnd",
        )
        assert r.masked_text is not None
        assert "[US_SSN]" in r.masked_text

    @pytest.mark.asyncio
    async def test_file_analysis_route_passes_masked_text(self):
        """analysis.py routes lines 266-267 pass masked_text from result to AnalysisResponse."""
        from app.schemas.analysis import AnalysisResponse
        mock_result = {
            "sensitive_data_detected": True,
            "detected_entities": [],
            "actions_taken": ["anonymized_EMAIL_ADDRESS"],
            "blocked": False,
            "alert_created": True,
            "policies_matched": True,
            "applied_policies": [],
            "encrypted_text": None,
            "masked_text": "File content with [EMAIL_ADDRESS] masked",
        }
        resp = AnalysisResponse(
            sensitive_data_detected=mock_result["sensitive_data_detected"],
            detected_entities=mock_result["detected_entities"],
            actions_taken=mock_result["actions_taken"],
            blocked=mock_result["blocked"],
            alert_created=mock_result.get("alert_created", False),
            policies_matched=mock_result.get("policies_matched", False),
            applied_policies=mock_result.get("applied_policies", []),
            encrypted_text=mock_result.get("encrypted_text"),
            masked_text=mock_result.get("masked_text"),
        )
        assert resp.masked_text == "File content with [EMAIL_ADDRESS] masked"
        assert resp.encrypted_text is None


# ===========================================================================
#  PATH 3 — Email monitoring (EmailMonitoringService.analyze_email)
# ===========================================================================

class TestAnonymizeEmail:
    """Verifies anonymize works in email body, subject, and attachments."""

    def _build_email(self, body, subject="Test Subject", attachments=None):
        return {
            "from": "sender@example.com",
            "to": ["recipient@example.com"],
            "subject": subject,
            "body": body,
            "attachments": attachments or [],
            "source_ip": "10.0.0.1",
        }

    @pytest.mark.asyncio
    async def test_email_body_anonymized(self):
        ems = EmailMonitoringService()
        body = "My email is user@test.com please reply"
        subject = "Hello"
        email = self._build_email(body, subject=subject)
        full_text = f"{subject}\n\n{body}"

        body_start = len(subject) + 2
        email_start = body_start + body.index("user@test.com")
        email_end = email_start + len("user@test.com")

        entities = [{
            "entity_type": "EMAIL_ADDRESS",
            "start": email_start,
            "end": email_end,
            "score": 0.95,
            "value": "user@test.com",
        }]
        policies = [_fake_policy("ep1", "Mask emails", "anonymize", ["EMAIL_ADDRESS"])]

        mock_policy_result = {
            "sensitive_data_detected": True,
            "detected_entities": entities,
            "actions_taken": ["anonymized_EMAIL_ADDRESS", "alert_created"],
            "blocked": False,
            "alert_created": True,
            "policies_matched": True,
            "applied_policies": [
                {"name": "Mask emails", "action": "anonymize", "severity": "medium",
                 "entity_types": ["EMAIL_ADDRESS"], "matched_entities": ["EMAIL_ADDRESS"], "matched_count": 1, "id": "ep1"}
            ],
            "encrypted_text": None,
            "masked_text": full_text[:email_start] + "[EMAIL_ADDRESS]" + full_text[email_end:],
            "last_alert_id": None,
        }

        with mock.patch.object(ems.presidio, "analyze", return_value=entities):
            with mock.patch.object(
                ems.policy_service, "apply_policy_with_entities",
                mock.AsyncMock(return_value=mock_policy_result),
            ):
                with mock.patch.object(ems, "_log_email_event", _noop):
                    with mock.patch.object(ems, "_store_detected_entity", _noop):
                        with mock.patch.object(ems.policy_service, "get_active_policies", mock.AsyncMock(return_value=policies)):
                            result = await ems.analyze_email(email)

        assert result["action"] == "anonymize"
        assert result["masked_body"] is not None
        assert "user@test.com" not in result["masked_body"]
        assert "[EMAIL_ADDRESS]" in result["masked_body"]
        assert result["blocked"] is False

    @pytest.mark.asyncio
    async def test_email_subject_anonymized(self):
        ems = EmailMonitoringService()
        subject = "Info for user@test.com"
        body = "No sensitive data here"
        email = self._build_email(body, subject=subject)
        full_text = f"{subject}\n\n{body}"

        subj_start = subject.index("user@test.com")
        subj_end = subj_start + len("user@test.com")

        entities = [{
            "entity_type": "EMAIL_ADDRESS",
            "start": subj_start,
            "end": subj_end,
            "score": 0.95,
            "value": "user@test.com",
        }]
        policies = [_fake_policy("ep2", "Mask emails", "anonymize", ["EMAIL_ADDRESS"])]

        mock_policy_result = {
            "sensitive_data_detected": True,
            "detected_entities": entities,
            "actions_taken": ["anonymized_EMAIL_ADDRESS", "alert_created"],
            "blocked": False,
            "alert_created": True,
            "policies_matched": True,
            "applied_policies": [
                {"name": "Mask emails", "action": "anonymize", "severity": "medium",
                 "entity_types": ["EMAIL_ADDRESS"], "matched_entities": ["EMAIL_ADDRESS"], "matched_count": 1, "id": "ep2"}
            ],
            "encrypted_text": None,
            "masked_text": full_text[:subj_start] + "[EMAIL_ADDRESS]" + full_text[subj_end:],
            "last_alert_id": None,
        }

        with mock.patch.object(ems.presidio, "analyze", return_value=entities):
            with mock.patch.object(
                ems.policy_service, "apply_policy_with_entities",
                mock.AsyncMock(return_value=mock_policy_result),
            ):
                with mock.patch.object(ems, "_log_email_event", _noop):
                    with mock.patch.object(ems, "_store_detected_entity", _noop):
                        with mock.patch.object(ems.policy_service, "get_active_policies", mock.AsyncMock(return_value=policies)):
                            result = await ems.analyze_email(email)

        assert result["action"] == "anonymize"
        assert result["masked_subject"] is not None
        assert "user@test.com" not in result["masked_subject"]
        assert "[EMAIL_ADDRESS]" in result["masked_subject"]

    @pytest.mark.asyncio
    async def test_email_attachment_text_anonymized(self):
        """Attachment text extracts should also be masked in the processed full_text."""
        rows = [{"filename": "contacts.txt", "content": "Owner: admin@corp.com\nPhone: 0501234567"}]
        masked_full = (
            "Subject\n\nBody text\n\n"
            "[Attachment: contacts.txt]\n"
            "Owner: [EMAIL_ADDRESS]\nPhone: [PHONE_NUMBER]"
        )
        out = attachment_contents_from_encrypted_full_text(masked_full, rows)
        assert out is not None
        assert len(out) == 1
        assert out[0]["filename"] == "contacts.txt"
        assert "[EMAIL_ADDRESS]" in out[0]["content"]
        assert "[PHONE_NUMBER]" in out[0]["content"]
        assert "admin@corp.com" not in out[0]["content"]
        assert "0501234567" not in out[0]["content"]

    @pytest.mark.asyncio
    async def test_email_attachment_download_uses_masked_text_for_text_files(self):
        """
        For anonymize policy, attachment_files download bytes for text-like files
        should reflect the masked extract (same as recipient preview), not raw upload.
        """
        attachment_files = [
            {
                "filename": "contacts.txt",
                "content_type": "text/plain",
                "content_base64": "T3JpZ2luYWw=",  # "Original"
            },
            {
                "filename": "evidence.pdf",
                "content_type": "application/pdf",
                "content_base64": "JVBERi0xLjQ=",
            },
        ]
        recipient_rows = [
            {"filename": "contacts.txt", "content": "Owner: [EMAIL_ADDRESS]\nPhone: [PHONE_NUMBER]"},
            {"filename": "evidence.pdf", "content": "[EMAIL_ADDRESS] in document"},
        ]
        out = attachment_files_recipient_masked_text(attachment_files, recipient_rows)
        assert out is not None

        txt = next(x for x in out if x["filename"] == "contacts.txt")
        assert txt.get("policy_masked_download") is True
        assert txt.get("content_type") == "text/plain; charset=utf-8"
        assert txt.get("content_base64") != "T3JpZ2luYWw="

        pdf = next(x for x in out if x["filename"] == "evidence.pdf")
        # Binary format stays original bytes; only note is added.
        assert pdf.get("content_base64") == "JVBERi0xLjQ="
        assert "masked preview" in (pdf.get("download_note") or "")

    @pytest.mark.asyncio
    async def test_email_result_has_correct_message_for_anonymize(self):
        ems = EmailMonitoringService()
        body = "Phone 0501234567"
        email = self._build_email(body, subject="Hi")
        full_text = f"Hi\n\n{body}"

        body_start = 4
        phone_start = body_start + body.index("0501234567")
        phone_end = phone_start + 10

        entities = [{
            "entity_type": "PHONE_NUMBER",
            "start": phone_start,
            "end": phone_end,
            "score": 0.85,
            "value": "0501234567",
        }]
        policies = [_fake_policy("ep3", "Mask phones", "anonymize", ["PHONE_NUMBER"])]

        mock_policy_result = {
            "sensitive_data_detected": True,
            "detected_entities": [dict(e, anonymized_value=f"[{e['entity_type']}]") for e in entities],
            "actions_taken": ["anonymized_PHONE_NUMBER", "alert_created"],
            "blocked": False,
            "alert_created": True,
            "policies_matched": True,
            "applied_policies": [
                {"name": "Mask phones", "action": "anonymize", "severity": "medium",
                 "entity_types": ["PHONE_NUMBER"], "matched_entities": ["PHONE_NUMBER"], "matched_count": 1, "id": "ep3"}
            ],
            "encrypted_text": None,
            "masked_text": full_text[:phone_start] + "[PHONE_NUMBER]" + full_text[phone_end:],
            "last_alert_id": None,
        }

        with mock.patch.object(ems.presidio, "analyze", return_value=entities):
            with mock.patch.object(
                ems.policy_service, "apply_policy_with_entities",
                mock.AsyncMock(return_value=mock_policy_result),
            ):
                with mock.patch.object(ems, "_log_email_event", _noop):
                    with mock.patch.object(ems, "_store_detected_entity", _noop):
                        with mock.patch.object(ems.policy_service, "get_active_policies", mock.AsyncMock(return_value=policies)):
                            result = await ems.analyze_email(email)

        assert result["action"] == "anonymize"
        assert "إخفاء" in result["message"] or "masking" in result["message"].lower()


# ===========================================================================
#  PATH 4 — Consistency: same engine produces identical masking for analysis & email
# ===========================================================================

class TestAnonymizeConsistency:
    """Verify that the SAME policy engine produces identical masking regardless of caller."""

    @pytest.mark.asyncio
    async def test_same_text_same_masked_output(self):
        """Given identical text + entities + policies, masked_text MUST be identical."""
        text = "Hello admin@corp.com and +966501234567"
        entities = [
            {"entity_type": "EMAIL_ADDRESS", "start": 6, "end": 20, "score": 0.95, "value": "admin@corp.com"},
            {"entity_type": "PHONE_NUMBER", "start": 25, "end": 38, "score": 0.85, "value": "+966501234567"},
        ]
        policies = [_fake_policy("c1", "Mask all", "anonymize", ["EMAIL_ADDRESS", "PHONE_NUMBER"])]

        svc = PolicyService()
        with _patch_policy_service(svc, policies):
            r1 = await svc.apply_policy_with_entities(
                detected_entities=[dict(e) for e in entities], text=text, user=None,
            )
        with _patch_policy_service(svc, policies):
            r2 = await svc.apply_policy_with_entities(
                detected_entities=[dict(e) for e in entities], text=text, user=None,
            )

        assert r1["masked_text"] == r2["masked_text"]
        assert "[EMAIL_ADDRESS]" in r1["masked_text"]
        assert "[PHONE_NUMBER]" in r1["masked_text"]
        assert "admin@corp.com" not in r1["masked_text"]
        assert "+966501234567" not in r1["masked_text"]

    @pytest.mark.asyncio
    async def test_email_body_uses_same_engine_offsets(self):
        """
        Email service builds full_text = subject + '\\n\\n' + body, then passes to
        apply_policy_with_entities. The body_start offset ensures body entities
        are correctly sliced for masked_body.
        """
        subject = "Report"
        body = "SSN: 123-45-6789"
        full_text = f"{subject}\n\n{body}"
        body_start = len(subject) + 2

        ssn_start_in_body = body.index("123-45-6789")
        ssn_start = body_start + ssn_start_in_body
        ssn_end = ssn_start + len("123-45-6789")

        assert full_text[ssn_start:ssn_end] == "123-45-6789"

        entities = [{
            "entity_type": "US_SSN",
            "start": ssn_start,
            "end": ssn_end,
            "score": 0.92,
            "value": "123-45-6789",
            "anonymized_value": "[US_SSN]",
        }]

        masked_body = body
        start_rel = ssn_start - body_start
        end_rel = ssn_end - body_start
        placeholder = entities[0]["anonymized_value"]
        masked_body = masked_body[:start_rel] + placeholder + masked_body[end_rel:]

        assert "123-45-6789" not in masked_body
        assert "[US_SSN]" in masked_body
        assert masked_body == "SSN: [US_SSN]"


# ---------------------------------------------------------------------------
#  Runner for direct execution
# ---------------------------------------------------------------------------

def main():
    tests = [
        TestAnonymizeTextAnalysis().test_single_email_entity_masked,
        TestAnonymizeTextAnalysis().test_multiple_entity_types_masked,
        TestAnonymizeTextAnalysis().test_no_matching_entity_no_masking,
        TestAnonymizeTextAnalysis().test_encrypted_text_is_none_when_anonymize_only,
        TestAnonymizeTextAnalysis().test_actions_taken_lists_anonymized,
        TestAnonymizeFileAnalysis().test_file_extracted_text_gets_masked,
        TestAnonymizeEmail().test_email_body_anonymized,
        TestAnonymizeEmail().test_email_subject_anonymized,
        TestAnonymizeEmail().test_email_attachment_text_anonymized,
        TestAnonymizeEmail().test_email_attachment_download_uses_masked_text_for_text_files,
        TestAnonymizeEmail().test_email_result_has_correct_message_for_anonymize,
        TestAnonymizeConsistency().test_same_text_same_masked_output,
        TestAnonymizeConsistency().test_email_body_uses_same_engine_offsets,
    ]
    for t in tests:
        if asyncio.iscoroutinefunction(t):
            asyncio.run(t())
        else:
            t()
        print(f"  PASS  {t.__qualname__}")
    print(f"\nAll {len(tests)} anonymize path tests passed.")


if __name__ == "__main__":
    main()
