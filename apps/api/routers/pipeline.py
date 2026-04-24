from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from routers.collect import (
    collect_plumbers,
    collect_companies,
    collect_demand,
    run_matching_endpoint
)
from routers.data import send_outreach

router = APIRouter()


@router.post("/run-full-pipeline")
def run_full_pipeline(db: Session = Depends(get_db)):
    results = {}

    results["collect_plumbers"] = collect_plumbers(db)
    results["enrich"] = enrich_plumber_emails(db)
    results["demand"] = collect_demand(db)
    results["matching"] = run_matching_endpoint(db)
    results["outreach"] = send_outreach(db)

    return {
        "status": "completed",
        "results": results,
    }