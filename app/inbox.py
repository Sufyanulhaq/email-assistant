"""Turns raw mail into an Email. Real mail is messy, so this takes the plain text part when there is
one, falls back to stripping tags from HTML, and drops quoted earlier messages."""
from __future__ import annotations

import json
import re
import uuid
from email import message_from_bytes, policy
from email.utils import parseaddr
from pathlib import Path

from .models import Email

MAX_BODY = 5000
MAX_SUBJECT = 200
MAX_RAW = 2 * 1024 * 1024


class EmailError(ValueError):
    """The mail cannot be read. The message is safe to show to the user."""


def _clean_body(text: str) -> str:
    lines = []
    for line in text.replace("\r\n", "\n").split("\n"):
        if re.match(r"^On .{5,120} wrote:\s*$", line.strip()) or line.strip().startswith("-----Original Message"):
            break  # everything below is the earlier thread
        if line.lstrip().startswith(">"):
            continue
        lines.append(line.rstrip())
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()[:MAX_BODY]


def _strip_html(markup: str) -> str:
    markup = re.sub(r"(?is)<(script|style).*?</\1>", " ", markup)
    markup = re.sub(r"(?i)<br\s*/?>|</p>|</div>", "\n", markup)
    return re.sub(r"[ \t]+", " ", re.sub(r"<[^>]+>", " ", markup))


def build(sender: str, subject: str, body: str, date: str = "", email_id: str | None = None) -> Email:
    name, address = parseaddr(sender)
    if "@" not in address:
        raise EmailError("The sender needs a valid email address.")
    body = _clean_body(body)
    if not body:
        raise EmailError("The email has no text.")
    return Email(
        id=email_id or uuid.uuid4().hex[:8],
        sender_name=name or address.split("@")[0],
        sender_email=address.lower(),
        subject=" ".join(subject.split())[:MAX_SUBJECT] or "(no subject)",
        date=date,
        body=body,
    )


def from_eml(data: bytes) -> Email:
    if len(data) > MAX_RAW:
        raise EmailError("This file is larger than 2 MB.")
    try:
        message = message_from_bytes(data, policy=policy.default)
        part = message.get_body(preferencelist=("plain", "html"))
        text = part.get_content() if part is not None else ""
        if part is not None and part.get_content_type() == "text/html":
            text = _strip_html(text)
    except Exception as exc:  # the email package raises many kinds of error on damaged files
        raise EmailError("This file could not be read as an email.") from exc
    return build(str(message.get("From", "")), str(message.get("Subject", "")), text, str(message.get("Date", "")))


def load_samples(path: Path) -> list[Email]:
    return [build(e["from"], e["subject"], e["body"], e["date"], e["id"]) for e in json.loads(path.read_text())]
