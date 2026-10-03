from __future__ import annotations

from dataclasses import dataclass, field

CATEGORIES = [
    "refund_request", "shipping_status", "technical_support", "billing",
    "cancellation", "sales_inquiry", "complaint", "spam", "other",
]
URGENCIES = ["high", "normal", "low"]
SENTIMENTS = ["negative", "neutral", "positive"]


@dataclass
class Email:
    id: str
    sender_name: str
    sender_email: str
    subject: str
    date: str
    body: str


@dataclass
class Triage:
    category: str
    urgency: str
    sentiment: str
    summary: str
    order_numbers: list[str] = field(default_factory=list)
    amount: float | None = None


@dataclass
class Draft:
    subject: str
    text: str
    policy_ids: list[str] = field(default_factory=list)


@dataclass
class Review:
    needs_human: bool
    reasons: list[str] = field(default_factory=list)
