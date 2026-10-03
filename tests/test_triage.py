import pytest

from app.triage import classify
from tests.conftest import make_email


@pytest.mark.parametrize("email_id, category, urgency, sentiment", [
    ("e1", "refund_request", "normal", "positive"),
    ("e2", "shipping_status", "normal", "neutral"),
    ("e3", "complaint", "high", "negative"),
    ("e4", "technical_support", "normal", "neutral"),
    ("e5", "billing", "normal", "neutral"),
    ("e6", "cancellation", "normal", "neutral"),
    ("e7", "sales_inquiry", "low", "neutral"),
    ("e8", "spam", "low", "neutral"),
    ("e9", "refund_request", "normal", "neutral"),
])
def test_sample_emails_are_sorted_correctly(samples, email_id, category, urgency, sentiment):
    t = classify(samples[email_id])
    assert (t.category, t.urgency, t.sentiment) == (category, urgency, sentiment)


def test_an_unclear_email_is_other():
    assert classify(make_email("Just saying hello to the team.")).category == "other"


def test_one_spam_phrase_alone_is_not_enough():
    assert classify(make_email("Click here to see the order status page you asked about.")).category != "spam"


def test_urgent_words_raise_urgency():
    assert classify(make_email("I need my invoice immediately for the audit.", "Invoice")).urgency == "high"


def test_summary_is_the_first_sentence_and_is_capped():
    t = classify(make_email("My desk wobbles. It started last week."))
    assert t.summary == "My desk wobbles."
    assert len(classify(make_email("word " * 100)).summary) <= 160
