"""
Redact large binary payloads from log extra_data for API list responses and audit previews.
Prevents multi-megabyte JSON responses while preserving structure for compliance review.
"""
from __future__ import annotations

from typing import Any, Dict, Union

JsonValue = Union[Dict[str, Any], list, str, int, float, bool, None]


def sanitize_extra_data(obj: JsonValue) -> JsonValue:
    """Return a tree copy with content_base64 fields stripped (length metadata only)."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return _sanitize_dict(obj)
    if isinstance(obj, list):
        return [sanitize_extra_data(x) for x in obj]
    return obj


def _sanitize_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, v in d.items():
        if k == "content_base64" and isinstance(v, str) and len(v) > 0:
            out[k] = None
            out["_binary_payload_redacted"] = True
            out["_base64_char_length"] = len(v)
            continue
        if isinstance(v, dict):
            out[k] = _sanitize_dict(v)
        elif isinstance(v, list):
            out[k] = [sanitize_extra_data(x) for x in v]
        else:
            out[k] = v
    return out
