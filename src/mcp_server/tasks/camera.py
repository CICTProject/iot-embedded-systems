# Development in progress - not fully implemented yet
"""
MCP Server tools for controlling ESP32 Camera module.
Provides tools to capture images, stream live video, and manage camera settings.
"""

import httpx
import json
from pathlib import Path
from typing import Optional, Any
from mcp.types import Tool, TextContent, ImageContent
from . import mcp_server

from src.utils.esp32cam import (
    ESP32_DEFAULT_HOST,
    ESP32_DEFAULT_PORT,
    ESP32_ENDPOINTS,
    CAMERA_FRAMESIZE,
    CAMERA_QUALITY,
    CAMERA_BRIGHTNESS,
    CAMERA_CONTRAST,
    CAMERA_SATURATION
)

from src.utils.esp32cam import get_esp32_url


@mcp_server.tool(name="capture_image")
async def capture_image(
    host: Optional[str] = None,
    port: Optional[int] = None,
    save_path: Optional[str] = None,
) -> str:
    """
    Capture a single image from the ESP32 camera.
    
    Args:
        host: ESP32 device IP address (default: 192.168.1.100)
        port: ESP32 web server port (default: 80)
        save_path: Optional local file path to save the captured image
        
    Returns:
        Status message with image details or file path if saved
    """
    if host is None:
        host = ESP32_DEFAULT_HOST
    if port is None:
        port = ESP32_DEFAULT_PORT
    
    url = get_esp32_url(host, port) + ESP32_ENDPOINTS["capture"]
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            image_data = response.content
            image_size = len(image_data)
            
            # Save image if path provided
            if save_path:
                path = Path(save_path)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(image_data)
                return f"Image captured and saved to {save_path} ({image_size} bytes)"
            
            return f"Image captured successfully ({image_size} bytes). Use save_path parameter to save locally."
            
    except httpx.ConnectError:
        return f"Error: Cannot connect to ESP32 camera at {host}:{port}"
    except httpx.HTTPStatusError as e:
        return f"Error: HTTP {e.response.status_code} from ESP32 camera"
    except Exception as e:
        return f"Error capturing image: {str(e)}"


@mcp_server.tool(name="get_stream_url")
async def get_stream_url(
    host: Optional[str] = None,
    port: Optional[int] = None,
) -> str:
    """
    Get the MJPEG stream URL for live video streaming from ESP32 camera.
    
    Args:
        host: ESP32 device IP address (default: 192.168.1.100)
        port: ESP32 web server port (default: 80)
        
    Returns:
        Complete URL for the MJPEG stream endpoint
    """
    if host is None:
        host = ESP32_DEFAULT_HOST
    if port is None:
        port = ESP32_DEFAULT_PORT
    
    stream_url = get_esp32_url(host, port) + ESP32_ENDPOINTS["stream"]
    return f"MJPEG stream available at: {stream_url}"


@mcp_server.tool(name="save_camera_settings")
async def save_camera_settings(
    settings: dict[str, Any],
    host: Optional[str] = None,
    port: Optional[int] = None,
) -> str:
    """
    Save camera sensor settings to the ESP32 device.
    
    Args:
        settings: Dictionary of camera settings (e.g., resolution, brightness, contrast)
                 Example: {"framesize": 6, "quality": 12, "brightness": 1}
        host: ESP32 device IP address (default: 192.168.1.100)
        port: ESP32 web server port (default: 80)
        
    Returns:
        Status message confirming settings were saved
    """
    if host is None:
        host = ESP32_DEFAULT_HOST
    if port is None:
        port = ESP32_DEFAULT_PORT
    
    url = get_esp32_url(host, port) + ESP32_ENDPOINTS["prompt"]
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # Send settings as POST request
            response = await client.post(
                url,
                json={"action": "save_settings", "settings": settings}
            )
            response.raise_for_status()
            
            return f"Camera settings saved successfully: {json.dumps(settings)}"
            
    except httpx.ConnectError:
        return f"Error: Cannot connect to ESP32 camera at {host}:{port}"
    except httpx.HTTPStatusError as e:
        return f"Error: HTTP {e.response.status_code} from ESP32 camera"
    except Exception as e:
        return f"Error saving settings: {str(e)}"


@mcp_server.tool(name="load_camera_settings")
async def load_camera_settings(
    host: Optional[str] = None,
    port: Optional[int] = None,
) -> str:
    """
    Load current camera sensor settings from the ESP32 device.
    
    Args:
        host: ESP32 device IP address (default: 192.168.1.100)
        port: ESP32 web server port (default: 80)
        
    Returns:
        JSON string containing current camera settings
    """
    if host is None:
        host = ESP32_DEFAULT_HOST
    if port is None:
        port = ESP32_DEFAULT_PORT
    
    url = get_esp32_url(host, port) + ESP32_ENDPOINTS["prompt"]
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # Fetch settings as GET request
            response = await client.get(url)
            response.raise_for_status()
            
            settings = response.json()
            return json.dumps(settings, indent=2)
            
    except httpx.ConnectError:
        return f"Error: Cannot connect to ESP32 camera at {host}:{port}"
    except httpx.HTTPStatusError as e:
        return f"Error: HTTP {e.response.status_code} from ESP32 camera"
    except Exception as e:
        return f"Error loading settings: {str(e)}"


@mcp_server.tool(name="save_and_load_image")
async def save_and_load_image(
    save_action: str,
    local_path: Optional[str] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
) -> str:
    """
    Save current captured image or load a previously captured image from ESP32.
    
    Args:
        save_action: "save" to save current image, "load" to load previous image
        local_path: Local file path for saving or reference to previously saved image
        host: ESP32 device IP address (default: 192.168.1.100)
        port: ESP32 web server port (default: 80)
        
    Returns:
        Status message with operation result
    """
    if host is None:
        host = ESP32_DEFAULT_HOST
    if port is None:
        port = ESP32_DEFAULT_PORT
    
    url = get_esp32_url(host, port) + ESP32_ENDPOINTS["prompt"]
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            payload = {
                "action": save_action,
                "path": local_path
            }
            
            response = await client.post(url, json=payload)
            response.raise_for_status()
            
            if save_action == "save":
                return f"Image saved to ESP32 storage at: {local_path}"
            else:
                return f"Image loaded from ESP32 storage: {local_path}"
                
    except httpx.ConnectError:
        return f"Error: Cannot connect to ESP32 camera at {host}:{port}"
    except httpx.HTTPStatusError as e:
        return f"Error: HTTP {e.response.status_code} from ESP32 camera"
    except Exception as e:
        return f"Error in save/load operation: {str(e)}"


@mcp_server.tool(name="check_esp32_connection")
async def check_esp32_connection(
    host: Optional[str] = None,
    port: Optional[int] = None,
) -> str:
    """
    Check connectivity to the ESP32 camera device.
    
    Args:
        host: ESP32 device IP address (default: 192.168.1.100)
        port: ESP32 web server port (default: 80)
        
    Returns:
        Connection status message
    """
    if host is None:
        host = ESP32_DEFAULT_HOST
    if port is None:
        port = ESP32_DEFAULT_PORT
    
    url = get_esp32_url(host, port)
    
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(url)
            return f"✓ ESP32 camera is online at {host}:{port} (HTTP {response.status_code})"
            
    except httpx.ConnectError:
        return f"✗ Cannot connect to ESP32 camera at {host}:{port}"
    except httpx.TimeoutException:
        return f"✗ Connection timeout to ESP32 camera at {host}:{port}"
    except Exception as e:
        return f"✗ Error connecting to ESP32 camera: {str(e)}"
