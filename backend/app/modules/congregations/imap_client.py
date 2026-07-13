"""IMAP client for polling the clergy e-mail update mailbox.

Uses the stdlib `imaplib`/`email` rather than adding a dependency — this only
needs to fetch a handful of messages per poll from one dedicated mailbox. All
methods are blocking (imaplib has no async API); callers running inside an
event loop should wrap calls in `asyncio.to_thread`.

See docs/plans/2026-07-13--clergy-email-updates.md.
"""

from __future__ import annotations

import imaplib
import re
from dataclasses import dataclass
from email import message_from_bytes
from email.header import decode_header
from email.message import Message
from email.utils import parseaddr

from app.core.config import EmailImportSettings

_AUTH_RESULT_RE = re.compile(r"\b(spf|dkim|dmarc)=([a-z]+)", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")
_SCRIPT_STYLE_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE)


@dataclass
class InboundEmail:
    imap_uid: str
    message_id: str | None
    from_address: str
    subject: str
    text_body: str
    auth_spf: str | None
    auth_dkim: str | None
    auth_dmarc: str | None


def _decode_header_value(value: str | None) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    decoded = []
    for text, encoding in parts:
        if isinstance(text, bytes):
            decoded.append(text.decode(encoding or "utf-8", errors="replace"))
        else:
            decoded.append(text)
    return "".join(decoded)


def _decode_part(part: Message) -> str:
    payload = part.get_payload(decode=True)
    if not isinstance(payload, bytes):
        return ""
    charset = part.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="replace")
    except LookupError:
        return payload.decode("utf-8", errors="replace")


def _strip_html(html: str) -> str:
    text = _SCRIPT_STYLE_RE.sub("", html)
    text = _TAG_RE.sub(" ", text)
    return _WHITESPACE_RE.sub(" ", text).strip()


def extract_text_body(msg: Message) -> str:
    """Prefers a text/plain part; falls back to a tag-stripped text/html part."""
    if not msg.is_multipart():
        body = _decode_part(msg)
        return body if msg.get_content_type() == "text/plain" else _strip_html(body)

    plain: str | None = None
    html: str | None = None
    for part in msg.walk():
        if part.get_content_disposition() == "attachment":
            continue
        content_type = part.get_content_type()
        if content_type == "text/plain" and plain is None:
            plain = _decode_part(part)
        elif content_type == "text/html" and html is None:
            html = _decode_part(part)

    if plain:
        return plain
    if html:
        return _strip_html(html)
    return ""


def parse_authentication_results(msg: Message) -> dict[str, str | None]:
    """Parses SPF/DKIM/DMARC verdicts from the Authentication-Results header(s).

    Added by the *receiving* mail server, not the sender — this is the
    anti-spoofing signal the sender authorization gate relies on. A message
    can pass through multiple relays, each prepending its own header, so we
    keep the first (topmost / most recent) verdict per mechanism.
    """
    results: dict[str, str | None] = {"spf": None, "dkim": None, "dmarc": None}
    for header_value in msg.get_all("Authentication-Results", []):
        for match in _AUTH_RESULT_RE.finditer(header_value):
            mechanism, verdict = match.group(1).lower(), match.group(2).lower()
            if results.get(mechanism) is None:
                results[mechanism] = verdict
    return results


class ImapClient:
    """Synchronous IMAP client, scoped to one poll cycle (`with` block).

    Fetches use BODY.PEEK[] so messages are *not* auto-marked \\Seen on
    fetch; the caller marks a message seen explicitly (`mark_seen`) only
    after it has been safely persisted, so a crash mid-processing leaves it
    for retry on the next poll instead of silently dropping it.
    """

    def __init__(self, settings: EmailImportSettings):
        self._settings = settings
        self._conn: imaplib.IMAP4 | None = None

    def __enter__(self) -> ImapClient:
        conn_cls = imaplib.IMAP4_SSL if self._settings.imap_use_ssl else imaplib.IMAP4
        conn = conn_cls(self._settings.imap_host, self._settings.imap_port)
        conn.login(self._settings.imap_user, self._settings.imap_password)
        conn.select(self._settings.imap_mailbox)
        self._conn = conn
        return self

    def __exit__(self, *exc_info: object) -> None:
        if self._conn is None:
            return
        try:
            self._conn.close()
        except imaplib.IMAP4.error:
            pass
        finally:
            self._conn.logout()
            self._conn = None

    def fetch_unseen(self) -> list[InboundEmail]:
        conn = self._require_conn()
        status, data = conn.search(None, "UNSEEN")
        if status != "OK" or not data or not data[0]:
            return []

        emails: list[InboundEmail] = []
        for uid_bytes in data[0].split():
            status, msg_data = conn.fetch(uid_bytes, "(BODY.PEEK[])")
            if status != "OK" or not msg_data or not isinstance(msg_data[0], tuple):
                continue
            raw = msg_data[0][1]
            msg = message_from_bytes(raw)
            auth = parse_authentication_results(msg)
            emails.append(
                InboundEmail(
                    imap_uid=uid_bytes.decode("ascii"),
                    message_id=msg.get("Message-ID"),
                    from_address=parseaddr(msg.get("From", ""))[1].strip().lower(),
                    subject=_decode_header_value(msg.get("Subject")),
                    text_body=extract_text_body(msg),
                    auth_spf=auth["spf"],
                    auth_dkim=auth["dkim"],
                    auth_dmarc=auth["dmarc"],
                )
            )
        return emails

    def mark_seen(self, uid: str) -> None:
        conn = self._require_conn()
        conn.store(uid, "+FLAGS", "\\Seen")

    def _require_conn(self) -> imaplib.IMAP4:
        if self._conn is None:
            raise RuntimeError("ImapClient must be used as a context manager")
        return self._conn
