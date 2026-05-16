from sqlalchemy.orm import Session
from models import DemandProspect, Plumber, Match

def run_matching_engine(db: Session, limit_plumbers: int = 100):
    prospects = db.query(DemandProspect).filter(
        DemandProspect.is_high_priority == 1
    ).all()

    plumbers = db.query(Plumber).filter(
        Plumber.email.isnot(None)
    ).limit(limit_plumbers).all()

    prospect_count = len(prospects)
    plumber_count = len(plumbers)

    created = 0
    skipped_city = 0
    skipped_existing = 0
    skipped_score = 0

    for prospect in prospects:
        for plumber in plumbers:
            score = 0
            p_city = (prospect.city or "").strip().lower()
            b_city = (plumber.city or "").strip().lower()

            if p_city and b_city and p_city == b_city:
                score += 40
            elif p_city == "" or b_city == "":
                score += 20
            else:
                skipped_city += 1
                continue

            if plumber.is_commercial:
                score += 30
            if plumber.website:
                score += 10
            if plumber.phone:
                score += 10

            if score < 40:
                skipped_score += 1
                continue

            existing = db.query(Match).filter(
                Match.demand_prospect_id == prospect.id,
                Match.plumber_id == plumber.id
            ).first()
            if existing:
                skipped_existing += 1
                continue

            match = Match(
                demand_prospect_id=prospect.id,
                plumber_id=plumber.id,
                match_score=score,
                match_reason="auto_match"
            )
            db.add(match)
            created += 1

    db.commit()
    return {
        "created": created,
        "prospects_checked": prospect_count,
        "plumbers_checked": plumber_count,
        "skipped_city_mismatch": skipped_city,
        "skipped_already_exists": skipped_existing,
        "skipped_low_score": skipped_score,
    }