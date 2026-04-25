from database import SessionLocal
from models import OutreachLog

db = SessionLocal()

rows = db.query(OutreachLog).all()

for r in rows:
    r.sent_at = None

db.commit()
db.close()

print("Reset complete: all sent_at cleared")