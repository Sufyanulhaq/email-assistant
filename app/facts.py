"""Facts the safety rules depend on, found with plain patterns. They never come from the model, so a
mistaken or manipulated model reply cannot hide an order number or a large refund."""
from __future__ import annotations

import re

ORDER = re.compile(r"\b[A-Z]{2}-\d{4,6}\b")
MONEY_BEFORE = re.compile(r"[$£€]\s?(\d[\d,]*(?:\.\d+)?)")
MONEY_AFTER = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(?:pounds|dollars|euros|gbp|usd|eur)\b", re.I)


def find_orders(text: str) -> list[str]:
    return list(dict.fromkeys(ORDER.findall(text)))


def find_amount(text: str) -> float | None:
    """The largest money amount mentioned. The currency is not converted."""
    found = [float(m.replace(",", "")) for m in MONEY_BEFORE.findall(text) + MONEY_AFTER.findall(text)]
    return max(found) if found else None
