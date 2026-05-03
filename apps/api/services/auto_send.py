from database import SessionLocal
from models import Opportunity, Plumber
from utils.email import send_email
from datetime import datetime


def run_auto_send():
    db = SessionLocal()

    try:
        # 1. Get unsent opportunities
        opportunities = db.query(Opportunity).filter(
            Opportunity.status == "new"
        ).all()

        for opp in opportunities:
            # 2. Select best plumber (valid email, London, prefer commercial)
            plumber = db.query(Plumber).filter(
                Plumber.email != None,
                Plumber.city == "London"
            ).order_by(
                Plumber.is_commercial.desc(),
                Plumber.id.asc()
            ).first()

            if not plumber:
                continue

            plumber_email = plumber.email

            if not plumber_email:
                continue

            subject = f"New plumbing job in your area (£{opp.estimated_value})"

            body = f"""
Hi,

We have a commercial job available in your area:

📍 {opp.business_name} ({opp.location})
🔧 Issue: {opp.issue_detected}
💰 Estimated value: £{opp.estimated_value}
⚠️ Urgency: {opp.urgency_score}/10

This is a live opportunity.

Reply YES to secure this job.

– MeritBold
"""

            # Send email
            send_email(plumber_email, subject, body)

            # Update DB
            opp.status = "sent"
            opp.plumber_id = plumber.id
            opp.sent_at = datetime.utcnow()

        db.commit()

    finally:
        db.close()