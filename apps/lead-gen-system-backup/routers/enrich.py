from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import DemandProspect, Plumber
from services.enrichment import enrich_records

router = APIRouter()


@router.post("/enrich/plumbers")
def enrich_plumbers(db: Session = Depends(get_db)):
    records = db.query(Plumber).all()
    return enrich_records(records, db)


@router.post("/enrich/demand")
def enrich_demand(db: Session = Depends(get_db)):
    records = db.query(DemandProspect).all()
    return enrich_records(records, db)