import os
from fastapi import Header, HTTPException
from dotenv import load_dotenv

load_dotenv()

API_SECRET_KEY = os.getenv("API_SECRET_KEY")


def require_api_key(x_api_key: str = Header(None, alias="X-API-KEY")):
    print("EXPECTED:", API_SECRET_KEY)
    print("RECEIVED:", x_api_key)

    if not API_SECRET_KEY:
        raise HTTPException(
            status_code=500,
            detail="API_SECRET_KEY not set"
        )

    if x_api_key != API_SECRET_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key"
        )

    return True