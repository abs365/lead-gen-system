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

BOUNCE_SUBJECTS = [
    "undeliverable", "delivery has failed", "delivery failure",
    "mail delivery failure", "returned mail", "non-delivery",
    "could not be delivered", "delivery status notification",
    "failure notice", "mail delivery failed", "message not delivered",
]

BOUNCE_PATTERNS = [
    r"recipient address:\\s*([a-zA-Z0-9._%+\\-]+@[a-zA-Z0-9.\\-]+\\.[a-zA-Z]{2,})",
    r"mailbox\\s+([a-zA-Z0-9._%+\\-]+@[a-zA-Z0-9.\\-]+\\.[a-zA-Z]{2,})\\s+unknown",
    r"<([a-zA-Z0-9._%+\\-]+@[a-zA-Z0-9.\\-]+\\.[a-zA-Z]{2,})>",
    r"([a-zA-Z0-9._%+\\-]+@[a-zA-Z0-9.\\-]+\\.[a-zA-Z]{2,})",
]

HARD_CODES = [
    "550", "551", "552", "553", "554",
    "5.1.1", "5.1.0", "5.7.1",
    "user unknown", "no such user", "mailbox not found",
    "does not exist", "relay access denied",
    "recipient not found", "mailbox unknown",
]


def _get_token():
    try:
        r = requests.post(
            f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token",
            data={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "scope": "https://graph.microsoft.com/.default",
                "grant_type": "client_credentials",
            },
            timeout=10,
        )
        return r.json().get("access_token") if r.status_code == 200 else None
    except Exception:
        return None


def _is_bounce(subject, body):
    s, b = subject.lower(), body.lower()
    return any(p in s or p in b for p in BOUNCE_SUBJECTS)


def _is_hard(body):
    b = body.lower()
    return any(c.lower() in b for c in HARD_CODES)


def _extract(body):
    sender = (SENDER_EMAIL or "").lower()
    for pat in BOUNCE_PATTERNS:
        for email in re.findall(pat, body, re.IGNORECASE):
            e = email.lower().strip()
            if e == sender:
                continue
            if "microsoft" in e or "outlook" in e or "meritbold" in e:
                continue
            if "@" in e and "." in e.split("@")[1]:
                return e
    return None


def _blacklist(db, email):
    p = db.query(Plumber).filter(Plumber.email == email).first()
    if not p:
        return False
    p.email = None
    db.query(OutreachLog).filter(OutreachLog.email == email).update(
        {"status": "bounced"}, synchronize_session=False
    )
    db.query(Match).filter(
        Match.plumber_id == p.id, Match.outreach_sent == 0
    ).update({"outreach_sent": 1}, synchronize_session=False)
    logger.info(f"Blacklisted: {email}")
    return True


def detect_bounces(db: Session) -> dict:
    token = _get_token()
    if not token:
        return {"success": False, "error": "No token"}
    since = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        r = requests.get(
            f"https://graph.microsoft.com/v1.0/users/{SENDER_EMAIL}/messages",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "$filter": f"receivedDateTime ge {since}",
                "$select": "subject,body,from",
                "$top": 100,
            },
            timeout=30,
        )
        if r.status_code != 200:
            return {"success": False, "error": str(r.status_code)}
        msgs = r.json().get("value", [])
    except Exception as e:
        return {"success": False, "error": str(e)}

    scanned = bounces = blacklisted = 0
    for msg in msgs:
        try:
            scanned += 1
            subj = msg.get("subject", "") or ""
            body = re.sub(r"<[^>]+>", " ", msg.get("body", {}).get("content", "") or "")
            body = re.sub(r"\\s+", " ", body).strip()
            if not _is_bounce(subj, body):
                continue
            bounces += 1
            if not _is_hard(body):
                continue
            em = _extract(body)
            if not em:
                continue
            if _blacklist(db, em):
                blacklisted += 1
        except Exception:
            continue
    db.commit()
    return {
        "success": True,
        "scanned": scanned,
        "bounces_found": bounces,
        "emails_blacklisted": blacklisted,
    }
'''

with open("services/bounce_handler.py", "w", encoding="utf-8") as f:
    f.write(content)
print("bounce_handler.py written successfully")