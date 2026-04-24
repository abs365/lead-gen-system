from sqlalchemy.orm import Session
from models import DemandProspect, Plumber, Match


def is_valid_plumber(plumber):
    if plumber.is_commercial != 1:
        return False

    if not plumber.email and not plumber.phone:
        return False

    if not plumber.website:
        return False

    return True


def calculate_match_score(prospect, plumber):
    score = 0
    reasons = []

    # Borough
    if prospect.borough and plumber.borough:
        if prospect.borough == plumber.borough:
            score += 40
            reasons.append("same_borough:+40")
        else:
            score += 10
            reasons.append("nearby:+10")

    # Demand strength
    if prospect.demand_score:
        val = int(prospect.demand_score * 0.7)
        score += val
        reasons.append(f"demand:{val}")

    # Category
    if prospect.category and "restaurant" in prospect.category.lower():
        score += 15
        reasons.append("restaurant:+15")

    # Contact quality
    if plumber.email:
        score += 10
        reasons.append("email:+10")

    if plumber.phone:
        score += 5
        reasons.append("phone:+5")

    # Commercial boost
    if plumber.is_commercial == 1:
        score += 20
        reasons.append("commercial:+20")

    # HARD CAP
    score = min(score, 100)

    return score, ", ".join(reasons)


def run_matching(db: Session):
    prospects = db.query(DemandProspect)\
        .order_by(DemandProspect.demand_score.desc())\
        .all()

    plumbers = db.query(Plumber).all()

    created = 0
    plumber_usage = {}

    for prospect in prospects:
        scored = []

        for plumber in plumbers:
            if not is_valid_plumber(plumber):
                continue

            score, reason = calculate_match_score(prospect, plumber)

            if score < 30:
                continue

            scored.append((plumber, score, reason))

        scored.sort(key=lambda x: x[1], reverse=True)

        for plumber, score, reason in scored:
            usage = plumber_usage.get(plumber.id, 0)

            if usage >= 5:
                continue

            existing = db.query(Match).filter(
                Match.demand_prospect_id == prospect.id,
                Match.plumber_id == plumber.id
            ).first()

            if existing:
                continue

            db.add(Match(
                demand_prospect_id=prospect.id,
                plumber_id=plumber.id,
                match_score=score,
                match_reason=reason
            ))

            plumber_usage[plumber.id] = usage + 1
            created += 1

            break  # one match per prospect

    db.commit()
    return created