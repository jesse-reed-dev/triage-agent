"""
Sends the digest email through Gmail SMTP using the Python standard library —
no SendGrid account, no extra dependency.

Auth uses a Gmail *app password* (not the normal account password): generate
one at https://myaccount.google.com/apppasswords (requires 2FA on the account)
and put it in .env. Regular passwords don't work over SMTP anymore.
"""

import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

# ─── Config ───────────────────────────────────────────────────────────────────

load_dotenv()

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
DIGEST_TO = os.getenv("DIGEST_TO") or GMAIL_ADDRESS  # defaults to sending to yourself

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465  # implicit TLS
TIMEOUT_SECONDS = 30


# ─── Sending ──────────────────────────────────────────────────────────────────

def email_configured() -> bool:
    """
    True if .env has what we need to send. When False, the pipeline falls back
    to treating the report file write as delivery instead of failing the run.
    """
    return bool(GMAIL_ADDRESS and GMAIL_APP_PASSWORD)


def send_digest(subject: str, text_body: str, html_body: str) -> bool:
    """
    Sends a multipart email (plain text + HTML alternative) and returns
    True on success. Returns False on any SMTP or network failure — the
    caller uses this as the delivery signal that gates mark_seen, so a
    failed send must never look like a success.
    """
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = DIGEST_TO
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=TIMEOUT_SECONDS) as smtp:
            smtp.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            smtp.send_message(msg)
    except (smtplib.SMTPException, OSError) as e:
        print(f"  Email send failed: {e}")
        return False

    return True
