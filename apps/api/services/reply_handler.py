from utils.email_reader import read_replies
from database import SessionLocal
from models import Opportunity
from datetime import datetime


def process_replies():
    db = SessionLocal()

    replies = read_replies()

    for reply in replies:
        # Simple logic: match latest sent opportunity
        opp = db.query(Opportunity).filter(
            Opportunity.status == "sent"
        ).order_by(Opportunity.sent_at.desc()).first()

        if not opp:
            continue

        opp.status = "interested"
        opp.accepted_at = datetime.utcnow()

    db.commit()
    db.close()