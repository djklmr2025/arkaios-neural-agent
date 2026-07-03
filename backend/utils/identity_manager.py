import os
import json
import uuid
import requests
import threading
from datetime import datetime, timezone

VAULT_API_URL = "https://ais-pre-xtl6gtdgpojowhvfuibzxm-607191134694.us-east1.run.app/api/v1/sovereign-db"

def get_app_data_dir():
    app_data_dir = os.path.join(os.path.expanduser("~"), "AppData", "Local", "NeuralAgent")
    os.makedirs(app_data_dir, exist_ok=True)
    return app_data_dir

def generate_soul_id():
    raw_uuid = uuid.uuid4().hex.upper()
    # Format: ARKAIOS-NODE-XXXX-XXXX
    return f"ARKAIOS-NODE-{raw_uuid[:4]}-{raw_uuid[4:8]}"

def load_or_create_identity():
    identity_path = os.path.join(get_app_data_dir(), "node_identity.json")
    if os.path.exists(identity_path):
        with open(identity_path, "r") as f:
            return json.load(f)
    
    # Generate new identity
    soul_id = generate_soul_id()
    identity_data = {
        "agentId": soul_id,
        "name": f"NeuralAgent Node ({soul_id})",
        "status": "active",
        "amrBalance": 100.00,
        "btcBacking": 0.01,
        "ethBacking": 0.50,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    with open(identity_path, "w") as f:
        json.dump(identity_data, f, indent=4)
        
    return identity_data

def register_node_to_vault(identity_data):
    try:
        payload = {
            "agentProfiles": [
                {
                    "agentId": identity_data["agentId"],
                    "name": identity_data["name"],
                    "status": "active",
                    "amrBalance": identity_data["amrBalance"],
                    "btcBacking": identity_data["btcBacking"],
                    "ethBacking": identity_data["ethBacking"]
                }
            ]
        }
        response = requests.post(VAULT_API_URL, json=payload, timeout=15)
        if response.status_code == 200:
            print(f"[IdentityManager] Node {identity_data['agentId']} successfully registered/synced with PRIMORDIAL-VAULT.")
        else:
            print(f"[IdentityManager] Failed to sync node with Vault. Status: {response.status_code}")
    except Exception as e:
        print(f"[IdentityManager] Error connecting to PRIMORDIAL-VAULT: {e}")

def boot_identity():
    identity_data = load_or_create_identity()
    print(f"[IdentityManager] Booting Identity: {identity_data['agentId']}")
    
    # Set it as an environment variable so the rest of the app can easily access it
    os.environ["ARKAIOS_NODE_SOUL_ID"] = identity_data["agentId"]
    
    # Register/Sync in background
    threading.Thread(target=register_node_to_vault, args=(identity_data,), daemon=True).start()
    
    return identity_data
