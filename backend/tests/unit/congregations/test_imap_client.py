"""Tests for the IMAP message parsing helpers (no real IMAP connection).

See docs/plans/2026-07-13--clergy-email-updates.md.
"""

import os

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-min-32-characters-long-for-testing")
os.environ.setdefault("ALLOWED_HOSTS", '["localhost","127.0.0.1"]')
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from email import message_from_string
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.modules.congregations.imap_client import (
    extract_text_body,
    parse_authentication_results,
)


def test_extract_text_body_plain() -> None:
    msg = message_from_string("Content-Type: text/plain; charset=utf-8\n\nZmiana numeru telefonu na 600123456.")
    assert extract_text_body(msg) == "Zmiana numeru telefonu na 600123456."


def test_extract_text_body_prefers_plain_over_html() -> None:
    msg = MIMEMultipart("alternative")
    msg.attach(MIMEText("<p>Zmiana <b>adresu</b></p>", "html", "utf-8"))
    msg.attach(MIMEText("Zmiana adresu", "plain", "utf-8"))
    assert extract_text_body(msg) == "Zmiana adresu"


def test_extract_text_body_falls_back_to_stripped_html() -> None:
    msg = MIMEMultipart("alternative")
    msg.attach(MIMEText("<p>Nowy adres: <b>ul. Kwiatowa 5</b></p>", "html", "utf-8"))
    assert extract_text_body(msg) == "Nowy adres: ul. Kwiatowa 5"


def test_extract_text_body_skips_attachments() -> None:
    msg = MIMEMultipart()
    body = MIMEText("Treść wiadomości", "plain", "utf-8")
    msg.attach(body)
    attachment = MIMEText("nie to", "plain", "utf-8")
    attachment.add_header("Content-Disposition", "attachment", filename="skan.txt")
    msg.attach(attachment)
    assert extract_text_body(msg) == "Treść wiadomości"


def test_parse_authentication_results_pass() -> None:
    msg = message_from_string("Authentication-Results: mx.example.com;\n" " spf=pass smtp.mailfrom=pastor@example.com;\n" " dkim=pass header.d=example.com;\n" " dmarc=pass header.from=example.com\n\nBody")
    result = parse_authentication_results(msg)
    assert result == {"spf": "pass", "dkim": "pass", "dmarc": "pass"}


def test_parse_authentication_results_missing_header() -> None:
    msg = message_from_string("Subject: no auth header\n\nBody")
    result = parse_authentication_results(msg)
    assert result == {"spf": None, "dkim": None, "dmarc": None}


def test_parse_authentication_results_fail() -> None:
    msg = message_from_string("Authentication-Results: mx.example.com; spf=fail; dkim=none; dmarc=fail\n\nBody")
    result = parse_authentication_results(msg)
    assert result == {"spf": "fail", "dkim": "none", "dmarc": "fail"}


def test_parse_authentication_results_keeps_first_verdict_across_relays() -> None:
    msg = message_from_string("Authentication-Results: relay1.example.com; spf=pass\n" "Authentication-Results: relay2.example.com; spf=fail\n\nBody")
    result = parse_authentication_results(msg)
    assert result["spf"] == "pass"
