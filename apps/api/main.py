from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from database import Base, engine, SessionLocal
from models import OutreachLog
from routers import collect, data, automation, analytics

app = FastAPI(title="Lead Generation System")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DATABASE
Base.metadata.create_all(bind=engine)

# ROUTERS
app.include_router(collect.router)
app.include_router(data.router)
app.include_router(automation.router)
app.include_router(analytics.router)

# ROOT
@app.get("/")
def root():
    return {"status": "root working"}

# HEALTH
@app.get("/health")
def health():
    return {"status": "ok"}

# TEST
@app.get("/test")
def test():
    return {"message": "API is alive"}

# TRACK OPEN
@app.get("/track/open/{lead_id}")
def track_open(lead_id: int):
    db = SessionLocal()
    try:
        lead = db.query(OutreachLog).filter(OutreachLog.id == lead_id).first()
        if lead:
            lead.opened = 1
            db.commit()
    finally:
        db.close()

    return Response(
        content=b"",
        media_type="image/png"
    )