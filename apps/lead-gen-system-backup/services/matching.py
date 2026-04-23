from __future__ import annotations

import logging
from typing import List, Tuple

from sqlalchemy.orm import Session

from models import DemandProspect, Match, Plumber

logger = logging.getLogger(__name__)


def _score(prospect: DemandProspect, plumber: Plumber) -> Tuple[int, str]:
    score = 0
    reasons: List[str] = []

    if prospect.borough and plumber.borough and prospect.borough == plumber.borough:
        score += 50
        reasons.append("same borough")

    if plumber.email:
        score += 20
        reasons.append("has email")

    if plumber.phone:
        score += 10
        reasons.append("has phone")

    if plumber.website:
        score += 10
        reasons.append("has website")

    return score, " | ".join(reasons)


def run_matching(db: Session) -> int:
    prospects = db.query(DemandProspect).all()
    plumbers = db.query(Plumber).all()

    created = 0

    for prospect in prospects:
        for plumber in plumbers:
            score, reason = _score(prospect, plumber)

            if score == 0:
                continue

            exists = db.query(Match).filter(
                Match.demand_prospect_id == prospect.id,
                Match.plumber_id == plumber.id
            ).first()

            if exists:
                continue

            db.add(Match(
                demand_prospect_id=prospect.id,
                plumber_id=plumber.id,
                match_score=score,
                match_reason=reason
            ))

            created += 1

    db.commit()
    logger.info(f"Matches created: {created}")
    return created