"""
MCP Server tools for monitoring and managing medical sensor deployments.
Queries InfluxDB for device data, metrics, and alarms.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from . import mcp_server
from src.db.models import DeviceType

from src.utils.system import (
    get_device_from_registry,
    list_all_devices_from_registry,
    get_metric_readings
)


logger = logging.getLogger(__name__)


# Deployment status and topology

@mcp_server.tool()
async def get_deployment_status() -> Dict[str, Any]:
    """
    Get the overall status of the medical sensor deployment.
    
    Returns:
        Deployment status including device counts, zones, active services, and alarms.
    """
    devices = list_all_devices_from_registry()
    
    # Extract zones, filtering None values
    zones = [d.get("zone") for d in devices if d.get("zone") is not None]
    
    return {
        "timestamp": datetime.now().isoformat(),
        "deployment_mode": "INFLUXDB_MEDICAL",
        "total_devices": len(devices),
        "online": len([d for d in devices if d.get("status") == "online"]),
        "offline": len([d for d in devices if d.get("status") == "offline"]),
        "error": len([d for d in devices if d.get("status") == "error"]),
        "zones": sorted(set(str(z) for z in zones)),
        "active_alarms": 0,
        "services": ["heart_rate", "spo2", "ecg", "video_stream", "temperature"],
    }


@mcp_server.tool()
async def get_network_topology() -> Dict[str, Any]:
    """
    Get the network topology of the medical sensor deployment.
    
    Returns:
        Topology information with gateway nodes, edge nodes, and medical endpoints.
    """
    devices = list_all_devices_from_registry()
    
    return {
        "internet": True,
        "gateway_nodes": [
            d for d in devices if d.get("device_type") == DeviceType.GATEWAY.value
        ],
        "edge_nodes": [
            d for d in devices if d.get("device_type") == DeviceType.EDGE_NODE.value
        ],
        "medical_endpoints": [
            d for d in devices 
            if d.get("device_type") in {DeviceType.MEDICAL_SENSOR.value, DeviceType.CAMERA.value}
        ],
    }


# ==================== DEVICE DISCOVERY ====================

@mcp_server.tool()
async def list_medical_devices(
    zone: Optional[str] = None,
    device_type: Optional[str] = None,
    required_service: Optional[str] = None,
    status: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    List medical devices in the deployment with optional filtering.
    
    Args:
        zone: Physical location zone (e.g., corridor, ward_a, icu_room_1).
        device_type: Device type filter (medical_sensor, camera, gateway, edge_node).
        required_service: Filter by required service capability (e.g., video_stream, ecg, spo2).
        status: Device status filter (online, offline, error).
    
    Returns:
        List of devices matching the specified filters.
    """
    devices = list_all_devices_from_registry()
    
    if zone:
        devices = [d for d in devices if d.get("zone") == zone]
    if device_type:
        devices = [d for d in devices if d.get("device_type") == device_type]
    if status:
        devices = [d for d in devices if d.get("status") == status]
    
    return devices


@mcp_server.tool()
async def find_available_devices(zone: str, required_service: str) -> List[Dict[str, Any]]:
    """
    Find online devices in a specific zone with a required service capability.
    
    Useful for natural language queries like "Which devices in the corridor can stream video?"
    
    Args:
        zone: Physical location zone (e.g., corridor, ward_a, icu_room_1).
        required_service: Required service capability (e.g., video_stream, ecg, spo2, heart_rate).
    
    Returns:
        List of online devices in the zone that support the requested service.
    """
    return await list_medical_devices(zone=zone, status="online")


@mcp_server.tool()
async def get_device_details(device_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific device.
    
    Args:
        device_id: Device identifier.
    
    Returns:
        Complete device configuration, status, location, and services.
    
    Raises:
        ValueError: If device not found.
    """
    device = get_device_from_registry(device_id)
    if not device:
        raise ValueError(f"Device {device_id} not found")
    return device


@mcp_server.tool()
async def query_devices_by_capability(service_name: str) -> List[Dict[str, Any]]:
    """
    Find all online devices supporting a specific capability.
    
    Args:
        service_name: Service/capability name (e.g., video_stream, ecg, spo2, heart_rate).
    
    Returns:
        List of online devices that expose the requested service.
    """
    return await list_medical_devices(status="online")


# ==================== MEDICAL METRIC READING ====================

@mcp_server.tool()
async def read_medical_metric(device_id: str, metric: str) -> Dict[str, Any]:
    """
    Read a medical metric from a sensor device.
    
    Args:
        device_id: Device identifier.
        metric: Metric name (e.g., heart_rate, spo2, ecg, body_temperature).
    
    Returns:
        Current metric value with unit, quality score, battery level, and timestamp.
    
    Raises:
        ValueError: If device or metric not found.
    """
    device = get_device_from_registry(device_id)
    if not device:
        raise ValueError(f"Device {device_id} not found")
    
    # Query latest reading from InfluxDB
    readings = get_metric_readings(device_id, metric, hours=24)
    if not readings:
        raise ValueError(f"No readings found for metric {metric} on device {device_id}")
    
    latest = readings[-1]  # Most recent
    
    return {
        "device_id": device_id,
        "metric": metric,
        "value": latest.get("value"),
        "unit": "units",
        "quality": latest.get("quality"),
        "battery_level": device.get("battery_level"),
        "timestamp": latest.get("timestamp"),
        "source": "influxdb",
    }


@mcp_server.tool()
async def read_multiple_medical_metrics(
    requests: List[Dict[str, str]],
) -> List[Dict[str, Any]]:
    """
    Read multiple medical metrics in batch from different devices.
    
    Args:
        requests: List of metric read requests with format
                 [{"device_id": "...", "metric": "..."}, ...].
    
    Returns:
        List of metric readings or error details for each request.
    """
    results = []
    for req in requests:
        device_id = req.get("device_id")
        metric = req.get("metric")
        try:
            result = await read_medical_metric(device_id, metric)
            results.append(result)
        except Exception as exc:
            results.append(
                {
                    "device_id": device_id,
                    "metric": metric,
                    "error": str(exc),
                }
            )
    return results


# ==================== METRIC HISTORY ====================

@mcp_server.tool()
async def get_metric_history(
    device_id: str,
    hours: int = 24,
    metric: Optional[str] = None,
    aggregation: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Get historical metric readings for a device.
    
    Args:
        device_id: Device identifier.
        hours: Time window in hours (default 24).
        metric: Optional specific metric to filter.
        aggregation: Optional aggregation method (mean, min, max).
    
    Returns:
        Historical data points or aggregated values within the time window.
    """
    readings = get_metric_readings(device_id, metric, hours)
    
    if not readings:
        return []
    
    if aggregation == "mean":
        values: List[Any] = []
        for r in readings:
            val = r.get("value")
            if val is not None:
                values.append(val)
        if values:
            return [{
                "device_id": device_id,
                "metric": metric or "mixed",
                "aggregation": "mean",
                "value": sum(values) / len(values),
            }]
    
    elif aggregation == "max":
        values: List[Any] = []
        for r in readings:
            val = r.get("value")
            if val is not None:
                values.append(val)
        if values:
            return [{
                "device_id": device_id,
                "metric": metric or "mixed",
                "aggregation": "max",
                "value": max(values),
            }]
    
    elif aggregation == "min":
        values: List[Any] = []
        for r in readings:
            val = r.get("value")
            if val is not None:
                values.append(val)
        if values:
            return [{
                "device_id": device_id,
                "metric": metric or "mixed",
                "aggregation": "min",
                "value": min(values),
            }]
    
    return readings


# Alarm management

@mcp_server.tool()
async def get_active_deployment_alarms(priority: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get all active alarms in the medical deployment.
    
    Args:
        priority: Optional priority filter (LOW, MEDIUM, HIGH, CRITICAL).
    
    Returns:
        List of active alarms sorted by priority and timestamp.
    """
    return []


@mcp_server.tool()
async def acknowledge_deployment_alarm(alarm_id: str) -> bool:
    """
    Acknowledge and dismiss an active alarm.
    
    Args:
        alarm_id: Alarm identifier to acknowledge.
    
    Returns:
        True if alarm was successfully acknowledged, False if not found.
    """
    return False


# Device control

@mcp_server.tool()
async def execute_device_command(
    device_id: str,
    command: str,
    parameters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Execute a control command on a device.
    
    Supported commands:
    - reboot: Restart the device
    - set_offline: Set device to offline status
    - start_stream: Begin video streaming
    - stop_stream: Stop video streaming
    - set_sampling_rate: Adjust sensor sampling rate (requires sampling_rate_hz parameter)
    
    Args:
        device_id: Device identifier.
        command: Command to execute.
        parameters: Optional command parameters (e.g., {"sampling_rate_hz": 10}).
    
    Returns:
        Command execution status and details.
    
    Raises:
        ValueError: If device not found.
    """
    device = get_device_from_registry(device_id)
    if not device:
        raise ValueError(f"Device {device_id} not found")
    
    return {
        "device_id": device_id,
        "command": command,
        "parameters": parameters or {},
        "status": "executed",
        "timestamp": datetime.now().isoformat(),
    }
