import multiprocessing
import uvicorn
import os
from dotenv import load_dotenv

# Initialize env file in AppData
app_data_dir = os.path.join(os.path.expanduser("~"), "AppData", "Local", "NeuralAgent")
os.makedirs(app_data_dir, exist_ok=True)
env_path = os.path.join(app_data_dir, "API_KEYS.env")

if not os.path.exists(env_path):
    with open(env_path, "w") as f:
        f.write("# Pega aqui tu llave de Gemini y reinicia la aplicacion\nGEMINI_API_KEY=\nJWT_SECRET=Arkaios_Super_Secret_Key_777!\nJWT_ISS=NeuralAgent_Local\n")
        
load_dotenv(env_path)

from main import app

if __name__ == "__main__":
    multiprocessing.freeze_support()
    uvicorn.run(app, host="0.0.0.0", port=8000)

