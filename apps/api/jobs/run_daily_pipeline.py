import requests
from datetime import datetime

BASE_URL = "https://leadgen-api-khfd.onrender.com"
API_KEY = "12B295n305T286s113a151e24"
LOG_FILE = "pipeline.log"
TIMEOUT = 180

HEADERS = {"X-API-KEY": API_KEY}


def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def run_get(name, endpoint, params=None):
    log(f"RUNNING: {name}")
    try:
        response = requests.get(
            f"{BASE_URL}{endpoint}",
            headers=HEADERS,
            params=params,
            timeout=TIMEOUT,
        )
        data = response.json()
        log(f"SUCCESS: {name} -> {data}")
        return data
    except Exception as e:
        log(f"FAILED: {name} -> {str(e)}")
        return {}


def run_post(name, endpoint):
    log(f"RUNNING: {name}")
    try:
        response = requests.post(
            f"{BASE_URL}{endpoint}",
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        data = response.json()
        log(f"SUCCESS: {name} -> {data}")
        return data
    except Exception as e:
        log(f"FAILED: {name} -> {str(e)}")
        return {}


def run_pipeline():
    log("=== DAILY PIPELINE START ===")

    # 1. Collect fresh demand prospects
    run_get("Collect Demand FSA", "/collect/collect-demand-all-cities")
    run_get("Collect Companies House", "/collect/collect-companies-house")
    run_get("Collect Contracts Finder", "/collect/collect-contracts-finder", {"days_back": 2})

    # 2. Enrich with Snov.io (3 cycles x 25)
    log("--- Snov.io email enrichment ---")
    for i in range(3):
        result = run_get(f"Snov Enrichment (cycle {i+1})", "/collect/enrich-demand-snov", {"limit": 25})
        enriched = result.get("enriched", 0)
        log(f"Cycle {i+1}: enriched {enriched} emails")

    # 3. Score all demand prospects
    run_get("Score Demand", "/collect/score-demand")

    # 4. Run matching engine
    run_get("Run Matching", "/collect/run-matching-engine")

    # 5. Send outreach emails
    run_post("Send Outreach", "/automation/send-match-outreach")

    # 6. Detect replies
    run_post("Detect Replies", "/automation/detect-replies")

    # 7. Detect bounces and clean bad emails
    run_post("Detect Bounces", "/automation/detect-bounces")

    log("=== DAILY PIPELINE END ===")


if __name__ == "__main__":
    run_pipeline()