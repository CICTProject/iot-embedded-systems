# LLMThings: Intelligent Large-Scale IoT Deployments in Nursing Home Environment. 


## Overview

Modern medical research laboratories have integrated gradually into smart workspace environments, with the integration of heterogeneous IoT devices and services [2,3]. Large Language Models (LLMs) have emphasized the capabilities in reasoning, planning, and task orchestration, providing a promising methodology for translating natural user intents into executable laboratory operations [4,5]. This project aims to develop an LLM-driven deployment engine [1,6] for medical research laboratories. The system (Figure 1) enables clinicians to interact with medical datasets, IoT-connected sequencing devices, and AI models through natural language queries, automating data retrieval, analysis, and workflow execution [7]. This project aims to the first-round candidation of Concours Innovation Creative Challenge 2026 in the intersection domain between IOT, Intelligence Artificielle (AI) and Edge-Cloud Computing. Our complete work presents in [CICT Hackathon Round 1 Presentation](https://docs.google.com/presentation/d/1wKNIP_Rr-3uXvEWs3CL8ITc8lvj-x6bo/edit?slide=id.g3cb0a89473b_1_1384#slide=id.g3cb0a89473b_1_1384).

![Figure 1: Fall detection in nursing home scenario](docs/scenario/architecture.png)
*Figure 1: Fall detection in nursing home scenario.*

---

## Project Structure

```
iot-embedded-systems/
├── src/
│   ├── main.py                    # CLI entry point (LLM Agent → MCP execution)
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── system_prompt.txt      # Operation prompts
│   │   └── agent.py               # LLM Agent 
│   ├── mcp_server/
│   │   ├── main.py                # FastMCP server entry point
│   │   └── tasks/                 # FastMCP server instance
│   ├── api/                       # FastAPI client
│   ├── iot/                       # ESP32-based sensors stimulation
│   └── db/                        # Database schema (SQLite)
├── test/                          # Unit tests
├── utils/                         # Utility tools
├── swagger.json                   # API specification docs
├── pyproject.toml                 # Poetry dependencies
├── .python-version                # Python version
├── uv.lock                        # WebUI package requirements
└── .env.template                  # Environment variables
```

---

## Quick Setup

### Prerequisites
```bash
# Dependencies installation fully pinned via poetry.lock (deployment lock standard)
poetry install --no-root
uv sync  # WebUI package 
poetry run python src/db/main.py # Seed database mitigation (Future replacement with real-time iot device data)
```

### Running the Application (LLM User Intent)

```bash
# Lauch Open WebUI  
uv run --with open-webui open-webui serve
poetry run uvicorn src.main:app --host 0.0.0.0 --port 8001
```
> **Note:** Our project prioritizes the use of InfluxDB as it enables high-throughput ingestion, efficient storage, and time-based querying of large-scale time-series IOT device data with open UI web browser in http://localhost:8086. Data query format in InfluxDB:

```bash
from(bucket: "medical_sensors")
  |> range(start: -30d)
  |> limit(n: 50)
```

---
## Basic Flow: From LLM User Intent to IOT device deployment control.
The deployment monitoring agent (Figure 2) is responsible for maintaining an up-to-date data structure that records the status of each device and its connectivity. 
![Deployment Agent Workflow](docs/llm/workflow.png)
*Figure 2: IOT Deployment Agent Workflow with specific examples.*
### 1. LLM to MCP (Tool Registration)
- LLM Deployment Agent maintains real-time data structures for all deployed devices with unique identifiers. For each ESP32-based device, some information details such as registered microservices (`/camera`, `/sensor`, etc.), communication protocols (HTTP, MQTT, CoAP), and service-specific metadata (e.g., camera FoV, detection area, resolution, sampling frequency).

- MCP Server tools are registered in the agent and correspond to network operations, current tools are, with full CRUD (create, read, update and delete) functionality.

Open WebUI (Future replacement with Shacdn256/Boostrap Fontend) has supported 2 LLMs model (OpenAI, Ollama), implement FastAPIs to retrieve model & chat information with LLM agents, all the API docs in http://localhost:8001/docs#/ with the launching interface in http://localhost:8001 for local version, further deploy in Vercel.

[![LLM Demo View](https://img.youtube.com/vi/E6YcugELNrc/maxresdefault.jpg)](https://youtu.be/E6YcugELNrc)

*Prototype Alpha v1.0.1: Workflow Demo in IOT deployment scenario*

### 2. MCP to ESP32 (FastAPI Bridge)

- MCP server (`src/mcp_server/`) receives tool calls from the agent and maps them to REST endpoints. FastAPI clients translate LLM-generated tool calls into HTTP requests targeting actual ESP32 devices via deployment endpoints (`/api/deploy`, `/api/control`, `/api/status`). All service details (**devices**, etc) documented in `swagger.json`.

> **Note:** Some tools and API mappings are under development, see more in `src/mcp_server` for tool registration.

### 3. ESP32-based Execution (Device layer)

- ESP32-based device (ESP32 CAM, ECG sensors) receives deployment instructions, loads camera-based fall detection models, configures inference pipelines, and executes real-time monitoring workflows. Device details (IP address, device status (active, inactive, idle, sleep, deep sleep), location coordinates (x, y, z)) streamed back to FastAPI for InfluxDB database retrieve, with the implementations in `esp32/` for resource-constrained devices.

---

## References

### Theory-based ressources 

[1] LLMind: Orchestrating AI and IoT with LLM for Complex Task Execution. arXiv. Available: https://arxiv.org/pdf/2312.09007

[2] SmartIntent: A Serverless LLM-Oriented Architecture for Intent-Driven Building Automation. ResearchGate. Available: https://www.researchgate.net/publication/397059674

[3] LLM Agents for Internet of Things (IoT) Applications. CS598 JY2-Topics in LLM Agents. Available: https://openreview.net/pdf?id=BikB3f8ByV

[4] A Survey on IoT Application Architectures. MDPI Sensors. Available: https://www.mdpi.com/1424-8220/24/16/5320

[5] Tree-of-Thought vs Chain-of-Thought for LLMs. arXiv. Available: https://arxiv.org/html/2401.14295v3

[6] Introduction to Model Context Protocol. Available: https://anthropic.skilljar.com/introduction-to-model-context-protocol

[7] Model Context Protocol (MCP): Landscape, Security Threats, and Future Research Directions. arXiv. Available: https://arxiv.org/pdf/2503.23278

### Code implementation ressources (Additional)
#### MCP Server
1. MCP SDK Integration: [modelcontextprotocol.io/docs/sdk](https://modelcontextprotocol.io/docs/sdk)
2. MCP Learning Resources: [youtu.be/QIOk4XZ5XNU](https://youtu.be/QIOk4XZ5XNU)
3. Integration with FastMCP via [langchain-mcp-adapters](https://github.com/langchain-ai/langchain-mcp-adapters)

#### Real-time Database
4. InfluxDB: [influx-iot-dev-guide](https://influxdata.github.io/iot-dev-guide/iot-center.html)
5. REST API with InfluxDB: [iot-api-python](https://github.com/influxdata/iot-api-python)
6. Sharding in Redis local server (Future development): [redis-influxdb-iot](https://github.com/Bienvenu2004/capteursIotRedis-InfluxDB)

#### UI Package
7. Pipx: [github.com/pypa/pipx](https://github.com/pypa/pipx)
8. Poetry: [python-poetry.org/docs](https://python-poetry.org/docs)
9. Open WebUI: [openwebui.com/docs](https://docs.openwebui.com/getting-started/quick-start/)

### Hardware configuration
10. ESP32 CAM: [esp32cam.html/docs](https://hieromon.github.io/AutoConnect/esp32cam.html)
11. ESP3 CAM-MB-USB: [esp32camusb.com/docs](https://randomnerdtutorials.com/upload-code-esp32-cam-mb-usb/)
12. ESP32 CAM Video Streaming: [esp32camfunctionality.com/docs](https://lastminuteengineers.com/getting-started-with-esp32-cam/)

---
## Future Work
- Implement deployment algorithms & test case in camera-based scenarios.
- Develop & Integrate with medical sensors & ESP32 CAM.
