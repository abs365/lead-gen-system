import requests
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"
LOG_FILE = "pipeline.log"
TIMEOUT = 120  # increase timeout


def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def run_step(name, endpoint):
    log(f"RUNNING: {name}")
    try:
        response = requests.post(
            f"{BASE_URL}{endpoint}",
            timeout=TIMEOUT
        )
        log(f"SUCCESS: {name} {response.status_code}")
    except Exception as e:
        log(f"FAILED: {name} {str(e)}")


def run_pipeline():
    log("=== DAILY PIPELINE START ===")

    run_step("Collect Plumbers", "/collect/plumbers")
    run_step("Enrich Emails", "/enrich/plumber-emails")
    run_step("Collect Demand", "/collect/demand")
    run_step("Run Matching", "/run-matching")
    run_step("Send Outreach", "/send-outreach")

    log("=== DAILY PIPELINE END ===")


if __name__ == "__main__":
    run_pipeline()