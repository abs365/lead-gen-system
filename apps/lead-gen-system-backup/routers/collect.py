import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from database import get_db
from models import DemandProspect, JobLog, Plumber
from services.adapters.google_places import search_plumbers
from services.adapters.fsa import search_demand
from services.ai_scoring import score_prospect_with_ai
from services.enrichment import extract_contact_details, extract_email_from_website
from services.matching import run_matching

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/collect/plumbers")
def collect_plumbers(db: Session = Depends(get_db)):
    db.add(JobLog(job_type="collect_plumbers", status="started"))
    db.commit()

    try:
        records = search_plumbers("plumber", "London, UK")
    except Exception as e:
        logger.exception("Plumber collection failed")
        db.add(JobLog(job_type="collect_plumbers", status="failed", message=str(e)))
        db.commit()
        return {"error": str(e)}

    inserted = 0
    updated = 0
    skipped = 0

    for record in records:
        if "google_place_id" in record:
            record["place_id"] = record.pop("google_place_id")

        existing = db.query(Plumber).filter(
            Plumber.place_id == record.get("place_id")
        ).first()

        if not existing:
            website = record.get("website")
            email = None
            scraped_phone = None

            if website:
                email, scraped_phone = extract_contact_details(website)

            if not record.get("email") and website:
                record["email"] = extract_email_from_website(website)

            if not record.get("email") and email:
                record["email"] = email

            if not record.get("phone") and scraped_phone:
                record["phone"] = scraped_phone

            db.add(Plumber(**record))
            inserted += 1

        else:
            changed = False

            for field in ["phone", "website", "borough", "postcode", "address", "email"]:
                if getattr(existing, field) is None and record.get(field):
                    setattr(existing, field, record[field])
                    changed = True

            if existing.website and (existing.email is None or existing.phone is None):
                email, scraped_phone = extract_contact_details(existing.website)

                if existing.email is None and email:
                    existing.email = email
                    changed = True

                if existing.phone is None and scraped_phone:
                    existing.phone = scraped_phone
                    changed = True

            if changed:
                existing.updated_at = func.now()
                updated += 1
            else:
                skipped += 1

    db.commit()

    db.add(
        JobLog(
            job_type="collect_plumbers",
            status="completed",
            message=f"inserted={inserted} updated={updated} skipped={skipped}",
        )
    )
    db.commit()

    return {
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
    }


@router.post("/enrich/plumber-emails")
def enrich_plumber_emails(db: Session = Depends(get_db)):
    plumbers = (
        db.query(Plumber)
        .filter(Plumber.website.isnot(None))
        .all()
    )

    updated = 0
    skipped = 0

    for plumber in plumbers:
        changed = False

        if plumber.email is None and plumber.website:
            email = extract_email_from_website(plumber.website)
            if email:
                plumber.email = email
                changed = True

        if plumber.phone is None and plumber.website:
            _, phone = extract_contact_details(plumber.website)
            if phone:
                plumber.phone = phone
                changed = True

        if changed:
            plumber.updated_at = func.now()
            updated += 1
        else:
            skipped += 1

    db.commit()

    db.add(
        JobLog(
            job_type="enrich_plumber_emails",
            status="completed",
            message=f"updated={updated} skipped={skipped}",
        )
    )
    db.commit()

    return {
        "updated": updated,
        "skipped": skipped,
    }


@router.post("/collect/demand")
def collect_demand(db: Session = Depends(get_db)):
    db.add(JobLog(job_type="collect_demand", status="started"))
    db.commit()

    try:
        records = search_demand("London", "Restaurant/Cafe/Canteen", 1, 50)
    except Exception as e:
        logger.exception("Demand collection failed")
        db.add(JobLog(job_type="collect_demand", status="failed", message=str(e)))
        db.commit()
        return {"error": str(e)}

    inserted = 0
    skipped = 0

    for record in records:
        existing = db.query(DemandProspect).filter(
            DemandProspect.fsa_establishment_id == record.get("fsa_establishment_id")
        ).first()

        if not existing:
            ai = score_prospect_with_ai(record)
            record["demand_score"] = ai.get("score", 0)

            db.add(DemandProspect(**record))
            inserted += 1
        else:
            skipped += 1

    db.commit()

    db.add(
        JobLog(
            job_type="collect_demand",
            status="completed",
            message=f"inserted={inserted} skipped={skipped}",
        )
    )
    db.commit()

    return {
        "inserted": inserted,
        "skipped": skipped,
    }


@router.post("/run-matching")
def run_matching_endpoint(db: Session = Depends(get_db)):
    created = run_matching(db)
    return {"matches_created": created}