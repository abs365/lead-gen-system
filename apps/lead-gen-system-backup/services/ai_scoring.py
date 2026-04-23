from dotenv import load_dotenv
import os
import json
import re
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def score_prospect_with_ai(record):
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ No OpenAI API key")
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
        response = client.chat.completions.create(
            model="gpt-4o-mini",   # fast + cheap
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )

        text = response.choices[0].message.content.strip()
        print("AI RAW:", text)

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError("No JSON found")

        parsed = json.loads(match.group())

        return {
            "score": int(parsed.get("score", 0)),
            "reason": parsed.get("reason", ""),
        }

    except Exception as e:
        print("❌ AI ERROR:", str(e))
        return {"score": 0, "reason": "AI failed"}