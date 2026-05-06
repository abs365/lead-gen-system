import os
import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models import Plumber, OutreachLog, Match

IMAP_HOST = "outlook.office365.com"
IMAP_EMAIL = os.getenv("EMAIL_ACCOUNT")
IMAP_PASSWORD = os.getenv("AZURE_CLIENT_SECRET")

BOUNCE_SUBJECTS = [
    "undeliverable",
    "delivery failed",
    "delivery status notification",
    "mail delivery failed",
    "returned mail",
    "failure notice",
    "delivery failure",
    "non-delivery",
    "bounced",
]

def _decode_text(value) -> str:
    if not value:
        return ""
    decoded_parts = decode_header(value)
    result = ""
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            result += part.decode(encoding or "utf-8", errors="ignore")
        else:
            result += part
    return result.strip()

def clean_bounced_emails(db: Session) -> dict:
    if not IMAP_EMAIL or not IMAP_PASSWORD:
        return {"success": False, "message": "Missing IMAP credentials", "cleaned": 0}

    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST)
        mail.login(IMAP_EMAIL, IMAP_PASSWORD)
        mail.select("INBOX")

        since_date = (datetime.utcnow() - timedelta(days=7)).strftime("%d-%b-%Y")
        status, messages = mail.search(None, f'(SINCE "{since_date}")')

        if status != "OK":
            mail.logout()
            return {"success": False, "message": "IMAP search failed", "cleaned": 0}

        email_ids = messages[0].split()
        cleaned = 0
        bounced_emails = []

        for email_id in email_ids:
            try:
                status, data = mail.fetch(email_id, "(RFC822)")
                if status != "OK":
                    continue

                msg = email.message_from_bytes(data[0][1])
                subject = _decode_text(msg.get("Subject", "")).lower()

                if not any(b in subject for b in BOUNCE_SUBJECTS):
                    continue

                # Extract bounced email address from body
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            payload = part.get_payload(decode=True)
                            if payload:
                                body += payload.decode(errors="ignore")
                else:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        body = payload.decode(errors="ignore")

                # Find email addresses in bounce body
                import re
                emails_found = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", body)

                for bad_email in emails_found:
                    bad_email = bad_email.lower().strip()
                    if "meritbold" in bad_email or "microsoft" in bad_email:
                        continue

                    # Remove from plumbers
                    plumber = db.query(Plumber).filter(
                        Plumber.email == bad_email
                    ).first()
                    if plumber:
                        plumber.email = None
                        bounced_emails.append(bad_email)
                        cleaned += 1

                    # Mark outreach log as bounced
                    log = db.query(OutreachLog).filter(
                        OutreachLog.email == bad_email
                    ).first()
                    if log:
                        log.status = "bounced"

            except Exception:
                continue

        db.commit()
        mail.logout()

        return {
            "success": True,
            "cleaned": cleaned,
            "bounced_emails": bounced_emails[:20],
        }

    except Exception as e:
        return {"success": False, "message": str(e), "cleaned": 0}