import os
import logging
from fastapi import APIRouter, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import anthropic

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chatbot", tags=["chatbot"])

SYSTEM = """You are the MeritBold AI assistant on www.meritbold.com. MeritBold is a UK commercial plumbing lead generation service.
Key facts:
- Plans: Basic £49/month (5 leads), Pro £99/month (20 leads), Pro Max £199/month (50 leads), Enterprise £349/month (100 leads). Leads from just £3.49 each — industry average is £25.
- Leads delivered instantly by email after signup, matched by location, never shared between plumbers
- Subscribe at: https://lead-gen-system-azure.vercel.app/subscribe
- Contact: outreach@meritbold.com, +44 1322 952157
- Address: 128 City Road, London, EC1V 2NX
- UK-wide coverage: London, Manchester, Birmingham, Leeds, Sheffield, Bristol and 50+ cities
Be friendly, concise, under 80 words per reply. Always encourage plumbers to subscribe."""

class ChatRequest(BaseModel):
    messages: list[dict]

@router.post("/chat")
async def chat(data: ChatRequest):
    try:
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=300,
            system=SYSTEM,
            messages=data.messages
        )
        return {"reply": response.content[0].text}
    except Exception as e:
        logger.error(f"Chatbot error: {e}")
        return {"reply": "Sorry, I'm having trouble right now. Please email outreach@meritbold.com or call +44 1322 952157."}