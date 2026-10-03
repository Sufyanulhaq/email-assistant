"""When a person must look at an email. These rules run after the drafting step and cannot be
overridden by it, whichever mode produced the draft."""
from __future__ import annotations

from .models import Draft, Email, Review, Triage

REFUND_LIMIT = 500  # refunds above this are never handled from a draft alone
LEGAL = ("solicitor", "lawyer", "legal action", "trading standards", "sue ", "court", "chargeback", "ombudsman")
SAFETY = ("injur", "caught fire", "smoke", "burn", "unsafe", "dangerous", "collapsed")
PRIVACY = ("gdpr", "data breach", "delete my data", "personal data")
NEEDS_POLICY = {"refund_request", "shipping_status", "technical_support", "billing", "cancellation"}


def review(email: Email, triage: Triage, draft: Draft | None) -> Review:
    if triage.category == "spam":
        return Review(False)
    text = f"{email.subject}\n{email.body}".lower()
    reasons: list[str] = []
    for label, words in (("Legal language", LEGAL), ("Possible safety issue", SAFETY), ("Privacy or data request", PRIVACY)):
        found = next((w.strip() for w in words if w in text), None)
        if found:
            reasons.append(f'{label} in the email ("{found}")')
    if triage.category == "refund_request" and triage.amount is not None and triage.amount > REFUND_LIMIT:
        reasons.append(f"Refund of {triage.amount:,.0f} is above the {REFUND_LIMIT} limit for draft only handling")
    if triage.category == "complaint":
        reasons.append("Complaints are always reviewed by a person")
    if triage.category in NEEDS_POLICY and (draft is None or not draft.policy_ids):
        reasons.append("No company policy covers this question")
    if triage.category in {"sales_inquiry", "other"}:
        reasons.append("Not covered by the support policies, needs a colleague")
    return Review(bool(reasons), reasons)
