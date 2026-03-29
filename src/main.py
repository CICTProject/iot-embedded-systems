import time
import uuid
import logging
from typing import Any, List, Dict, Optional, Union

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict

from src.llm.agent import LLMAgent
from src.mcp_server.tasks import mcp_server
from src.utils.chat import extract_last_user_message, ChatMessage

from fastapi.responses import StreamingResponse
import json

from src.mcp_server.tasks.system import get_deployment_status, get_network_topology, list_medical_devices, find_available_devices, get_device_details, query_devices_by_capability, read_medical_metric, read_multiple_medical_metrics, get_metric_history, get_active_deployment_alarms, acknowledge_deployment_alarm, execute_device_command
from src.mcp_server.tasks.camera import capture_image, get_stream_url, save_camera_settings, load_camera_settings, save_and_load_image, check_esp32_connection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_agent() -> LLMAgent:
    agent = LLMAgent()
    agent.register_tools({
        # System tools
        "get_deployment_status": get_deployment_status,
        "get_network_topology": get_network_topology,
        "list_medical_devices": list_medical_devices,
        "find_available_devices": find_available_devices,
        "get_device_details": get_device_details,
        "query_devices_by_capability": query_devices_by_capability,
        "read_medical_metric": read_medical_metric,
        "read_multiple_medical_metrics": read_multiple_medical_metrics,
        "get_metric_history": get_metric_history,
        "get_active_deployment_alarms": get_active_deployment_alarms,
        "acknowledge_deployment_alarm": acknowledge_deployment_alarm,
        "execute_device_command": execute_device_command,
        # Camera tools
        "capture_image": capture_image, 
        "get_stream_url": get_stream_url,
        "save_camera_settings": save_camera_settings,
        "load_camera_settings": load_camera_settings,
        "save_and_load_image": save_and_load_image,
        "check_esp32_connection": check_esp32_connection,
    })
    return agent


class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="allow") # allow extra fields for flexibility
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0
    stream: Optional[bool] = False


app = FastAPI(title="LLM Agent for IOT Deployment Management in Nursing Home Environment", version="1.0")

AGENT: Optional[LLMAgent] = None
CHATGPT_MODEL_ID = "llm-agent-chatgpt"  
OLLAMA_MODEL_ID = "llm-agent-ollama"

# API Endpoints for Web UI and LLM interaction
@app.on_event("startup")
async def startup():
    global AGENT
    AGENT = create_agent()


@app.get("/v1/models")
async def list_models():
    now = int(time.time())
    return {
        "object": "list",
        "data": [
            {
                "id": CHATGPT_MODEL_ID,
                "object": "model",
                "created": now,
                "owned_by": "local",
            },
            {
                "id": OLLAMA_MODEL_ID,
                "object": "model",
                "created": now,
                "owned_by": "local",
            }
        ],
    }



@app.post(
    "/v1/chat/completions",
    responses={
        400: {"description": "Bad Request"},
        500: {"description": "Internal Server Error"},
    },
)
async def chat_completions(req: ChatCompletionRequest):
    if req.model not in [CHATGPT_MODEL_ID, OLLAMA_MODEL_ID]:
        raise HTTPException(status_code=400, detail=f"Unknown model: {req.model}")
    if AGENT is None:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    
    user_text = extract_last_user_message(req.messages)
    if not user_text:
        raise HTTPException(status_code=400, detail="Empty message")

    try:
        if req.model == CHATGPT_MODEL_ID or req.model == OLLAMA_MODEL_ID:
            answer = await AGENT.process(user_text)
        else:
            answer = "[Unknown model]"
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    completion_id = f"chatcmpl-{uuid.uuid4().hex}"
    now = int(time.time())

    # Handle streaming response if requested
    if req.stream:
        async def event_gen():
            chunk = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": now,
                "model": req.model,
                "choices": [{
                    "index": 0,
                    "delta": {"role": "assistant", "content": answer},
                    "finish_reason": None
                }]
            }
            yield f"data: {json.dumps(chunk)}\n\n"
            done = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": now,
                "model": req.model,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]
            }
            yield f"data: {json.dumps(done)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(event_gen(), media_type="text/event-stream")

    # Handle non-streaming response
    return {
        "id": completion_id,
        "object": "chat.completion",
        "created": now,
        "model": req.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": str(answer)},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }