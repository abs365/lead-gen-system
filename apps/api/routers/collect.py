import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from database import get_db
from models import DemandProspect, JobLog, Plumber, ProspectSignal
from services.adapters.google_places import search_plumbers
from services.adapters.companies_house import search_companies
from services.adapters.fsa import search_demand
from services.enrichment import extract_contact_details, detect_commercial_plumber
from services.matching import run_matching
from services.scoring import calculate_demand_score
from services.scoring import assign_high_priority_flags

logger = logging.getLogger(__name__)
router = APIRouter()


# --------------------------------------------------------------------------- #
# COLLECT PLUMBERS
# --------------------------------------------------------------------------- #

@router.post("/collect/plumbers")
def collect_plumbers(db: Session = Depends(get_db)):
    db.add(JobLog(job_type="collect_plumbers", status="started"))
    db.commit()

    records = search_plumbers("plumber", "London, UK")

    inserted = 0
    skipped = 0

    for record in records:
        if "google_place_id" in record:
            record["place_id"] = record.pop("google_place_id")

        existing = db.query(Plumber).filter(
            Plumber.place_id == record.get("place_id")
        ).first()

        if existing:
            skipped += 1
            continue

        db.add(Plumber(**record))
        inserted += 1

    db.commit()

    db.add(JobLog(
        job_type="collect_plumbers",
        status="completed",
        message=f"inserted={inserted} skipped={skipped}"
    ))
    db.commit()

    return {"inserted": inserted, "skipped": skipped}


# --------------------------------------------------------------------------- #
# ENRICH PLUMBERS
# --------------------------------------------------------------------------- #

@router.post("/enrich/prospects")
def enrich_prospects(db: Session = Depends(get_db)):
    plumbers = db.query(Plumber).all()

    updated = 0
    skipped = 0

    for plumber in plumbers:
        changed = False

        if plumber.website:
            email, phone = extract_contact_details(plumber.website)

            if plumber.email is None and email:
                plumber.email = email
                changed = True

            if plumber.phone is None and phone:
                plumber.phone = phone
                changed = True

            plumber.is_commercial = detect_commercial_plumber(plumber.website)
            changed = True

        if changed:
            plumber.updated_at = func.now()
            updated += 1
        else:
            skipped += 1

    db.commit()

    db.add(JobLog(
        job_type="enrich_plumber_emails",
        status="completed",
        message=f"updated={updated} skipped={skipped}"
    ))
    db.commit()

    return {"updated": updated, "skipped": skipped}


# --------------------------------------------------------------------------- #
# COLLECT COMPANIES
# --------------------------------------------------------------------------- #

@router.post("/collect/companies")
def collect_companies(db: Session = Depends(get_db)):
    db.add(JobLog(job_type="collect_companies", status="started"))
    db.commit()

    inserted = 0
    skipped = 0

    page = 1
    max_pages = 3

    while page <= max_pages:
        records = search_companies("restaurant", "London", page, 20)

        if not records:
            break

        for record in records:
            company_number = record.get("company_number")

            existing = db.query(DemandProspect).filter(
                DemandProspect.source == "companies_house",
                DemandProspect.source_record_id == company_number
            ).first()

            if existing:
                skipped += 1
                continue

            prospect = DemandProspect(
                name=record.get("name"),
                category="company",
                address=record.get("address"),
                source="companies_house",
                source_record_id=company_number,
                status="new",
            )

            db.add(prospect)
            db.flush()

            db.add(ProspectSignal(
                prospect_id=prospect.id,
                signal_type="new_company",
                signal_source="companies_house",
                signal_strength="medium",
                freshness_score=1.0
            ))

            score, breakdown = calculate_demand_score(
                signals=["new_company"],
                source="companies_house",
                inspection_date=None
            )

            prospect.demand_score = score
            prospect.score_breakdown = breakdown

            inserted += 1

        page += 1

    db.commit()

    db.add(JobLog(
        job_type="collect_companies",
        status="completed",
        message=f"pages={page-1} inserted={inserted} skipped={skipped}"
    ))
    db.commit()

    return {"pages_processed": page - 1, "inserted": inserted, "skipped": skipped}


# --------------------------------------------------------------------------- #
# COLLECT DEMAND (FSA)
# --------------------------------------------------------------------------- #

@router.post("/collect/demand")
def collect_demand(db: Session = Depends(get_db)):
    db.add(JobLog(job_type="collect_demand", status="started"))
    db.commit()

    inserted = 0
    skipped = 0

    page = 1
    max_pages = 5

    while page <= max_pages:
        records = search_demand("London", "Restaurant/Cafe/Canteen", page, 50)

        if not records:
            break

        for record in records:
            fsa_id = record.get("fsa_establishment_id")

            existing = db.query(DemandProspect).filter(
                DemandProspect.source == "fsa",
                DemandProspect.fsa_establishment_id == fsa_id
            ).first()

            if existing:
                skipped += 1
                continue

            prospect = DemandProspect(
                name=record.get("name"),
                category=record.get("category"),
                address=record.get("address"),
                postcode=record.get("postcode"),
                borough=record.get("borough"),
                source="fsa",
                source_record_id=fsa_id,
                fsa_establishment_id=fsa_id,
                fsa_rating=record.get("fsa_rating"),
                last_inspection_date=record.get("last_inspection_date"),
                status="new",
            )

            db.add(prospect)
            db.flush()

            signals = ["new_food_business", "high_water_usage"]

            if not record.get("website"):
                signals.append("no_website")

            for signal in signals:
                db.add(ProspectSignal(
                    prospect_id=prospect.id,
                    signal_type=signal,
                    signal_source="fsa",
                    signal_strength="high",
                    freshness_score=1.0
                ))

            score, breakdown = calculate_demand_score(
                signals=signals,
                source="fsa",
                inspection_date=record.get("last_inspection_date")
            )

            prospect.demand_score = score
            prospect.score_breakdown = breakdown

            inserted += 1

        page += 1

    db.commit()

    db.add(JobLog(
        job_type="collect_demand",
        status="completed",
        message=f"pages={page-1} inserted={inserted} skipped={skipped}"
    ))
    db.commit()

    return {"pages_processed": page - 1, "inserted": inserted, "skipped": skipped}


# --------------------------------------------------------------------------- #
# MATCHING
# --------------------------------------------------------------------------- #

from services.scoring import assign_high_priority_flags

@router.post("/run-matching")
def run_matching_endpoint(db: Session = Depends(get_db)):
    created = run_matching(db)

    # IMPORTANT: assign priority AFTER matching
    assign_high_priority_flags(db)

    return {"matches_created": created}
    created = run_matching(db)
    return {"matches_created": created}

    updated = 0
    skipped = 0

    for p in prospects:
        changed = False

        # find website
        if not p.website:
            website = find_business_website(p.name)
            if website:
                p.website = website
                changed = True

        # extract contact
        if p.website:
            email, phone = extract_contact_details(p.website)

            if not p.email and email:
                p.email = email
                changed = True

            if not p.phone and phone:
                p.phone = phone
                changed = True

        if changed:
            p.updated_at = func.now()
            updated += 1
        else:
            skipped += 1

    db.commit()

    return {
        "updated": updated,
        "skipped": skipped
    }