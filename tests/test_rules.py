import pytest

from app import rules
from app.models import Draft, Triage
from tests.conftest import make_email


def triage(category="other", amount=None):
    return Triage(category, "normal", "neutral", "s", [], amount)


def with_policy():
    return Draft("Re: x", "text", ["refunds"])


@pytest.mark.parametrize("text, label", [
    ("I will speak to my solicitor", "Legal language"),
    ("This is a chargeback request", "Legal language"),
    ("The motor started to smoke", "Possible safety issue"),
    ("Please delete my data under GDPR", "Privacy or data request"),
])
def test_sensitive_wording_always_needs_a_person(text, label):
    r = rules.review(make_email(text), triage("technical_support"), with_policy())
    assert r.needs_human and any(label in reason for reason in r.reasons)


def test_the_refund_limit_is_inclusive_of_the_limit_itself():
    e = make_email("refund please")
    assert not rules.review(e, triage("refund_request", rules.REFUND_LIMIT), with_policy()).needs_human
    over = rules.review(e, triage("refund_request", rules.REFUND_LIMIT + 1), with_policy())
    assert over.needs_human and "above the 500 limit" in over.reasons[0]


def test_a_complaint_is_always_reviewed():
    assert rules.review(make_email("not happy"), triage("complaint"), with_policy()).needs_human


def test_a_support_question_with_no_policy_needs_a_person():
    r = rules.review(make_email("where is it"), triage("shipping_status"), Draft("s", "t", []))
    assert r.needs_human and "No company policy" in r.reasons[0]


def test_sales_and_other_go_to_a_colleague():
    for category in ("sales_inquiry", "other"):
        assert rules.review(make_email("hello"), triage(category), Draft("s", "t", ["hours"])).needs_human


def test_spam_is_never_flagged_even_with_scary_words():
    assert not rules.review(make_email("my solicitor says click here to win"), triage("spam"), None).needs_human


def test_an_ordinary_covered_question_is_not_flagged():
    assert not rules.review(make_email("where is my order"), triage("shipping_status"), Draft("s", "t", ["shipping"])).needs_human
