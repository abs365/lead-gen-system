import os
import re
import requests
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models import OutreachLog, Plumber, Match
from services.scoring import calculate_lead_score

TENANT_ID = os.getenv("AZURE_TENANT_ID")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
SENDER_EMAIL = os.getenv("EMAIL_ACCOUNT")


MANUAL_UNSUBSCRIBE_EMAILS = [
    "info@boilerandheatingcare.com",
]


def process_manual_unsubscribes(db: Session) -> dict:
    processed = []
    for email in MANUAL_UNSUBSCRIBE_EMAILS:
        hard_unsubscribe(db, email.lower().strip())
        processed.append(email)
    return {"processed": processed, "count": len(processed)}


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


def hard_unsubscribe(db: Session, sender_email: str):
    # 1. Mark ALL outreach logs for this email as unsubscribed
    db.query(OutreachLog).filter(
        OutreachLog.email == sender_email
    ).update({"status": "unsubscribed", "replied": 1}, synchronize_session=False)

    # 2. Find plumber and block completely
    plumber = db.query(Plumber).filter(
        Plumber.email == sender_email
    ).first()

    if plumber:
        # Block from future outreach
        plumber.is_commercial = 0
        # Mark all their unsent matches as sent so they won't be emailed again
        db.query(Match).filter(
            Match.plumber_id == plumber.id,
            Match.outreach_sent == 0
        ).update({"outreach_sent": 1}, synchronize_session=False)

    db.commit()


def detect_gmail_replies(db: Session) -> dict:
    try:
        token = get_access_token()
        headers = {"Authorization": f"Bearer {token}"}

        since_date = (datetime.utcnow() - timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%SZ")
        url = f"https://graph.microsoft.com/v1.0/users/{SENDER_EMAIL}/messages"
        params = {
            "$filter": f"receivedDateTime ge {since_date}",
            "$select": "subject,body,from",
            "$top": 200,
        }

        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            return {
                "success": False,
                "message": response.text,
                "scanned_emails": 0,
                "matched_replies": 0,
            }

        messages = response.json().get("value", [])
        scanned = 0
        matched_replies = 0
        processed_emails = set()

        for msg in messages:
            try:
                scanned += 1

                sender_email = msg.get("from", {}).get("emailAddress", {}).get("address", "").lower().strip()
                subject = msg.get("subject", "") or ""
                body = msg.get("body", {}).get("content", "") or ""
                body_clean = re.sub(r"<[^>]+>", " ", body).strip()
                body_lower = body_clean.lower().strip()
                subject_lower = subject.lower().strip()

                if not sender_email or sender_email == SENDER_EMAIL.lower():
                    continue

                is_stop = (
                    body_lower.strip() == "stop" or
                    body_lower.startswith("stop") or
                    "unsubscribe" in body_lower or
                    "remove me" in body_lower or
                    "please stop" in body_lower or
                    "stop sending" in body_lower or
                    "stop emailing" in body_lower or
                    "excessive" in body_lower or
                    "do not contact" in body_lower or
                    "stop" in subject_lower
                )

                if is_stop:
                    # Only process once per email address
                    if sender_email not in processed_emails:
                        hard_unsubscribe(db, sender_email)
                        processed_emails.add(sender_email)
                        matched_replies += 1
                    continue

                # Find matching lead for YES replies
                lead = db.query(OutreachLog).filter(
                    OutreachLog.email == sender_email
                ).first()

                if not lead and "@" in sender_email:
                    sender_domain = sender_email.split("@")[1]
                    for l in db.query(OutreachLog).all():
                        if l.email and "@" in l.email:
                            if l.email.split("@")[1] == sender_domain:
                                lead = l
                                break

                if not lead:
                    continue

                lead.replied = 1
                lead.status = "interested"
                if hasattr(lead, "reply_subject"):
                    lead.reply_subject = subject
                if hasattr(lead, "reply_body"):
                    lead.reply_body = body_clean[:5000]
                if hasattr(lead, "replied_at"):
                    lead.replied_at = datetime.utcnow()
                lead.lead_score = calculate_lead_score(lead)
                matched_replies += 1

                # AUTO-REPLY: Send prospect details if YES reply
                is_yes = (
                    body_lower.strip() in ["yes", "yes.", "yes!"] or
                    body_lower.startswith("yes") or
                    "interested" in body_lower or
                    "send details" in body_lower or
                    "send me" in body_lower or
                    "please send" in body_lower
                )
                if is_yes and not lead.auto_replied:
                    try:
                        # Find the match for this plumber
                        plumber = db.query(Plumber).filter(
                            Plumber.email == sender_email
                        ).first()
                        if plumber:
                            from models import Match, DemandProspect
                            match = (
                                db.query(Match, DemandProspect)
                                .join(DemandProspect, Match.demand_prospect_id == DemandProspect.id)
                                .filter(Match.plumber_id == plumber.id)
                                .filter(Match.outreach_sent == 1)
                                .order_by(Match.id.desc())
                                .first()
                            )
                            if match:
                                match_obj, prospect = match
                                prospect_details = f"""Hi,

Thanks for getting back to us!

Here are the details for the commercial lead we identified:

Business: {prospect.name}
Type: {prospect.category or 'Commercial premises'}
Address: {prospect.address or prospect.city}
City: {prospect.city}

We recommend reaching out directly and mentioning you were referred through MeritBold.

If this lead converts to a job, please let us know so we can keep sending you relevant opportunities in your area.

Best,

Zephyr William
Team LeadGen
Merit-Bold Lead Generation
128 City Road, London, United Kingdom, EC1V 2NX"""

                                from utils.email import send_email
                                send_email(
                                    to_email=sender_email,
                                    subject=f"Re: {subject}",
                                    body=f"<p>{prospect_details.replace(chr(10), '</p><p>')}</p>"
                                )
                                lead.auto_replied = 1
                                lead.status = "deal_sent"
                    except Exception as e:
                        pass

            except Exception:
                continue

        db.commit()

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