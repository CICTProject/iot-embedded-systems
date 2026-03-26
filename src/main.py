import sys
import os
import threading
import time
import json
import requests
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.sensor_tools import read_temperature, get_camera_feed, set_fan_speed
from src.tasks.ota_task import process_ota_update
from src.agents.agents import evaluate_energy_state

app = FastAPI(title="IoT Edge Node")

class FanPayload(BaseModel):
    speed: int

class OTAPayload(BaseModel):
    version: str

@app.get("/health")
def health():
    return {"status": "ok", "uptime": time.time()}

@app.get("/temperature")
def temperature():
    return {"sensor": "temperature", "value": read_temperature()}

@app.get("/camera")
def camera():
    return get_camera_feed()

@app.post("/fan")
def fan(payload: FanPayload):
    return set_fan_speed(payload.speed)

@app.post("/ota-update")
def ota(payload: OTAPayload):
    success = process_ota_update(payload.version)
    return {"operation": "OTA", "status": "completed" if success else "failed"}

def start_server():
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="critical")

def run_cli():
    time.sleep(2)
    base_url = "http://127.0.0.1:8000"
    
    config_path = os.path.join("configs", "device_config.json")
    with open(config_path, "r") as f:
        config = json.load(f)
    
    while True:
        print(f"\n--- Device: {config['device_id']} ---")
        print("1. Health Check")
        print("2. Read Temperature")
        print("3. Check Camera")
        print("4. Set Fan Speed")
        print("5. Trigger OTA Update")
        print("6. Agent: Evaluate Energy State")
        print("0. Exit")
        
        choice = input("Select option: ")
        
        try:
            if choice == "1":
                print(requests.get(f"{base_url}/health").json())
            elif choice == "2":
                print(requests.get(f"{base_url}/temperature").json())
            elif choice == "3":
                print(requests.get(f"{base_url}/camera").json())
            elif choice == "4":
                s = input("Enter target speed: ")
                print(requests.post(f"{base_url}/fan", json={"speed": int(s)}).json())
            elif choice == "5":
                v = input("Enter OTA version: ")
                print(requests.post(f"{base_url}/ota-update", json={"version": v}).json())
            elif choice == "6":
                b = int(input("Enter current battery percentage: "))
                state = evaluate_energy_state(b)
                print(f"Agent decision -> Switch to state: {state}")
            elif choice == "0":
                print("Exiting...")
                break
            else:
                print("Invalid selection.")
        except Exception as e:
            print(f"Request Error: {e}")

if __name__ == "__main__":
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    run_cli()