from fastapi import APIRouter
from datetime import datetime
from sqlalchemy.orm import Session

from database import SessionLocal
from models import Outreach

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

    leads = db.query(Outreach).limit(5).all()

    sent_count = 0

    for lead in leads:
        try:
            # TEMP: simulate sending
            print(f"Sending email to {lead.email}")

            lead.sent_at = datetime.utcnow()
            sent_count += 1

        except Exception as e:
            print("Error:", e)

    db.commit()

    return {
        "status": "outreach sent",
        "sent": sent_count,
        "timestamp": datetime.utcnow().isoformat()
    }