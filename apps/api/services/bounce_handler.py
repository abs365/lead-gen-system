"""
Bounce handler service.
Reads NDR (non-delivery report) emails from the outreach inbox
and automatically nulls the email address on the plumber record.
"""
import os
import re
import requests
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models import Plumber, OutreachLog, Match

logger = logging.getLogger(__name__)

TENANT_ID = os.getenv("AZURE_TENANT_ID")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
SENDER_EMAIL = os.getenv("EMAIL_ACCOUNT")

# NDR subject patterns from mail servers
BOUNCE_SUBJECT_PATTERNS = [
    "undeliverable",
    "delivery has failed",
    "delivery failure",
    "mail delivery failure",
    "returned mail",
    "non-delivery",
    "could not be delivered",
    "couldn't be delivered",
    "delivery status notification",
    "failure notice",
    "mail delivery failed",
    "message not delivered",
    "relay access denied",
]

# NDR body patterns that contain the failed recipient
notepad "C:\Users\Admin\Workspace\projects\lead-gen-system\apps\api\services\bounce_handler.py"
# Hard bounce error codes — permanent failures
HARD_BOUNCE_CODES = [
    "550", "551", "552", "553", "554",
    "5.1.0", "5.1.1", "5.1.2", "5.1.3", "5.1.6", "5.1.10",
    "5.7.1",
    "user unknown", "no such user", "mailbox not found",
    "does not exist", "invalid address", "address rejected",
    "relay access denied", "recipient not found",
    "RecipientNotFound", "AddressNotFound",
]


def _get_token() -> str | None:
    try:
        url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
        resp = requests.post(url, data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials",
        }, timeout=10)
        if resp.status_code == 200:
            return resp.json().get("access_token")
        logger.error(f"Bounce handler token error: {resp.status_code}")
        return None
    except Exception as e:
        logger.error(f"Bounce handler token failed: {e}")
        return None


def _is_bounce(subject: str, body: str) -> bool:
    subject_lower = subject.lower()
    body_lower = body.lower()
    return any(p in subject_lower or p in body_lower for p in BOUNCE_SUBJECT_PATTERNS)


def _is_hard_bounce(body: str) -> bool:
    body_lower = body.lower()
    return any(code.lower() in body_lower for code in HARD_BOUNCE_CODES)


def _extract_bounced_email(body: str) -> str | None:
    """Extract the failed recipient email from bounce body."""
    for pattern in BOUNCE_EMAIL_PATTERNS:
        matches = re.findall(pattern, body, re.IGNORECASE)
        for email in matches:
            email = email.lower().strip()
            # Skip our own sending address and common false positives
            if email == (SENDER_EMAIL or "").lower():
                continue
            if "microsoft" in email or "outlook" in email:
                continue
            if "@" in email and "." in email.split("@")[1]:
                return email
    return None


def _blacklist_plumber_email(db: Session, email: str) -> bool:
    """
    Null the email on the plumber record and mark all unsent
    matches as sent so we never contact them again.
    """
    plumber = db.query(Plumber).filter(
        Plumber.email == email
    ).first()

    if not plumber:
        return False

    # Null the email so it's never used again
    plumber.email = None

    # Mark all outreach logs as bounced
    db.query(OutreachLog).filter(
        OutreachLog.email == email
    ).update({"status": "bounced"}, synchronize_session=False)

    # Block all unsent matches for this plumber
    # Block all unsent matches for this plumber
    db.query(Match).filter(
        Match.plumber_id == plumber.id,
        Match.outreach_sent == 0,
    ).update({"outreach_sent": 1}, synchronize_session=False)

    logger.info(f"Blacklisted bounced email: {email} (plumber: {plumber.name})")
    return True


def detect_bounces(db: Session) -> dict:
    """
    Scan the outreach inbox for NDR bounce emails
    and clean up bad plumber email addresses.
    """
    token = _get_token()
    if not token:
        return {"success": False, "error": "Failed to get access token"}

    since_date = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")

    url = f"https://graph.microsoft.com/v1.0/users/{SENDER_EMAIL}/messages"
    params = {
        "$filter": f"receivedDateTime ge {since_date}",
        "$select": "subject,body,from,receivedDateTime",
        "$top": 100,
    }

    try:
        resp = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            params=params,
            timeout=30,
        )
        if resp.status_code != 200:
            return {"success": False, "error": f"Graph API error: {resp.status_code}"}

        messages = resp.json().get("value", [])

    except Exception as e:
        return {"success": False, "error": str(e)}

    scanned = 0
    bounces_found = 0
    emails_blacklisted = 0

    for msg in messages:
        try:
            scanned += 1
            subject = msg.get("subject", "") or ""
            body_content = msg.get("body", {}).get("content", "") or ""

            body_clean = re.sub(r"<[^>]+>", " ", body_content)
            body_clean = re.sub(r"\s+", " ", body_clean).strip()

            if not _is_bounce(subject, body_clean):
                continue

            bounces_found += 1

            if not _is_hard_bounce(body_clean):
                logger.info(f"Soft bounce ignored: {subject}")
                continue

            bounced_email = _extract_bounced_email(body_clean)
            if not bounced_email:
                logger.warning(f"Could not extract email from bounce: {subject}")
                continue

            if _blacklist_plumber_email(db, bounced_email):
                emails_blacklisted += 1
                logger.info(f"Hard bounce processed: {bounced_email}")

        except Exception as e:
            logger.error(f"Bounce processing error: {e}")
            continue

    db.commit()

    return {
        "success": True,
        "scanned": scanned,
        "bounces_found": bounces_found,
        "emails_blacklisted": emails_blacklisted,
    }