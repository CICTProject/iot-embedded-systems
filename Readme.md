### INSTALLATION

```bash
# Create and activate virtual environment
py -m venv venv
source venv\Scripts\activate

# Install required dependencies
pip install fastapi uvicorn requests pydantic
```

### PROJECT STRUCTURE

```text
iot-embedded-system/
├── src/
│   ├── main.py              # CLI entry point and FastAPI server initialization
│   ├── crew.py              # Edge-level orchestration and task routing
│   ├── agents/
│   │   └── agents.py        # Environmental reasoning and energy state evaluation
│   └── tasks/
│       └── ota_task.py      # OTA update processing and SHA256 verification logic
├── configs/
│   ├── device_config.json   # Device profiles (ID, location x/y/z, supported services)
│   └── energy_policies.yaml # Energy constraints and algorithm thresholds
├── tests/
│   └── test_api.py          # Unit tests for hardware endpoint simulation
├── docs/                    # Hardware schematics and OTA architecture documentation
├── tools/
│   └── sensor_tools.py      # Hardware interaction mock functions (Camera, Temp, Fan)
├── data/                    # Logs and aggregated sensor telemetry
└── .env                     # Environment variables (Broker IPs, Ports)
```

### RUN THE APPLICATION
Start the background REST API server and the interactive CLI menu:
```bash
# CLI menu:
py src/main.py
```