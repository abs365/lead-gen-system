import os
import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from models import OutreachLog
from services.scoring import calculate_lead_score


# =========================
# ENV CONFIG (NO SETTINGS OBJECT)
# =========================
IMAP_EMAIL = os.getenv("EMAIL_ACCOUNT")
IMAP_PASSWORD = os.getenv("EMAIL_PASSWORD")  # you must add this
IMAP_HOST = os.getenv("IMAP_HOST", "outlook.office365.com")
IMAP_FOLDER = os.getenv("IMAP_FOLDER", "INBOX")


# =========================
# HELPERS
# =========================
def _decode_text(value: Optional[str]) -> str:
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


def _extract_email_address(from_header: str) -> str:
    return email.utils.parseaddr(from_header)[1].lower().strip()


def _get_email_body(message) -> str:
    try:
        if message.is_multipart():
            for part in message.walk():
                content_type = part.get_content_type()
                disposition = str(part.get("Content-Disposition"))

                if content_type == "text/plain" and "attachment" not in disposition:
                    payload = part.get_payload(decode=True)
                    if payload:
                        return payload.decode(errors="ignore")
        else:
            payload = message.get_payload(decode=True)
            if payload:
                return payload.decode(errors="ignore")
    except Exception:
        return ""

    return ""


# =========================
# MAIN FUNCTION
# =========================
def detect_gmail_replies(db: Session) -> dict:
    # --- VALIDATION ---
    if not IMAP_EMAIL or not IMAP_PASSWORD:
        return {
            "success": False,
            "message": "Missing IMAP credentials (.env)",
            "scanned_emails": 0,
            "matched_replies": 0,
        }

    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST)
        mail.login(IMAP_EMAIL, IMAP_PASSWORD)
        mail.select(IMAP_FOLDER)

        since_date = (datetime.utcnow() - timedelta(days=14)).strftime("%d-%b-%Y")
        status, messages = mail.search(None, f'(SINCE "{since_date}")')

        if status != "OK":
            mail.logout()
            return {
                "success": False,
                "message": "IMAP search failed",
                "scanned_emails": 0,
                "matched_replies": 0,
            }

        email_ids = messages[0].split()

        scanned = 0
        matched_replies = 0

        for email_id in email_ids:
            try:
                status, data = mail.fetch(email_id, "(RFC822)")

                if status != "OK":
                    continue

                scanned += 1

                msg = email.message_from_bytes(data[0][1])

                from_header = _decode_text(msg.get("From"))
                sender_email = _extract_email_address(from_header)

                subject = _decode_text(msg.get("Subject"))
                body = _get_email_body(msg)

                if not sender_email:
                    continue

                # =========================
                # MATCHING LOGIC
                # =========================
                lead = (
                    db.query(OutreachLog)
                    .filter(OutreachLog.email == sender_email)
                    .first()
                )

                # fallback: match by domain
                if not lead and "@" in sender_email:
                    sender_domain = sender_email.split("@")[1]

                    leads = db.query(OutreachLog).all()

                    for l in leads:
                        if l.email and "@" in l.email:
                            lead_domain = l.email.split("@")[1]
                            if sender_domain == lead_domain:
                                lead = l
                                break

                if not lead:
                    continue

                # =========================
                # UPDATE LEAD
                # =========================
                # =========================
                # UPDATE LEAD
                # =========================

                # CHECK FOR UNSUBSCRIBE
                body_lower = body.lower().strip()
                subject_lower = subject.lower().strip()
                is_stop = (
                    body_lower.startswith("stop") or
                    "unsubscribe" in body_lower or
                    "remove me" in body_lower or
                    "stop" == body_lower.strip() or
                    "stop" in subject_lower
                )

                if is_stop:
                    lead.status = "unsubscribed"
                    lead.replied = 1
                    if hasattr(lead, "reply_body"):
                        lead.reply_body = body[:5000]
                    if hasattr(lead, "replied_at"):
                        lead.replied_at = datetime.utcnow()
                    matched_replies += 1

                    # Also flag the plumber so future outreach skips them
                    from models import Plumber
                    plumber = db.query(Plumber).filter(
                        Plumber.email == sender_email
                    ).first()
                    if plumber:
                        plumber.is_commercial = 0  # repurpose flag to block outreach

                    continue

                lead.replied = 1
                lead.status = "interested"

                if hasattr(lead, "reply_subject"):
                    lead.reply_subject = subject

                if hasattr(lead, "reply_body"):
                    lead.reply_body = body[:5000]

                if hasattr(lead, "replied_at"):
                    lead.replied_at = datetime.utcnow()

                lead.lead_score = calculate_lead_score(lead)

                matched_replies += 1

            except Exception:
                continue  # skip broken emails safely

        db.commit()
        mail.logout()

        return {
            "success": True,
            "message": "Reply detection completed",
            "scanned_emails": scanned,
            "matched_replies": matched_replies,
        }

    except Exception as e:
        return {
            "success": False,
            "message": str(e),
            "scanned_emails": 0,
            "matched_replies": 0,
        }