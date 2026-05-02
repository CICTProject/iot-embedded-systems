"""
MCP Server tools for ECG (Electrocardiogram) sensor management.
Provides tools to read ECG waveform data, monitor heart rate, manage sensor calibration,
and analyze cardiac metrics.
"""

import httpx
import json
from typing import Optional
from datetime import datetime
from . import mcp_server

from src.utils.system import write_ecg_data

import logging

logger = logging.getLogger(__name__)

# ECG sensor configuration
ECG_DEFAULT_HOST = "192.168.1.77"
ECG_DEFAULT_PORT = 80
ECG_ENDPOINTS = {
    "metadata": "/api/ecg",
}

# Standard ECG sampling rates (Hz)
ECG_SAMPLING_RATES = {
    "low": 100,
    "medium": 250,
    "high": 500,
    "clinical": 1000,
}


def get_ecg_url(host: str, port: int) -> str:
    """Construct base URL for ECG device."""
    return f"http://{host}:{port}"


@mcp_server.tool(name="get_ecg_metadata")
async def get_ecg_metadata(
    host: Optional[str] = None,
    port: Optional[int] = None,
    save_to_db: bool = True,
) -> str:
    """
    Get current ECG sensor metadata and status including device info, sampling rate, and calibration.
    
    Args:
        host: ECG device IP address (default: 192.168.1.77)
        port: ECG web server port (default: 80)
        save_to_db: Whether to save ECG metadata to database (default: True)
        
    Returns:
        JSON string containing ECG metadata, current configuration, and available endpoints
    """
    if host is None:
        host = ECG_DEFAULT_HOST
    if port is None:
        port = ECG_DEFAULT_PORT
    
    url = get_ecg_url(host, port) + ECG_ENDPOINTS["metadata"]
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            metadata = response.json()
            
            # Save ECG metadata to database
            if save_to_db:
                device_id = metadata.get("device_id", "ecg_unknown")
                status = metadata.get("status", "unknown")
                ecg_raw = metadata.get("ecg_raw", 0)
                unit = metadata.get("unit", "mV_raw")
                
                write_ecg_data(
                    device_id=device_id,
                    metric="ecg_metadata",
                    value=ecg_raw,
                    unit=unit,
                    status=status,
                    timestamp=datetime.utcnow()
                )
                logger.info(f"Saved ECG metadata for {device_id} to database")
            
            return json.dumps(metadata, indent=2)
            
    except httpx.ConnectError:
        return f"Error: Cannot connect to ECG device at {host}:{port}"
    except httpx.HTTPStatusError as e:
        return f"Error: HTTP {e.response.status_code} from ECG device"
    except Exception as e:
        return f"Error fetching ECG metadata: {str(e)}"

@mcp_server.tool(name="check_ecg_connection")
async def check_ecg_connection(
    host: Optional[str] = None,
    port: Optional[int] = None,
) -> str:
    """
    Check connectivity and basic status of the ECG sensor device.
    
    Args:
        host: ECG device IP address (default: 192.168.1.77)
        port: ECG web server port (default: 80)
        
    Returns:
        Connection status message with device information
    """
    if host is None:
        host = ECG_DEFAULT_HOST
    if port is None:
        port = ECG_DEFAULT_PORT
    
    url = get_ecg_url(host, port) + ECG_ENDPOINTS["metadata"]
    
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            metadata = response.json()
            device_id = metadata.get("device_id", "unknown")
            status = metadata.get("status", "unknown")
            
            return f"ECG sensor '{device_id}' is online at {host}:{port} - Status: {status}"
            
    except httpx.ConnectError:
        return f"Cannot connect to ECG device at {host}:{port}"
    except httpx.TimeoutException:
        return f"Connection timeout to ECG device at {host}:{port}"
    except Exception as e:
        return f"Error connecting to ECG device: {str(e)}"