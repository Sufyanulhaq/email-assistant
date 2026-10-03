from email.message import EmailMessage

import pytest

from app import inbox
from app.inbox import EmailError


def test_build_cleans_the_sender_subject_and_body():
    e = inbox.build('"Priya Nair" <Priya.Nair@Example.com>', "  Return   of desk ", "Hello\r\n\r\n\r\n\r\nThanks", "d", "x1")
    assert (e.sender_name, e.sender_email, e.subject) == ("Priya Nair", "priya.nair@example.com", "Return of desk")
    assert e.body == "Hello\n\nThanks"


def test_a_sender_without_a_name_uses_the_address():
    assert inbox.build("sam@example.com", "s", "body").sender_name == "sam"


@pytest.mark.parametrize("sender, body", [("not an address", "hi"), ("a@b.co", "   "), ("", "hi")])
def test_unusable_mail_is_refused_with_a_reason(sender, body):
    with pytest.raises(EmailError):
        inbox.build(sender, "s", body)


def test_quoted_earlier_messages_are_dropped():
    body = "Yes please go ahead.\n\n> old text from before\n> more old text\n\nOn Mon, 28 Sep 2026 at 10:00, Support <s@x.co> wrote:\nOur earlier reply"
    assert inbox.build("a@b.co", "s", body).body == "Yes please go ahead."


def test_body_and_subject_are_capped():
    e = inbox.build("a@b.co", "s" * 500, "word " * 5000)
    assert len(e.body) <= inbox.MAX_BODY and len(e.subject) <= inbox.MAX_SUBJECT


def _eml(plain=None, html=None, subject="Hello", sender="Sam Lee <sam@example.com>"):
    m = EmailMessage()
    m["From"], m["Subject"], m["Date"] = sender, subject, "Thu, 01 Oct 2026 09:00:00 +0000"
    if plain is not None:
        m.set_content(plain)
        if html is not None:
            m.add_alternative(html, subtype="html")
    else:
        m.set_content(html, subtype="html")
    return bytes(m)


def test_eml_plain_text():
    e = inbox.from_eml(_eml(plain="Where is my order?"))
    assert (e.sender_email, e.subject, e.body) == ("sam@example.com", "Hello", "Where is my order?")


def test_eml_prefers_the_plain_part_of_a_multipart():
    assert inbox.from_eml(_eml(plain="plain version", html="<p>html version</p>")).body == "plain version"


def test_eml_html_only_is_stripped_to_text():
    e = inbox.from_eml(_eml(html="<html><style>p{color:red}</style><body><p>Please <b>cancel</b> it</p><script>alert(1)</script></body></html>"))
    assert "Please cancel it" in " ".join(e.body.split()) and "alert" not in e.body and "color" not in e.body


def test_eml_garbage_is_refused():
    with pytest.raises(EmailError):
        inbox.from_eml(b"\x00\x01 this is not mail")


def test_eml_too_large_is_refused():
    with pytest.raises(EmailError, match="2 MB"):
        inbox.from_eml(b"x" * (inbox.MAX_RAW + 1))


def test_the_sample_inbox_loads(samples):
    assert sorted(samples) == [f"e{i}" for i in range(1, 10)]
