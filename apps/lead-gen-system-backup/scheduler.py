from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from database import SessionLocal
from routers.collect import collect_plumbers, collect_demand
from services.matching import run_matching

scheduler = BackgroundScheduler(timezone="Europe/London")


from routers.data import send_outreach

def run_daily_pipeline():
    db = SessionLocal()
    try:
        print("RUNNING DAILY PIPELINE...")

        plumbers_result = collect_plumbers(db)
        print("Plumbers:", plumbers_result)

        demand_result = collect_demand(db)
        print("Demand:", demand_result)

        matches_created = run_matching(db)
        print("Matches:", matches_created)

        email_result = send_outreach(db)
        print("Emails:", email_result)

    except Exception as e:
        print("PIPELINE ERROR:", str(e))
        db.rollback()
    finally:
        db.close()

def start_scheduler():
    if scheduler.running:
        return

    scheduler.add_job(
        run_daily_pipeline,
        trigger="cron",
        hour=7,
        minute=0,
        id="daily_pipeline",
        replace_existing=True,
    )

    scheduler.start()


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()