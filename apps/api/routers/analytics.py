from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import OutreachLog

router = APIRouter()


# ------------------------------------------------------------------
# OUTREACH METRICS
# ------------------------------------------------------------------

@router.get("/analytics/outreach")
def outreach_analytics(db: Session = Depends(get_db)):
    total = db.query(func.count(OutreachLog.id)).scalar()
    opened = db.query(func.count(OutreachLog.id)).filter(OutreachLog.opened == 1).scalar()
    clicked = db.query(func.count(OutreachLog.id)).filter(OutreachLog.clicked == 1).scalar()

    open_rate = round((opened / total) * 100, 2) if total else 0
    click_rate = round((clicked / total) * 100, 2) if total else 0

    return {
        "total_sent": total,
        "opened": opened,
        "clicked": clicked,
        "open_rate_percent": open_rate,
        "click_rate_percent": click_rate
    }


# ------------------------------------------------------------------
# RECENT ACTIVITY
# ------------------------------------------------------------------

@router.get("/analytics/recent-activity")
def recent_activity(db: Session = Depends(get_db)):
    logs = (
        db.query(OutreachLog)
        .order_by(OutreachLog.sent_at.desc())
        .limit(20)
        .all()
    )

    return [
        {
            "email": log.email,
            "subject": log.subject,
            "opened": log.opened,
            "clicked": log.clicked,
            "sent_at": log.sent_at
        }
        for log in logs
    ]