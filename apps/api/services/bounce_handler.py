cat > services/bounce_handler.py << 'ENDOFFILE'
"""
Bounce handler service.
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

BOUNCE_SUBJECT_PATTERNS = [
    "undeliverable", "delivery has failed", "delivery failure",
    "mail delivery failure", "returned mail", "non-delivery",
    "could not be delivered", "delivery status notification",
    "failure notice", "mail delivery failed", "message not delivered",
]

BOUNCE_EMAIL_PATTERNS = [
    r"recipient address:\s*([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})",
    r"recipient:\s*([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})",
    r"mailbox\s+([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})\s+unknown",
    r"<([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})>",
    r"([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})",
]

HARD_BOUNCE_CODES = [
    "550", "551", "552", "553", "554",
    "5.1.0", "5.1.1", "5.1.2", "5.1.3", "5.1.6", "5.1.10",
    "5.7.1", "user unknown", "no such user", "mailbox not found",
    "does not exist", "invalid address", "address rejected",
    "relay access denied", "recipient not found", "mailbox unknown",
]


def _get_token():
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
        return None
    except Exception:
        return None


def _is_bounce(subject, body):
    subject_lower = subject.lower()
    body_lower = body.lower()
    return any(p in subject_lower or p in body_lower for p in BOUNCE_SUBJECT_PATTERNS)


def _is_hard_bounce(body):
    body_lower = body.lower()
    return any(code.lower() in body_lower for code in HARD_BOUNCE_CODES)


def _extract_bounced_email(body):
    sender = (SENDER_EMAIL or "").lower()
    for pattern in BOUNCE_EMAIL_PATTERNS:
        matches = re.findall(pattern, body, re.IGNORECASE)
        for email in matches:
            email = email.lower().strip()
            if email == sender:
                continue
            if "microsoft" in email or "outlook" in email or "meritbold" in email:
                continue
            if "@" in email and "." in email.split("@")[1]:
                return email
    return None


def _blacklist_plumber_email(db, email):
    plumber = db.query(Plumber).filter(Plumber.email == email).first()
    if not plumber:
        return False
    plumber.email = None
    db.query(OutreachLog).filter(OutreachLog.email == email).update({"status": "bounced"}, synchronize_session=False)
    db.query(Match).filter(Match.plumber_id == plumber.id, Match.outreach_sent == 0).update({"outreach_sent": 1}, synchronize_session=False)
    logger.info(f"Blacklisted: {email}")
    return True


def detect_bounces(db: Session) -> dict:
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
        resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, params=params, timeout=30)
        if resp.status_code != 200:
            return {"success": False, "error": f"Graph API error: {resp.status_code}"}
        messages = resp.json().get("value", [])
    except Exception as e:
        return {"success": False, "error": str(e)}

    scanned = bounces_found = emails_blacklisted = 0

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
                continue

            bounced_email = _extract_bounced_email(body_clean)
            if not bounced_email:
                continue

            if _blacklist_plumber_email(db, bounced_email):
                emails_blacklisted += 1
        except Exception as e:
            logger.error(f"Bounce error: {e}")
            continue

    db.commit()
    return {"success": True, "scanned": scanned, "bounces_found": bounces_found, "emails_blacklisted": emails_blacklisted}
ENDOFFILE
# updated
