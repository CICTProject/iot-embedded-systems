# Development in progress - not fully implemented yet
"""
MCP Server tools for controlling ESP32 Camera module.
Provides tools to capture images, stream live video, manage settings, and SD card operations.
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


@mcp_server.tool(name="get_camera_metadata")
async def get_camera_metadata(
    host: Optional[str] = None,
    port: Optional[int] = None,
) -> str:
    """
    Get current camera metadata and status including device info, settings, and endpoints.
    
    Args:
        host: ESP32 device IP address (default: 192.168.1.100)
        port: ESP32 web server port (default: 80)
        
    Returns:
        JSON string containing camera metadata, current configuration, and available endpoints
    """
    if host is None:
        host = ESP32_DEFAULT_HOST
    if port is None:
        port = ESP32_DEFAULT_PORT
    
    url = get_esp32_url(host, port) + ESP32_ENDPOINTS["metadata"]
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            metadata = response.json()
            return json.dumps(metadata, indent=2)
            
    except httpx.ConnectError:
        return f"Error: Cannot connect to ESP32 camera at {host}:{port}"
    except httpx.HTTPStatusError as e:
        return f"Error: HTTP {e.response.status_code} from ESP32 camera"
    except Exception as e:
        return f"Error fetching metadata: {str(e)}"


@mcp_server.tool(name="control_camera")
async def control_camera(
    settings: dict[str, Any],
    host: Optional[str] = None,
    port: Optional[int] = None,
) -> str:
    """
    Control camera settings like resolution, quality, brightness, contrast, and flash.
    
    Args:
        settings: Dictionary of camera settings to update. Supported keys:
            - active: bool (enable/disable camera)
            - flash: "on" or "off" (control flash LED)
            - framesize: string (QQVGA, QVGA, VGA, SVGA, XGA, SXGA, UXGA)
            - quality: int (10-63, lower = better quality)
            - brightness: int (-2 to 2)
            - contrast: int (-2 to 2)
            - vflip: bool (vertical flip)
            - hmirror: bool (horizontal mirror)
            Example: {"framesize": "VGA", "quality": 12, "brightness": 1}
        host: ESP32 device IP address (default: 192.168.1.100)
        port: ESP32 web server port (default: 80)
        
    Returns:
        Status message confirming settings were applied
    """
    if host is None:
        host = ESP32_DEFAULT_HOST
    if port is None:
        port = ESP32_DEFAULT_PORT
    
    url = get_esp32_url(host, port) + ESP32_ENDPOINTS["control"]
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                url,
                json=settings,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            result = response.json()
            return json.dumps(result, indent=2)
            
    except httpx.ConnectError:
        return f"Error: Cannot connect to ESP32 camera at {host}:{port}"
    except httpx.HTTPStatusError as e:
        return f"Error: HTTP {e.response.status_code} from ESP32 camera"
    except Exception as e:
        return f"Error controlling camera: {str(e)}"


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


@mcp_server.tool(name="save_image_to_sdcard")
async def save_image_to_sdcard(
    host: Optional[str] = None,
    port: Optional[int] = None,
) -> str:
    """
    Capture and save current image to SD card on the ESP32 device.
    
    Args:
        host: ESP32 device IP address (default: 192.168.1.100)
        port: ESP32 web server port (default: 80)
        
    Returns:
        Status message with filename and size information
    """
    if host is None:
        host = ESP32_DEFAULT_HOST
    if port is None:
        port = ESP32_DEFAULT_PORT
    
    url = get_esp32_url(host, port) + ESP32_ENDPOINTS["sdcard_save"]
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url)
            response.raise_for_status()
            
            result = response.json()
            return json.dumps(result, indent=2)
            
    except httpx.ConnectError:
        return f"Error: Cannot connect to ESP32 camera at {host}:{port}"
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            return "Error: Camera is disabled"
        elif e.response.status_code == 500:
            return "Error: SD card not mounted or capture failed"
        return f"Error: HTTP {e.response.status_code} from ESP32 camera"
    except Exception as e:
        return f"Error saving image to SD card: {str(e)}"


@mcp_server.tool(name="list_sdcard_files")
async def list_sdcard_files(
    host: Optional[str] = None,
    port: Optional[int] = None,
) -> str:
    """
    List all files stored on the SD card of the ESP32 device.
    
    Args:
        host: ESP32 device IP address (default: 192.168.1.100)
        port: ESP32 web server port (default: 80)
        
    Returns:
        JSON listing of files with names, sizes, and truncation status
    """
    if host is None:
        host = ESP32_DEFAULT_HOST
    if port is None:
        port = ESP32_DEFAULT_PORT
    
    url = get_esp32_url(host, port) + ESP32_ENDPOINTS["sdcard_list"]
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            result = response.json()
            return json.dumps(result, indent=2)
            
    except httpx.ConnectError:
        return f"Error: Cannot connect to ESP32 camera at {host}:{port}"
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 500:
            return "Error: SD card not mounted"
        return f"Error: HTTP {e.response.status_code} from ESP32 camera"
    except Exception as e:
        return f"Error listing SD card files: {str(e)}"


@mcp_server.tool(name="reboot_device")
async def reboot_device(
    host: Optional[str] = None,
    port: Optional[int] = None,
) -> str:
    """
    Reboot the ESP32 camera device.
    
    Args:
        host: ESP32 device IP address (default: 192.168.1.100)
        port: ESP32 web server port (default: 80)
        
    Returns:
        Confirmation message that reboot has been initiated
    """
    if host is None:
        host = ESP32_DEFAULT_HOST
    if port is None:
        port = ESP32_DEFAULT_PORT
    
    url = get_esp32_url(host, port) + ESP32_ENDPOINTS["reboot"]
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url)
            response.raise_for_status()
            
            result = response.json()
            return json.dumps(result, indent=2)
            
    except httpx.ConnectError:
        return f"Error: Cannot connect to ESP32 camera at {host}:{port}"
    except httpx.TimeoutException:
        # Timeout is expected as device reboots immediately
        return "Device reboot initiated (connection timeout expected)"
    except Exception as e:
        return f"Note: Device may be rebooting: {str(e)}"


@mcp_server.tool(name="check_esp32_connection")
async def check_esp32_connection(
    host: Optional[str] = None,
    port: Optional[int] = None,
) -> str:
    """
    Check connectivity and basic status of the ESP32 camera device.
    
    Args:
        host: ESP32 device IP address (default: 192.168.1.100)
        port: ESP32 web server port (default: 80)
        
    Returns:
        Connection status message with device information
    """
    if host is None:
        host = ESP32_DEFAULT_HOST
    if port is None:
        port = ESP32_DEFAULT_PORT
    
    url = get_esp32_url(host, port) + ESP32_ENDPOINTS["metadata"]
    
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            metadata = response.json()
            device_id = metadata.get("device_id", "unknown")
            status = metadata.get("status", "unknown")
            
            return f"ESP32 camera '{device_id}' is online at {host}:{port} - Status: {status}"
            
    except httpx.ConnectError:
        return f"Cannot connect to ESP32 camera at {host}:{port}"
    except httpx.TimeoutException:
        return f"Connection timeout to ESP32 camera at {host}:{port}"
    except Exception as e:
        return f"Error connecting to ESP32 camera: {str(e)}"
