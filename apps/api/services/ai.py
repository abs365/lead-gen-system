from dotenv import load_dotenv
import os
import json
import re
from openai import OpenAI

# Load env
load_dotenv(".env.local")

api_key = os.getenv("SgDeEXJxWtIN9dMr6wxTw4r0hRLeFpdwz2iAMbEUqJAwBU2vIv9fTIBVUbFnES_FIowO9CeQYuT3BlbkFJZM6dLS59zJoT592hsh8dFF2YzK_5hjltICPvX6UzfVJyx7NOJ83t_vPYk18LBIrVg2yUCIrdQA")

client = OpenAI(api_key=api_key) if api_key else None


def ask_ai(prompt: str) -> str:
    if not client:
        return "No API key"

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print("AI ERROR:", str(e))
        return "AI failed"


def score_prospect_with_ai(record):
    if not client:
        return {"score": 0, "reason": "No API key"}

    prompt = f"""
You are scoring a business for plumbing opportunity.

Business:
Name: {record.get("name")}
Category: {record.get("category")}
Address: {record.get("address")}

Return ONLY valid JSON:
{{"score": 75, "reason": "short explanation"}}
"""

    try:
        text = ask_ai(prompt)

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError("No JSON found")

        parsed = json.loads(match.group())

        return {
            "score": int(parsed.get("score", 0)),
            "reason": parsed.get("reason", ""),
        }

    except Exception as e:
        print("AI PARSE ERROR:", str(e))
        return {"score": 0, "reason": "AI failed"}