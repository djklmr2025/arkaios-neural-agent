import google.generativeai as genai
import os

genai.configure(api_key=os.environ.get("GEMINI_API_KEY", "AIzaSyBzTXJoGc8sNhsoP1K8Xy3VoAz6aAYhEAg"))

try:
    models = genai.list_models()
    for m in models:
        print(f"Model: {m.name}")
except Exception as e:
    print(f"Error: {e}")
