# backend/gemini_client.py
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# Prefer GEMINI_API_KEY but also allow GOOGLE_API_KEY
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError(
        "Missing GEMINI_API_KEY/GOOGLE_API_KEY. "
        "Set it in your .env from Google AI Studio."
    )

# Default model – you can override via .env
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Gemini API client (NOT Vertex, no project/location needed)
client = genai.Client(api_key=GEMINI_API_KEY)


def generate_text(prompt: str, temperature: float = 0.3) -> str:
    """
    Simple helper: free-form text response from Gemini.
    """
    resp = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=temperature,
        ),
    )
    # .text is already the concatenated text from all parts
    return resp.text or ""


def generate_sql(prompt: str, temperature: float = 0.0) -> str:
    """
    Ask Gemini to produce BigQuery SQL. We:
      - ask it to wrap the SQL in ```sql ... ```
      - parse that block out of the response.
    """
    resp = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=temperature,
        ),
    )
    text = resp.text or ""

    # Try to extract ```sql ... ``` block if present
    lower = text.lower()
    start = lower.find("```sql")
    if start != -1:
        start = text.find("\n", start)
        if start == -1:
            start = 0
        else:
            start += 1
        end = text.lower().find("```", start)
        if end != -1:
            sql = text[start:end].strip()
            return sql

    # Fallback: return the whole text (you can inspect it in logs)
    return text.strip()
