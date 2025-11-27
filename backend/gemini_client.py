# backend/gemini_client.py
import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
MODEL_ID = os.getenv("GEMINI_MODEL", "google/gemini-2.0-flash-001")

# Client will read:
# - GOOGLE_GENAI_USE_VERTEXAI=true
# - GOOGLE_CLOUD_PROJECT
# - GOOGLE_CLOUD_LOCATION
# - GOOGLE_APPLICATION_CREDENTIALS
client = genai.Client()


def generate_text(prompt: str) -> str:
    """
    Simple helper: send a text prompt to Gemini and return the text output.
    Use this first just to verify integration works.
    """
    response = client.models.generate_content(
        model=MODEL_ID,
        contents=prompt,
    )
    # For plain text responses, .text is convenient
    return response.text
