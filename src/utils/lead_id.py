"""
Lead ID utilities.

We treat exported Excel files as the "database". To support stable updates from the
web app, each row gets a deterministic Lead_ID derived from business identity
fields.
"""

from __future__ import annotations

import hashlib
import re
from typing import Optional


_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def _norm_text(value: Optional[str]) -> str:
    if not value:
        return ""
    return _NON_ALNUM_RE.sub("", str(value).strip().lower())


def _norm_phone(value: Optional[str]) -> str:
    if not value:
        return ""
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    # Keep last 10 digits for US numbers.
    return digits[-10:] if len(digits) >= 10 else digits


def compute_lead_id(
    *,
    business_name: Optional[str],
    address: Optional[str] = None,
    phone: Optional[str] = None,
    website: Optional[str] = None,
) -> str:
    """
    Compute a deterministic Lead_ID.

    We intentionally include multiple fields to reduce collisions when two
    businesses share a similar name.
    """
    payload = "|".join(
        [
            _norm_text(business_name),
            _norm_text(address),
            _norm_phone(phone),
            _norm_text(website),
        ]
    ).encode("utf-8", errors="ignore")

    return hashlib.sha1(payload).hexdigest()
