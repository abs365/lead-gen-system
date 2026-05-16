import logging
import os
import re
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, Optional

import requests
from sqlalchemy.orm import Session

from models import Match, OutreachLog, Plumber

logger = logging.getLogger(__name__)

TENANT_ID = os.getenv("AZURE_TENANT_ID")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
SENDER_EMAIL = os.getenv("EMAIL_ACCOUNT")

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
TOKEN_URL_TEMPLATE = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"

BOUNCE_SUBJECTS = [
    "undeliverable",
    "delivery has failed",
    "delivery failure",
    "mail delivery failure",
    "returned mail",
    "non-delivery",
    "could not be delivered",
    "delivery status notification",
    "failure notice",
    "mail delivery failed",
    "message not delivered",
]

# Clear hard-bounce indicators only.
HARD_CODES = [
    "550",
    "551",
    "552",
    "553",
    "554",
    "5.1.1",
    "5.1.0",
    "5.2.1",
    "5.4.1",
    "5.7.1",
    "user unknown",
    "no such user",
    "unknown user",
    "mailbox not found",
    "mailbox unknown",
    "recipient not found",
    "recipient address rejected",
    "recipient address was rejected",
    "address rejected",
    "does not exist",
    "invalid recipient",
    "invalid address",
    "relay access denied",
]

# These should not normally blacklist immediately.
SOFT_CODES = [
    "mailbox full",
    "mailbox is full",
    "quota exceeded",
    "over quota",
    "temporarily unavailable",
    "temporary failure",
    "try again later",
    "greylisted",
    "rate limit",
    "too many messages",
    "connection timed out",
    "dns error",
    "deferred",
    "4.2.2",
    "4.3.0",
    "4.4.1",
    "4.4.2",
    "4.4.7",
]

# Prefer structured Delivery Status Notification fields first.
BOUNCE_PATTERNS = [
    r"Final-Recipient:\s*rfc822;\s*<?([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})>?",
    r"Original-Recipient:\s*rfc822;\s*<?([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})>?",
    r"X-Failed-Recipients:\s*<?([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})>?",
    r"Recipient address:\s*<?([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})>?",
    r"The email address\s*<?([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})>?",
    r"mailbox\s+<?([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})>?\s+(?:unknown|not found|does not exist)",
]

IGNORED_EMAIL_KEYWORDS = [
    "microsoft",
    "outlook",
    "postmaster",
    "mailer-daemon",
    "meritbold",
]


def _validate_config() -> Optional[str]:
    missing = []
    if not TENANT_ID:
        missing.append("AZURE_TENANT_ID")
    if not CLIENT_ID:
        missing.append("AZURE_CLIENT_ID")
    if not CLIENT_SECRET:
        missing.append("AZURE_CLIENT_SECRET")
    if not SENDER_EMAIL:
        missing.append("EMAIL_ACCOUNT")

    if missing:
        return f"Missing environment variable(s): {', '.join(missing)}"
    return None


def _get_token() -> Optional[str]:
    config_error = _validate_config()
    if config_error:
        logger.error(config_error)
        return None

    try:
        response = requests.post(
            TOKEN_URL_TEMPLATE.format(tenant_id=TENANT_ID),
            data={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "scope": "https://graph.microsoft.com/.default",
                "grant_type": "client_credentials",
            },
            timeout=15,
        )
        response.raise_for_status()
        return response.json().get("access_token")
    except requests.RequestException as exc:
        logger.exception("Failed to get Microsoft Graph token: %s", exc)
        return None


def _plain_text(html_or_text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html_or_text or "")
    text = re.sub(r"&nbsp;", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"&lt;", "<", text, flags=re.IGNORECASE)
    text = re.sub(r"&gt;", ">", text, flags=re.IGNORECASE)
    text = re.sub(r"&amp;", "&", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _is_bounce(subject: str, body: str, from_address: str = "") -> bool:
    subject_lower = (subject or "").lower()
    body_lower = (body or "").lower()
    from_lower = (from_address or "").lower()

    if any(keyword in subject_lower for keyword in BOUNCE_SUBJECTS):
        return True

    if any(keyword in body_lower for keyword in BOUNCE_SUBJECTS):
        return True

    if "mailer-daemon" in from_lower or "postmaster" in from_lower:
        return True

    return False


def _is_soft_bounce(body: str) -> bool:
    body_lower = (body or "").lower()
    return any(code.lower() in body_lower for code in SOFT_CODES)


def _is_hard_bounce(body: str) -> bool:
    body_lower = (body or "").lower()

    if _is_soft_bounce(body_lower):
        return False

    return any(code.lower() in body_lower for code in HARD_CODES)


def _normalise_email(email: str) -> str:
    return email.lower().strip().strip("<>").strip(".,;:'\")[]{}")


def _is_ignored_email(email: str) -> bool:
    email_lower = _normalise_email(email)
    sender = (SENDER_EMAIL or "").lower()

    if not email_lower or email_lower == sender:
        return True

    return any(keyword in email_lower for keyword in IGNORED_EMAIL_KEYWORDS)


def _extract_failed_email(body: str) -> Optional[str]:
    for pattern in BOUNCE_PATTERNS:
        match = re.search(pattern, body or "", flags=re.IGNORECASE)
        if not match:
            continue

        email = _normalise_email(match.group(1))
        if email and "@" in email and not _is_ignored_email(email):
            return email

    return None


def _get_from_address(message: Dict[str, Any]) -> str:
    return (
        message.get("from", {})
        .get("emailAddress", {})
        .get("address", "")
    )


def _fetch_messages(token: str, since: str, max_pages: int = 10) -> Iterable[Dict[str, Any]]:
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{GRAPH_BASE_URL}/users/{SENDER_EMAIL}/mailFolders/inbox/messages"
    params = {
        "$filter": f"receivedDateTime ge {since}",
        "$select": "id,subject,body,from,receivedDateTime",
        "$top": 100,
        "$orderby": "receivedDateTime desc",
    }

    pages_read = 0
    while url and pages_read < max_pages:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()

        payload = response.json()
        for message in payload.get("value", []):
            yield message

        url = payload.get("@odata.nextLink")
        params = None
        pages_read += 1


def _mark_as_bounced(db: Session, email: str) -> bool:
    plumber = db.query(Plumber).filter(Plumber.email == email).first()
    if not plumber:
        logger.info("Hard bounce found, but plumber not found in database: %s", email)
        return False

    # Best option if these columns exist in your Plumber model.
    # If your model does not have these columns, the fallback below keeps the old behaviour.
    if hasattr(plumber, "is_blacklisted"):
        plumber.is_blacklisted = True
    if hasattr(plumber, "blacklisted_reason"):
        plumber.blacklisted_reason = "hard_bounce"
    if hasattr(plumber, "blacklisted_at"):
        plumber.blacklisted_at = datetime.utcnow()

    # Fallback for your current schema: remove the active email so it is not contacted again.
    # Keep this only if you do not have is_blacklisted/blacklisted_at fields yet.
    if not hasattr(plumber, "is_blacklisted"):
        plumber.email = None

    db.query(OutreachLog).filter(OutreachLog.email == email).update(
        {"status": "bounced"},
        synchronize_session=False,
    )

    db.query(Match).filter(
        Match.plumber_id == plumber.id,
        Match.outreach_sent == 0,
    ).update(
        {"outreach_sent": 1},
        synchronize_session=False,
    )

    logger.info("Marked hard bounce: %s", email)
    return True


def detect_bounces(db: Session, days_back: int = 7) -> Dict[str, Any]:
    """
    Detect hard-bounced emails from Microsoft 365 inbox messages.

    Returns a summary dictionary:
    {
        "success": True,
        "scanned": 100,
        "bounces_found": 3,
        "hard_bounces_found": 2,
        "soft_bounces_found": 1,
        "emails_blacklisted": 2
    }
    """
    token = _get_token()
    if not token:
        config_error = _validate_config()
        return {"success": False, "error": config_error or "Could not get Microsoft Graph token"}

    since = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%dT%H:%M:%SZ")

    scanned = 0
    bounces_found = 0
    hard_bounces_found = 0
    soft_bounces_found = 0
    emails_blacklisted = 0
    extracted_emails = set()

    try:
        for message in _fetch_messages(token, since):
            scanned += 1

            subject = message.get("subject") or ""
            from_address = _get_from_address(message)
            body = _plain_text(message.get("body", {}).get("content", ""))

            if not _is_bounce(subject, body, from_address):
                continue

            bounces_found += 1

            if _is_soft_bounce(body):
                soft_bounces_found += 1
                continue

            if not _is_hard_bounce(body):
                continue

            hard_bounces_found += 1

            failed_email = _extract_failed_email(body)
            if not failed_email:
                logger.warning("Hard bounce detected but failed email could not be extracted. Subject: %s", subject)
                continue

            if failed_email in extracted_emails:
                continue

            extracted_emails.add(failed_email)

            if _mark_as_bounced(db, failed_email):
                emails_blacklisted += 1

        db.commit()

        return {
            "success": True,
            "scanned": scanned,
            "bounces_found": bounces_found,
            "hard_bounces_found": hard_bounces_found,
            "soft_bounces_found": soft_bounces_found,
            "emails_blacklisted": emails_blacklisted,
        }

    except requests.RequestException as exc:
        db.rollback()
        logger.exception("Microsoft Graph error while detecting bounces: %s", exc)
        return {"success": False, "error": str(exc)}

    except Exception as exc:
        db.rollback()
        logger.exception("Unexpected error while detecting bounces: %s", exc)
        return {"success": False, "error": str(exc)}
