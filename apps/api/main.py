import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from apscheduler.schedulers.background import BackgroundScheduler

from database import Base, engine, SessionLocal
from models import OutreachLog

from routers import collect, data, automation, analytics, replies, opportunities
from routers.automation import run_outreach_job  # scheduler-safe function
from services.reply_detector import detect_gmail_replies
from services.reply_followup import send_reply_followups
from services.deal_detector import detect_and_close_deals


print("DB URL:", os.getenv("DATABASE_URL"))

app = FastAPI(title="Lead Generation System")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DATABASE
Base.metadata.create_all(bind=engine)

# ROUTERS
app.include_router(collect.router)
app.include_router(data.router)
app.include_router(automation.router)
app.include_router(analytics.router)
app.include_router(replies.router)
app.include_router(opportunities.router)

# ROOT
@app.get("/")
def root():
    return {"status": "root working"}

# HEALTH
@app.get("/health")
def health():
    return {"status": "ok"}

# TEST
@app.get("/test")
def test():
    return {"message": "API is alive"}

# TRACK OPEN
@app.get("/track/open/{lead_id}")
def track_open(lead_id: int):
    db = SessionLocal()
    try:
        db.query(OutreachLog).filter(OutreachLog.id == lead_id).update(
            {"opened": 1},
            synchronize_session=False
        )
        db.commit()
    finally:
        db.close()

    return Response(content=b"", media_type="image/png")

# SCHEDULER
scheduler = BackgroundScheduler()


@app.on_event("startup")
def start_scheduler():
    # Outreach runs once per day
    scheduler.add_job(run_outreach_job, "interval", hours=24)

    # Reply detection every 10 minutes
    scheduler.add_job(
        lambda: detect_gmail_replies(SessionLocal()),
        "interval",
        minutes=10
    )

    # Reply follow-ups every 15 minutes
    scheduler.add_job(
        lambda: send_reply_followups(SessionLocal()),
        "interval",
        minutes=15
    )

    # Deal detection every 20 minutes
    scheduler.add_job(
        lambda: detect_and_close_deals(SessionLocal()),
        "interval",
        minutes=20
    )

    scheduler.start()
    print("Scheduler started")