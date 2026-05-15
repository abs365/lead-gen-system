from database import SessionLocal
from models import OutreachLog
import logging

logger = logging.getLogger(__name__)

KEYWORDS = [
    "yes", "interested", "call", "quote",
    "price", "how much", "let's do it", "sounds good"
]


def detect_and_close_deals() -> dict:
    """Scheduled job — creates its own db session."""
    db = SessionLocal()
    try:
        leads = db.query(OutreachLog).filter(
            OutreachLog.replied == 1,
            OutreachLog.status == "interested",
        ).all()

        closed = 0
        for lead in leads:
            if lead.status == "closed":
                continue
            text = ""
            if hasattr(lead, "reply_body") and lead.reply_body:
                text = lead.reply_body.lower()
            if any(kw in text for kw in KEYWORDS):
                lead.status = "closed"
                lead.deal_value = lead.estimated_value or 200
                closed += 1

        db.commit()
        return {"success": True, "closed_deals": closed}
    except Exception as e:
        logger.error(f"detect_and_close_deals error: {e}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()