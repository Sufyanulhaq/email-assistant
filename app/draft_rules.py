"""Offline analyzer: sorts the email with triage.py and writes the reply from a template that quotes
the matching policy. Nothing is made up, because every sentence is either fixed text or a policy."""
from __future__ import annotations

import re

from .facts import find_orders
from .models import Draft, Email, Triage
from .policies import Policy
from .triage import classify

SIGN = "Kind regards,\nBrightline Support"
ACCOUNT_WORDS = ("password", "log in", "login", "reset")
HARDWARE_WORDS = ("motor", "broken", "fault", "warranty", "not working")


TITLES = {"dr", "mr", "mrs", "ms", "miss", "mx", "prof", "sir"}


def first_name(email: Email) -> str:
    words = [w for w in re.split(r"[\s._-]+", email.sender_name.strip()) if w and w.lower().rstrip(".") not in TITLES]
    return words[0].capitalize() if words else "there"


def reply_subject(subject: str) -> str:
    return subject if subject.lower().startswith("re:") else f"Re: {subject}"


def _policy_ids(email: Email, triage: Triage, policies: dict[str, Policy]) -> list[str]:
    text = f"{email.subject}\n{email.body}".lower()
    wanted = {
        "refund_request": ["refunds"],
        "shipping_status": ["shipping"],
        "billing": ["invoices"],
        "cancellation": ["cancellation"],
        "technical_support": ["password"] if any(w in text for w in ACCOUNT_WORDS) else ["warranty"] if any(w in text for w in HARDWARE_WORDS) else [],
    }.get(triage.category, [])
    return [p for p in wanted if p in policies]


def write_reply(email: Email, triage: Triage, ids: list[str], policies: dict[str, Policy]) -> Draft | None:
    if triage.category == "spam":
        return None
    first = first_name(email)
    orders = ", ".join(triage.order_numbers)
    if ids:
        quoted = " ".join(policies[i].text for i in ids)
        if triage.category == "refund_request":
            lead, close = "Thanks for getting in touch, and I am sorry the order has not worked out.", (
                f"If you reply to confirm that order {orders} is the one to send back, we will take it from there." if orders
                else "If you reply with your order number, we will take it from there.")
        elif triage.category == "shipping_status":
            lead, close = "Sorry for the wait.", (f"We will check order {orders} with the courier and write back." if orders
                                                   else "If you reply with your order number, we will check it with the courier and write back.")
        elif triage.category == "billing":
            lead, close = "Thanks for your message.", "If you reply with the order number or the month you need, we can resend it by email."
        elif triage.category == "cancellation":
            lead, close = "Thanks for letting us know.", "If you would rather we cancelled it for you, reply to confirm the email address on the account."
        else:
            lead, close = "Sorry you are having trouble.", "If that does not solve it, reply here and we will pick it up."
        body = f"{lead} {quoted}\n\n{close}"
    else:
        sorry = " I am sorry for the trouble you have had." if triage.category == "complaint" else ""
        hours = policies["hours"].text if "hours" in policies else ""
        body = f"Thank you for your message.{sorry} I have passed it to a colleague who will review it and reply. {hours}".strip()
        ids = ["hours"] if "hours" in policies else []
    return Draft(reply_subject(email.subject), f"Hi {first},\n\n{body}\n\n{SIGN}", ids)


class OfflineAnalyzer:
    def __init__(self, policies: dict[str, Policy]) -> None:
        self.policies = policies

    def __call__(self, email: Email) -> tuple[Triage, Draft | None]:
        triage = classify(email)
        triage.order_numbers = find_orders(f"{email.subject}\n{email.body}")
        return triage, write_reply(email, triage, _policy_ids(email, triage, self.policies), self.policies)
