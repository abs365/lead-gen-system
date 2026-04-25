from fastapi import APIRouter
from datetime import datetime
from sqlalchemy.orm import Session

from database import SessionLocal
from models import OutreachLog
from services.email import send_email

router = APIRouter(prefix="/automation", tags=["automation"])


def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()


@router.get("/send-outreach")
def send_outreach():
    db: Session = get_db()

    leads = db.query(OutreachLog).filter(OutreachLog.sent_at == None).limit(5).all()

    sent_count = 0

    for lead in leads:
        try:
            body = f"""
Hello,

We noticed your business and wanted to offer fast, reliable plumbing support in your area.

Let us know if you need help.

Best regards,
LeadGen Team

<img src="https://leadgen-api-khfd.onrender.com/track/open/{lead.id}" width="1" height="1" />
"""

            send_email(
                to_email=lead.email,
                subject=lead.subject,
                body=body
            )

            lead.sent_at = datetime.utcnow()
            sent_count += 1

        except Exception as e:
            print("Email error:", e)

    db.commit()

    return {
        "status": "outreach sent",
        "sent": sent_count,
        "timestamp": datetime.utcnow().isoformat()
    }