import requests
from apscheduler.schedulers.background import BackgroundScheduler

# ✅ PRODUCTION BASE URL (RENDER)
BASE_URL = "https://leadgen-api-hkfd.onrender.com"


def run_pipeline():
    try:
        requests.post(f"{BASE_URL}/run-full-pipeline")
        print("Pipeline executed")
    except Exception as e:
        print("Pipeline error:", str(e))


def run_followups():
    try:
        requests.post(f"{BASE_URL}/follow-up")
        print("Follow-ups executed")
    except Exception as e:
        print("Follow-up error:", str(e))


def start_scheduler():
    scheduler = BackgroundScheduler()

    # Production schedule
    scheduler.add_job(run_pipeline, "cron", hour=6, minute=0)
    scheduler.add_job(run_followups, "cron", hour=9, minute=0)

    scheduler.start()