"""One email in, one record out: analyze, add the facts found by code, apply the safety rules."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from . import rules
from .facts import find_amount, find_orders
from .models import Draft, Email, Review, Triage

Analyzer = Callable[[Email], tuple[Triage, Draft | None]]


@dataclass
class Record:
    email: Email
    triage: Triage
    draft: Draft | None
    review: Review
    approved: bool = False
    edited: bool = False

    @property
    def status(self) -> str:
        if self.triage.category == "spam":
            return "spam"
        if self.approved:
            return "approved"
        return "needs_human" if self.review.needs_human else "draft_ready"


def process(email: Email, analyzer: Analyzer) -> Record:
    triage, draft = analyzer(email)
    text = f"{email.subject}\n{email.body}"
    triage.order_numbers = find_orders(text)
    triage.amount = find_amount(text)
    return Record(email, triage, draft, rules.review(email, triage, draft))
