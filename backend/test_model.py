import os

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise SystemExit("Missing GEMINI_API_KEY")

genai.configure(api_key=api_key)
print([m.name for m in genai.list_models()])
