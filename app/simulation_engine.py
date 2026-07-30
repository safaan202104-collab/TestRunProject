import os
import json
import uuid
from datetime import datetime

RUNTIME_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "runtime"))
SESSIONS_DIR = os.path.join(RUNTIME_DIR, "sessions")
QUEUE_FILE = os.path.join(RUNTIME_DIR, "queue.jsonl")

os.makedirs(RUNTIME_DIR, exist_ok=True)
os.makedirs(SESSIONS_DIR, exist_ok=True)

def generate_simulated_message(message: str, channel: str = "sms", language: str = "English", scenario: str = "Custom", patient_id: str = None) -> dict:
    if not patient_id:
        patient_id = f"sim_pat_{uuid.uuid4().hex[:6]}"
        
    from_address = f"+1555{uuid.uuid4().hex[:6]}"
    if channel == "email":
        from_address = f"{patient_id}@example.com"
        
    now_str = datetime.now().isoformat()
    
    sim_id = f"sim_{uuid.uuid4().hex[:8]}"
    
    entry = {
        "id": sim_id,
        "category": scenario,
        "note": f"Simulated {language} {channel} message",
        "input": {
            "message": {
                "channel": channel,
                "from": from_address,
                "body": message
            },
            "patient_id": patient_id,
            "now": now_str
        }
    }
    
    # Save to runtime queue
    with open(QUEUE_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
        
    return entry

def clear_simulation_queue():
    if os.path.exists(QUEUE_FILE):
        os.remove(QUEUE_FILE)
