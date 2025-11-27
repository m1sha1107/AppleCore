# backend/gemini_client.py
import os
import re
from dotenv import load_dotenv
import google.genai as genai

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is not set in environment")

client = genai.Client(api_key=GEMINI_API_KEY)


def _extract_text(response) -> str:
    """
    Flatten a google.genai response into a plain text string.
    """
    parts = []
    for cand in response.candidates:
        for part in cand.content.parts:
            if hasattr(part, "text") and part.text:
                parts.append(part.text)
    return "\n".join(parts).strip()


def generate_text(prompt: str) -> str:
    """
    Simple text generation helper (for /gemini/test).
    """
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )
    return _extract_text(response)


def _extract_sql(raw: str) -> str:
    """
    Given raw model output, try to extract a clean SQL string:

    - If there's a ```sql``` or ```bigquery``` fenced block, take that.
    - Strip language prefixes like "sql\nSELECT" or "bigquery\nSELECT".
    - Trim everything before the first SELECT.
    - Remove trailing semicolon.
    """
    # 1) fenced code block
    m = re.search(
        r"```(?:sql|bigquery)?\s*(.*?)```",
        raw,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if m:
        raw = m.group(1).strip()

    # 2) find first SELECT
    idx = raw.upper().find("SELECT")
    if idx != -1:
        raw = raw[idx:]

    # 3) cleanup
    raw = raw.strip()
    if raw.endswith(";"):
        raw = raw[:-1].strip()

    return raw


def generate_sql(prompt: str) -> str:
    """
    Generate SQL from a prompt and normalize it so it starts with SELECT.
    """
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )
    text = _extract_text(response)
    sql = _extract_sql(text)
    return sql
