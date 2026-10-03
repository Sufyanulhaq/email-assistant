import pytest

from app.draft_rules import first_name, reply_subject
from app.pipeline import process
from tests.conftest import make_email


def draft_for(offline, email):
    return process(email, offline).draft


def test_a_reply_quotes_the_matching_policy_word_for_word(offline, pols, samples):
    d = draft_for(offline, samples["e1"])
    assert pols["refunds"].text in d.text and d.policy_ids == ["refunds"]
    assert d.text.startswith("Hi Priya,") and d.text.endswith("Kind regards,\nBrightline Support")
    assert "NW-10482" in d.text


@pytest.mark.parametrize("email_id, policy", [("e2", "shipping"), ("e4", "password"), ("e5", "invoices"), ("e6", "cancellation")])
def test_each_category_uses_its_own_policy(offline, pols, samples, email_id, policy):
    d = draft_for(offline, samples[email_id])
    assert d.policy_ids == [policy] and pols[policy].text in d.text


def test_a_broken_desk_uses_the_warranty_not_the_password_policy(offline):
    d = draft_for(offline, make_email("The motor on my desk is broken and not working.", "Broken motor"))
    assert d.policy_ids == ["warranty"]


def test_a_technical_question_with_no_matching_policy_gets_a_holding_reply(offline):
    d = draft_for(offline, make_email("The app shows an error when I open it.", "Error"))
    assert d.policy_ids == ["hours"] and "passed it to a colleague" in d.text


def test_a_complaint_gets_an_apology_and_a_promise_of_nothing_specific(offline, samples):
    text = draft_for(offline, samples["e3"]).text
    assert "I am sorry for the trouble" in text and "refund" not in text.lower() and "compensation" not in text.lower()


def test_spam_gets_no_reply(offline, samples):
    assert draft_for(offline, samples["e8"]) is None


def test_the_reply_never_invents_an_order_number(offline):
    d = draft_for(offline, make_email("I would like to return my desk please, I want a refund.", "Return"))
    assert "NW-" not in d.text and "your order number" in d.text


def test_names_and_subjects():
    assert first_name(make_email("hi", sender="priya.nair@example.com")) == "Priya"
    assert first_name(make_email("hi", sender="Dr. Sam Lee <s@x.co>")) == "Sam"
    assert first_name(make_email("hi", sender="Mrs <s@x.co>")) == "there"
    assert reply_subject("Hello") == "Re: Hello" and reply_subject("RE: Hello") == "RE: Hello"
