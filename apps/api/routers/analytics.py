@router.get("/recent-activity")
def get_recent_activity():
    db = SessionLocal()

    try:
        rows = (
            db.query(OutreachLog)
            .filter(OutreachLog.sent_at != None)
            .order_by(OutreachLog.sent_at.desc())
            .limit(10)
            .all()
        )

        return [
            {
                "email": r.email,
                "subject": r.subject,
                "opened": r.opened,
                "clicked": r.clicked,
                "sent_at": r.sent_at,
            }
            for r in rows
        ]
    finally:
        db.close()