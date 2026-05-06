import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from apscheduler.schedulers.background import BackgroundScheduler

from database import Base, engine, SessionLocal
from models import OutreachLog

from routers import collect, data, automation, analytics, replies, opportunities, auth
from routers.automation import run_outreach_job  # scheduler-safe function
from services.reply_detector import detect_gmail_replies
from services.reply_followup import send_reply_followups
from services.deal_detector import detect_and_close_deals


print("DB URL:", os.getenv("DATABASE_URL"))

app = FastAPI(title="Lead Generation System")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://lead-gen-system-azure.vercel.app",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
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
app.include_router(auth.router)

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

    # --- FULL PIPELINE (daily at 6am) ---
    def run_full_pipeline():
        db = SessionLocal()
        try:
            print("[Pipeline] Starting full automated pipeline...")

            # Step 1 - Collect FSA demand
            from services.food_standards import fetch_all_cities
            from models import DemandProspect
            results = fetch_all_cities()
            added = 0
            for r in results:
                existing = db.query(DemandProspect).filter(
                    DemandProspect.fsa_establishment_id == str(r.get("fsa_id", ""))
                ).first()
                if not existing and r.get("name"):
                    prospect = DemandProspect(
                        name=r.get("name"),
                        category=r.get("category"),
                        address=r.get("address"),
                        city=r.get("city", "London"),
                        borough=r.get("borough"),
                        postcode=r.get("postcode"),
                        fsa_establishment_id=str(r.get("fsa_id", "")),
                        fsa_rating=r.get("rating"),
                        last_inspection_date=r.get("inspection_date"),
                        source="fsa",
                        status="new",
                    )
                    db.add(prospect)
                    added += 1
            db.commit()
            print(f"[Pipeline] FSA collected: {added} new prospects")

            # Step 2 - Collect Companies House
            from services.companies_house import collect_companies_house
            ch_result = collect_companies_house(db)
            print(f"[Pipeline] Companies House: {ch_result}")

            # Step 3 - Score demand
            from services.scoring import calculate_demand_score, assign_high_priority_flags
            prospects = db.query(DemandProspect).all()
            for p in prospects:
                raw = p.score_breakdown or ""
                signals = [s.strip() for s in raw.split(",") if s.strip()]
                score, breakdown = calculate_demand_score(
                    signals=signals,
                    source=p.source or "fsa",
                    inspection_date=p.last_inspection_date
                )
                p.demand_score = score
                p.score_breakdown = breakdown
                p.is_high_priority = 1 if score >= 70 else 0
            assign_high_priority_flags(db)
            db.commit()
            print(f"[Pipeline] Scoring complete")

            # Step 4 - Run matching engine
            from services.matching_engine import run_matching_engine
            matches_created = run_matching_engine(db)
            print(f"[Pipeline] Matches created: {matches_created}")

            # Step 5 - Enrich plumber emails
            from services.plumber_enrichment import enrich_plumbers
            enrich_result = enrich_plumbers(db, limit=100)
            print(f"[Pipeline] Plumber enrichment: {enrich_result}")

            # Step 6 - Clean bounced emails
            from services.bounce_handler import clean_bounced_emails
            bounce_result = clean_bounced_emails(db)
            print(f"[Pipeline] Bounces cleaned: {bounce_result}")
            run_outreach_job()
            print(f"[Pipeline] Outreach complete")

        except Exception as e:
            print(f"[Pipeline] ERROR: {e}")
        finally:
            db.close()

    # --- PLANNING DATA COLLECTION (daily at 7am) ---
    def run_planning_collection():
        from services.planning_data import collect_planning_applications
        db2 = SessionLocal()
        try:
            collect_planning_applications(db2, days_back=2, limit=100)
        finally:
            db2.close()

    # Full pipeline runs daily at 6am
    scheduler.add_job(run_full_pipeline, "cron", hour=6, minute=0)

    # Planning data runs daily at 7am
    scheduler.add_job(run_planning_collection, "cron", hour=7, minute=0)

    # Outreach runs every 24 hours
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