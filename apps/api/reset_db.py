from database import SessionLocal, Base, engine
from models import OutreachLog

db = SessionLocal()

# DROP TABLE (CRITICAL)
OutreachLog.__table__.drop(bind=engine, checkfirst=True)

# CREATE TABLE AGAIN (NEW SCHEMA)
OutreachLog.__table__.create(bind=engine)

print("Table recreated with new schema")

# ADD TEST DATA
leads = [
    OutreachLog(email="contact@realplumbingcompany.co.uk", subject="Emergency plumbing support London"),
    OutreachLog(email="info@cityplumbers.co.uk", subject="Commercial plumbing jobs available"),
    OutreachLog(email="yourrealemail@gmail.com", subject="Test low quality"),
]

for lead in leads:
    db.add(lead)

db.commit()
db.close()

print("New data inserted")