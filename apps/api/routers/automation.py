from fastapi import APIRouter
from datetime import datetime

router = APIRouter(prefix="/automation", tags=["automation"])

# TEST ROUTE
@router.get("/test")
def test_automation():
    return {"status": "automation working"}

# SEND OUTREACH ROUTE
@router.get("/send-outreach")
def send_outreach():
    # TEMP TEST RESPONSE
    return {
        "status": "outreach triggered",
        "timestamp": datetime.utcnow().isoformat()
    }