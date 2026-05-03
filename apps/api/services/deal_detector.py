from sqlalchemy.orm import Session
from models import OutreachLog


KEYWORDS = [
    "yes",
    "interested",
    "call",
    "quote",
    "price",
    "how much",
    "let's do it",
    "sounds good"
]


def detect_and_close_deals(db: Session) -> dict:
    leads = db.query(OutreachLog).filter(
        OutreachLog.replied == 1,
        OutreachLog.status == "contacted"
    ).all()

    closed = 0

    for lead in leads:
        if lead.status == "closed":
            continue

        text = ""
        if hasattr(lead, "reply_body") and lead.reply_body:
            text = lead.reply_body.lower()

        if any(keyword in text for keyword in KEYWORDS):
            lead.status = "closed"
            lead.deal_value = lead.estimated_value or 200
            closed += 1

    db.commit()

    return {
        "success": True,
        "closed_deals": closed
    }