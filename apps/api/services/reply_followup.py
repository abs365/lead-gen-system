from database import SessionLocal
from models import OutreachLog
from utils.email import send_email
import logging

logger = logging.getLogger(__name__)


def send_reply_followups() -> dict:
    """Scheduled job — creates its own db session."""
    db = SessionLocal()
    try:
        leads = db.query(OutreachLog).filter(
            OutreachLog.replied == 1,
            OutreachLog.status == "interested",
        ).all()

        sent = 0
        for lead in leads:
            if getattr(lead, "auto_replied", 0) == 1:
                continue
            try:
                send_email(
                    to_email=lead.email,
                    subject=f"Re: {lead.subject}",
                    body="<p>Just following up — happy to send more leads your way. Reply YES any time to claim a new one.</p>",
                )
                lead.auto_replied = 1
                sent += 1
            except Exception as e:
                logger.error(f"Follow-up error for {lead.email}: {e}")

        db.commit()
        return {"success": True, "sent_followups": sent}
    except Exception as e:
        logger.error(f"send_reply_followups error: {e}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()