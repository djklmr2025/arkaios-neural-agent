import multiprocessing
import uvicorn
import os
import secrets
from dotenv import load_dotenv

# Initialize env file in AppData
app_data_dir = os.path.join(os.path.expanduser("~"), "AppData", "Local", "NeuralAgent")
os.makedirs(app_data_dir, exist_ok=True)
env_path = os.path.join(app_data_dir, "API_KEYS.env")

if not os.path.exists(env_path):
    with open(env_path, "w") as f:
        f.write("""# Pega aqui tu llave de Gemini y reinicia la aplicacion
GEMINI_API_KEY=
JWT_SECRET=Arkaios_Super_Secret_Key_777!
JWT_ISS=NeuralAgent_Local
DEFAULT_AGENT_MODEL_TYPE=google
DEFAULT_AGENT_MODEL_ID=gemini-2.5-flash
PUTER_AUTH_TOKEN=
PUTER_OPENAI_BASE_URL=https://api.puter.com/puterai/openai/v1/
PUTER_TIMEOUT=30
PUTER_MAX_RETRIES=2
CLASSIFIER_AGENT_MODEL_TYPE=google
CLASSIFIER_AGENT_MODEL_ID=gemini-2.5-flash
TITLE_AGENT_MODEL_TYPE=google
TITLE_AGENT_MODEL_ID=gemini-2.5-flash
SUGGESTOR_AGENT_MODEL_TYPE=google
SUGGESTOR_AGENT_MODEL_ID=gemini-2.5-flash
PLANNER_AGENT_MODEL_TYPE=google
PLANNER_AGENT_MODEL_ID=gemini-2.5-flash
COMPUTER_USE_AGENT_MODEL_TYPE=google
COMPUTER_USE_AGENT_MODEL_ID=gemini-2.5-flash
GEMINI_TIMEOUT=20
GEMINI_MAX_RETRIES=1

# Google OAuth Login
GOOGLE_LOGIN_CLIENT_ID=756809656093-nammscarkr8bcjavl6qp00fbfikoqo72.apps.googleusercontent.com
GOOGLE_LOGIN_CLIENT_SECRET=
GOOGLE_LOGIN_DESKTOP_REDIRECT_URI=http://127.0.0.1:36478
""".replace("JWT_SECRET=Arkaios_Super_Secret_Key_777!", f"JWT_SECRET={secrets.token_urlsafe(48)}"))
load_dotenv(env_path, override=True)

from main import app

if __name__ == "__main__":
    multiprocessing.freeze_support()
    uvicorn.run(app, host="0.0.0.0", port=8000)
