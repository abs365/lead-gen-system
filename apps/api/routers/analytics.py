from fastapi import APIRouter
from sqlalchemy.orm import Session
from database import SessionLocal
from models import OutreachLog

router = APIRouter(prefix="/analytics", tags=["analytics"])


def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()


@router.get("/outreach")
def get_outreach_analytics():
    db: Session = get_db()

    total_sent = db.query(OutreachLog).filter(OutreachLog.sent_at != None).count()
    opened = db.query(OutreachLog).filter(OutreachLog.opened == 1).count()
    clicked = db.query(OutreachLog).filter(OutreachLog.clicked == 1).count()

    open_rate = (opened / total_sent * 100) if total_sent > 0 else 0
    click_rate = (clicked / total_sent * 100) if total_sent > 0 else 0

    return {
        "total_sent": total_sent,
        "opened": opened,
        "clicked": clicked,
        "open_rate_percent": round(open_rate, 2),
        "click_rate_percent": round(click_rate, 2),
    }