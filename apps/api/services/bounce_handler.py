import os
import re
import requests
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models import Plumber, OutreachLog

TENANT_ID = os.getenv("AZURE_TENANT_ID")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
SENDER_EMAIL = os.getenv("EMAIL_ACCOUNT")

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

def get_access_token():
    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials",
    }
    response = requests.post(url, data=data)
    if response.status_code != 200:
        raise Exception(f"Token error: {response.text}")
    return response.json()["access_token"]

def clean_bounced_emails(db: Session) -> dict:
    try:
        token = get_access_token()
        headers = {"Authorization": f"Bearer {token}"}

        since_date = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
        url = f"https://graph.microsoft.com/v1.0/users/{SENDER_EMAIL}/messages"
        params = {
            "$filter": f"receivedDateTime ge {since_date}",
            "$select": "subject,body",
            "$top": 200,
        }

        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            return {"success": False, "message": response.text, "cleaned": 0}

        messages = response.json().get("value", [])
        cleaned = 0
        bounced_emails = []

        for msg in messages:
            subject = (msg.get("subject") or "").lower()

            if not any(b in subject for b in BOUNCE_SUBJECTS):
                continue

            body = msg.get("body", {}).get("content", "")
            emails_found = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", body)

            for bad_email in emails_found:
                bad_email = bad_email.lower().strip()
                if any(x in bad_email for x in ["meritbold", "microsoft", "outlook", "example", "schema"]):
                    continue

                plumber = db.query(Plumber).filter(Plumber.email == bad_email).first()
                if plumber:
                    plumber.email = None
                    bounced_emails.append(bad_email)
                    cleaned += 1

                log = db.query(OutreachLog).filter(OutreachLog.email == bad_email).first()
                if log:
                    log.status = "bounced"

        db.commit()

        return {
            "success": True,
            "cleaned": cleaned,
            "bounced_emails": bounced_emails[:20],
        }

    except Exception as e:
        return {"success": False, "message": str(e), "cleaned": 0}