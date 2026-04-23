"""
Matching endpoint: link demand prospects to nearby plumbers.

POST /match  — run the full matching algorithm
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import JobLog
from schemas import JobResult, RunMatchRequest
from services.matching import run_matching

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/match", response_model=JobResult)
def create_matches(
    req: RunMatchRequest,
    db: Session = Depends(get_db),
):
    """
    Run matching between all demand prospects and plumbers.
    Existing matches are cleared and rebuilt from scratch.
    max_matches_per_prospect is capped at 10 by the schema.
    """
    log = JobLog(
        job_type="match",
        status="running",
        message=f"max_per_prospect={req.max_matches_per_prospect}",
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    try:
        total = run_matching(db, max_per_prospect=req.max_matches_per_prospect)

        log.status = "success"
        log.message = f"Created {total} match records"
        log.records_processed = total
        db.commit()

        return JobResult(
            status="success",
            message=log.message,
            added=total,
        )

    except Exception as exc:
        logger.error("match run failed: %s", exc, exc_info=True)
        log.status = "error"
        log.message = f"Matching failed: {type(exc).__name__}"
        db.commit()
        raise HTTPException(status_code=500, detail="Matching failed.")
