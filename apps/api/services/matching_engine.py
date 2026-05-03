from sqlalchemy.orm import Session
from models import DemandProspect, Plumber, Match


def run_matching_engine(db: Session):
    prospects = db.query(DemandProspect).filter(
        DemandProspect.is_high_priority == 1
    ).all()

    plumbers = db.query(Plumber).filter(
        Plumber.email.isnot(None)
    ).all()

    created = 0

    for prospect in prospects:
        for plumber in plumbers:
            score = 0

            # LOCATION
            p_city = (prospect.city or "").strip().lower()
            b_city = (plumber.city or "").strip().lower()

            if p_city and b_city and p_city == b_city:
                score += 40
            elif p_city == "" or b_city == "":
                score += 20  # unknown city — partial credit
            else:
                continue  # different cities — hard skip

            # COMMERCIAL FIT
            if plumber.is_commercial:
                score += 30

            # HAS WEBSITE
            if plumber.website:
                score += 10

            # HAS PHONE
            if plumber.phone:
                score += 10

            # MINIMUM THRESHOLD — lowered to 40
            if score < 40:
                continue

            # SKIP IF ALREADY MATCHED
            existing = db.query(Match).filter(
                Match.demand_prospect_id == prospect.id,
                Match.plumber_id == plumber.id
            ).first()

            if existing:
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
    return created