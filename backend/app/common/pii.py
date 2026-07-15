"""Helpers for keeping personal data out of logs."""


def mask_email(email: str | None) -> str:
    """Mask an e-mail address for safe logging, e.g. 'ja***@example.com'.

    Keeps enough of the local part to correlate log lines during debugging
    without writing the full address (and therefore the person's identity)
    to plaintext application logs.
    """
    if not email or "@" not in email:
        return "***"
    local, _, domain = email.partition("@")
    visible = local[:2]
    return f"{visible}***@{domain}"
