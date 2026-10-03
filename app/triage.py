"""Offline sorting of an email by keywords. It is crude on purpose: easy to read, easy to change, and
good enough for the plain cases. Claude mode handles the rest."""
from __future__ import annotations

import re

from .models import Email, Triage

SPAM = ("you have won", "you have been selected", "claim your", "claim your prize", "free gift", "gift card", "click here", "this offer expires", "congratulations")
COMPLAINT = ("unacceptable", "disgraceful", "terrible", "worst", "third time", "nobody has replied", "no one has replied", "solicitor", "trading standards", "furious", "appalled", "ridiculous")
NEGATIVE = COMPLAINT + ("disappointed", "angry", "frustrated", "awful", "broken", "useless")
POSITIVE = ("thanks", "thank you", "lovely", "great", "love ")
URGENT = ("urgent", "asap", "today", "immediately", "third time", "straight away")

KEYWORDS = {
    "refund_request": ("refund", "send it back", "return the", "money back", "return it", "return of"),
    "shipping_status": ("where is my order", "where is it", "tracking", "not arrived", "hasn't arrived", "dispatched", "delivery"),
    "technical_support": ("log in", "login", "password", "can't log", "cannot log", "not working", "error", "reset"),
    "billing": ("invoice", "receipt", "vat", "charged", "billing"),
    "cancellation": ("cancel", "unsubscribe"),
    "sales_inquiry": ("pricing", "discount", "bulk", "quote", "do you offer"),
}


def _hits(text: str, words: tuple[str, ...]) -> int:
    return sum(1 for w in words if w in text)


def _summary(body: str) -> str:
    first = re.split(r"(?<=[.!?])\s+", " ".join(body.split()), maxsplit=1)[0]
    return first if len(first) <= 160 else first[:157].rstrip() + "..."


def classify(email: Email) -> Triage:
    text = f"{email.subject}\n{email.body}".lower()
    if _hits(text, SPAM) >= 2:
        category = "spam"
    elif _hits(text, COMPLAINT) >= 2:
        category = "complaint"
    else:
        scores = {c: _hits(text, w) for c, w in KEYWORDS.items()}
        best = max(scores.values())
        category = next(c for c, s in scores.items() if s == best) if best else "other"

    negative = _hits(text, NEGATIVE) > 0
    sentiment = "negative" if negative else "positive" if _hits(text, POSITIVE) else "neutral"
    if category == "spam" or category == "sales_inquiry":
        urgency = "low"
    elif category == "complaint" or _hits(text, URGENT):
        urgency = "high"
    else:
        urgency = "normal"
    return Triage(category, urgency, sentiment, _summary(email.body))
