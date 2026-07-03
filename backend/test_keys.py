import os
import requests
from dotenv import load_dotenv

load_dotenv()

keys = [key for key in [
    os.getenv("GEMINI_API_KEY"),
    os.getenv("GEMINI_API_KEY_2"),
    os.getenv("GEMINI_API_KEY_3"),
] if key]

if not keys:
    raise SystemExit("No Gemini keys found in environment")

for key in keys:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
    resp = requests.post(url, json={
        "contents": [{"parts": [{"text": "Hello"}]}]
    }, timeout=10)
    print(f"Key {key[:15]}...: Status {resp.status_code}")
    if resp.status_code != 200:
        print("Error:", resp.text[:200])
