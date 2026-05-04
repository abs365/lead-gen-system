import requests
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models import DemandProspect

PLUMBING_KEYWORDS = [
    "drainage", "kitchen", "toilet", "washroom", "bathroom",
    "plumbing", "water supply", "waste water", "sewage",
    "refurbishment", "restaurant", "cafe", "hotel", "takeaway",
    "food preparation", "commercial kitchen", "wet room",
    "change of use", "food", "catering", "extraction",
    "grease trap", "sink", "hot water", "boiler"
]

BOROUGH_APIS = [
    {
        "name": "Camden",
        "url": "https://opendata.camden.gov.uk/resource/2eiu-s2cw.json",
        "date_field": "registered_date",
        "address_field": "development_address",
        "desc_field": "development_description",
        "ref_field": "application_number",
    },
]

def _is_plumbing_relevant(description: str) -> tuple:
    if not description:
        return False, 0, []
    desc_lower = description.lower()
    matched = [kw for kw in PLUMBING_KEYWORDS if kw in desc_lower]
    score = min(len(matched) * 20, 100)
    return len(matched) > 0, score, matched

def collect_planning_applications(db: Session, days_back: int = 90, limit: int = 200) -> dict:
    since_date = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%dT00:00:00.000")
    total_collected = 0
    total_added = 0
    total_skipped = 0
    errors = []

    for borough in BOROUGH_APIS:
        try:
            offset = 0
            page_size = 100
            records = []

            while True:
                params = {
                    "$limit": page_size,
                    "$offset": offset,
                    "$where": f"{borough['date_field']} >= '{since_date}'",
                    "$order": f"{borough['date_field']} DESC",
                }

                response = requests.get(
                    borough["url"],
                    params=params,
                    timeout=20,
                    headers={"User-Agent": "LeadGenSystem/1.0"}
                )

                if response.status_code != 200:
                    errors.append(f"{borough['name']}: HTTP {response.status_code}")
                    break

                page = response.json()
                if not page:
                    break

                records.extend(page)
                offset += page_size

                if len(page) < page_size or len(records) >= limit:
                    break

            total_collected += len(records)

            for record in records:
                description = record.get(borough["desc_field"], "") or ""
                address = record.get(borough["address_field"], "") or ""
                reference = record.get(borough["ref_field"], "") or ""
                date_val = record.get(borough["date_field"], "") or ""

                is_relevant, score, keywords = _is_plumbing_relevant(description)
                if not is_relevant:
                    total_skipped += 1
                    continue

                source_id = f"{borough['name']}_{reference}"
                existing = db.query(DemandProspect).filter(
                    DemandProspect.source_record_id == source_id
                ).first()

                if existing:
                    total_skipped += 1
                    continue

                prospect = DemandProspect(
                    name=(description[:255] if description else "Planning Application"),
                    category="planning_application",
                    address=(f"{address}, {borough['name']}, London" if address else None),
                    city="London",
                    borough=borough["name"],
                    source="planning_data",
                    source_record_id=source_id,
                    score_breakdown=",".join(keywords),
                    demand_score=score,
                    status="new",
                    is_high_priority=1 if score >= 60 else 0,
                    last_inspection_date=date_val[:10] if date_val else None,
                )

                db.add(prospect)
                total_added += 1

        except Exception as e:
            errors.append(f"{borough['name']}: {str(e)[:100]}")

    db.commit()

    return {
        "success": True,
        "collected": total_collected,
        "added": total_added,
        "skipped": total_skipped,
        "errors": errors,
    }