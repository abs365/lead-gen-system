from sqlalchemy.orm import Session
from models import OutreachLog
from email.mime.text import MIMEText
import smtplib

from config import settings


def send_reply_followups(db: Session) -> dict:
    leads = db.query(OutreachLog).filter(
        OutreachLog.replied == 1
    ).all()

    sent = 0

    for lead in leads:
        if getattr(lead, "auto_replied", 0) == 1:
            continue

        try:
            msg = MIMEText("""
Hi,

Thanks for your reply.

We have a qualified job opportunity that matches your services.

Would you be available for a quick call to discuss details?

Best regards
""")

            msg["Subject"] = "Next step"
            msg["From"] = settings.active_smtp_user
            msg["To"] = lead.email

            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
            server.starttls()
            server.login(
                settings.active_smtp_user,
                settings.active_smtp_password
            )

            server.send_message(msg)
            server.quit()

            # UPDATE STATUS
            lead.status = "contacted"

            # FLAG SENT
            if hasattr(lead, "auto_replied"):
                lead.auto_replied = 1

            sent += 1

        except Exception as e:
            print("FOLLOW-UP ERROR:", e)

    db.commit()

    return {
        "success": True,
        "sent_followups": sent
    }