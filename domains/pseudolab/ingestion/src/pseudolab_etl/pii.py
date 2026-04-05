"""PII 비식별화 — HMAC-SHA256 해싱."""

from __future__ import annotations

import hashlib
import hmac
from typing import Any

# 24개 테이블, 48개 칼럼 PII 매핑
PII_COLUMNS: dict[str, frozenset[str]] = {
    "email_verification_codes": frozenset({"email", "code"}),
    "event_cards": frozenset({"user_email"}),
    "event_committee": frozenset({"name", "email"}),
    "event_registrations": frozenset({"email", "name"}),
    "event_sessions": frozenset({"speaker_name", "speaker_email"}),
    "event_speaker_submissions": frozenset({"email", "speaker_name"}),
    "event_sponsor_submissions": frozenset({"contact_name", "email", "phone"}),
    "event_sponsors": frozenset({"contact_name", "contact_email", "contact_phone"}),
    "event_staff": frozenset({"name", "email"}),
    "legacy_members": frozenset({"email", "name"}),
    "opportunity_beneficiaries": frozenset({"beneficiary_name"}),
    "profiles": frozenset({"email", "name", "name_en", "name_kr"}),
    "program_feedbacks": frozenset({"user_email"}),
    "program_followups": frozenset({"user_email"}),
    "program_likes": frozenset({"user_email"}),
    "project_application_history": frozenset({"applicant_name_kr"}),
    "project_applications": frozenset({
        "applicant_name_kr", "applicant_name_en",
        "applicant_email", "applicant_phone",
    }),
    "registration_submissions": frozenset({"name", "email"}),
    "session_submissions": frozenset({"speaker_name", "email"}),
    "speaker_submissions": frozenset({"speaker_name", "email"}),
    "sponsor_submissions": frozenset({"contact_name", "email", "phone"}),
    "sponsorship_requests": frozenset({"name", "email"}),
    "user_follows": frozenset({"follower_email", "following_email"}),
    "user_which_projects": frozenset({"name"}),
}


def hash_pii(value: str | None, salt: str) -> str | None:
    """PII 값을 HMAC-SHA256으로 해싱한다.

    None은 None으로 유지. strip().lower() 전처리 후 해싱.
    """
    if value is None:
        return None
    return hmac.new(
        salt.encode(),
        value.strip().lower().encode(),
        hashlib.sha256,
    ).hexdigest()


def apply_pii_hashing(
    rows: list[dict[str, Any]],
    table_name: str,
    salt: str,
) -> list[dict[str, Any]]:
    """테이블의 PII 칼럼을 해싱한다. in-place 변환."""
    pii_cols = PII_COLUMNS.get(table_name)
    if not pii_cols:
        return rows

    for row in rows:
        for col in pii_cols:
            if col in row:
                row[col] = hash_pii(row[col], salt)

    return rows
