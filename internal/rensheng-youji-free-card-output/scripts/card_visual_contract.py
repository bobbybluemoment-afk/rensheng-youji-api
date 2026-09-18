"""Shared deterministic contract for free cards and full-report cards."""

from __future__ import annotations

import hashlib
import json
from typing import Any


CARD_ALGORITHM_VERSION = "2.0.0"


def canonical_digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

