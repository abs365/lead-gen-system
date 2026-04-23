"""
CSV export endpoints.

GET /export/plumbers  — download all plumbers as CSV
GET /export/demand    — download all demand prospects as CSV
GET /export/matches   — download all matches as CSV

SECURITY:
- CSV content is generated server-side; user cannot inject values.
- Filenames are hardcoded (no user input in Content-Disposition).
- All string fields are quoted by the csv module to prevent CSV injection.
  Leading =, +, -, @ characters in cell values are prefixed with a tab
  to neutralise formula injection in Excel/Google Sheets (OWASP CSV injection).
"""
from __future__ import annotations

import csv
import io
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models import DemandProspect, Match, Plumber

logger = logging.getLogger(__name__)
router = APIRouter()

# Characters that trigger formula execution in spreadsheet applications
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _sanitise_cell(value) -> str:
    """
    Convert a value to a safe CSV cell string.
    Neutralises CSV formula injection by prefixing dangerous characters
    with a tab character (industry-standard mitigation).
    """
    if value is None:
        return ""
    text = str(value).replace("\n", " ").replace("\r", " ")
    if text and text[0] in _FORMULA_PREFIXES:
        text = "\t" + text  # Defang formula prefix
    return text


def _stream_csv(headers: list, rows: list, filename: str) -> StreamingResponse:
    """Build a StreamingResponse that sends CSV data inline."""
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)
    writer.writerow(headers)
    for row in rows:
        writer.writerow([_sanitise_cell(v) for v in row])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            # Use attachment; filename to prompt download
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )


@router.get("/plumbers")
def export_plumbers(db: Session = Depends(get_db)):
    """Export all plumber records as a CSV file."""
    plumbers = db.query(Plumber).order_by(Plumber.id).all()

    headers = [
        "id", "name", "address", "postcode", "city", "borough",
        "website", "email", "phone", "lat", "lng",
        "source", "category", "is_commercial", "prospect_status", "created_at",
    ]
    rows = [
        [
            p.id, p.name, p.address, p.postcode, p.city, p.borough,
            p.website, p.email, p.phone, p.lat, p.lng,
            p.source, p.category, p.is_commercial, p.prospect_status,
            p.created_at.isoformat() if p.created_at else "",
        ]
        for p in plumbers
    ]
    logger.info("Exporting %d plumbers", len(rows))
    return _stream_csv(headers, rows, "plumbers.csv")


@router.get("/demand")
def export_demand(db: Session = Depends(get_db)):
    """Export all demand prospect records as a CSV file."""
    prospects = (
        db.query(DemandProspect)
        .order_by(DemandProspect.demand_score.desc())
        .all()
    )

    headers = [
        "id", "name", "category", "address", "postcode", "city", "borough",
        "website", "email", "phone", "source", "freshness_label",
        "demand_score", "fsa_rating", "created_at",
    ]
    rows = [
        [
            p.id, p.name, p.category, p.address, p.postcode, p.city, p.borough,
            p.website, p.email, p.phone, p.source, p.freshness_label,
            p.demand_score, p.fsa_rating,
            p.created_at.isoformat() if p.created_at else "",
        ]
        for p in prospects
    ]
    logger.info("Exporting %d demand prospects", len(rows))
    return _stream_csv(headers, rows, "demand_prospects.csv")


@router.get("/matches")
def export_matches(db: Session = Depends(get_db)):
    """Export all match records as a CSV file."""
    matches = (
        db.query(Match)
        .options(joinedload(Match.demand_prospect), joinedload(Match.plumber))
        .order_by(Match.match_score.desc())
        .all()
    )

    headers = [
        "match_id", "match_score", "match_reason",
        "prospect_name", "prospect_category", "prospect_borough", "prospect_postcode",
        "plumber_name", "plumber_borough", "plumber_postcode",
        "plumber_phone", "plumber_email", "plumber_website",
        "created_at",
    ]
    rows = [
        [
            m.id, m.match_score, m.match_reason,
            m.demand_prospect.name if m.demand_prospect else "",
            m.demand_prospect.category if m.demand_prospect else "",
            m.demand_prospect.borough if m.demand_prospect else "",
            m.demand_prospect.postcode if m.demand_prospect else "",
            m.plumber.name if m.plumber else "",
            m.plumber.borough if m.plumber else "",
            m.plumber.postcode if m.plumber else "",
            m.plumber.phone if m.plumber else "",
            m.plumber.email if m.plumber else "",
            m.plumber.website if m.plumber else "",
            m.created_at.isoformat() if m.created_at else "",
        ]
        for m in matches
    ]
    logger.info("Exporting %d matches", len(rows))
    return _stream_csv(headers, rows, "matches.csv")
