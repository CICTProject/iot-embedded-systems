"""
Data models and enumerations for medical sensor deployment.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# Enumerations for device types, sensor kinds, and alarm priorities
class DeviceType(Enum):
    """Enumeration of supported device types in the medical deployment."""
    MEDICAL_SENSOR = "medical_sensor"
    CAMERA = "camera"
    GATEWAY = "gateway"
    EDGE_NODE = "edge_node"
    ACTUATOR = "actuator"


class SensorKind(Enum):
    """Enumeration of supported medical sensor metrics."""
    HEART_RATE = "heart_rate"
    SPO2 = "spo2"
    BLOOD_PRESSURE_SYSTOLIC = "blood_pressure_systolic"
    BLOOD_PRESSURE_DIASTOLIC = "blood_pressure_diastolic"
    ECG = "ecg"
    RESPIRATION_RATE = "respiration_rate"
    BODY_TEMPERATURE = "body_temperature"
    GLUCOSE = "glucose"
    MOTION = "motion"
    AIR_QUALITY = "air_quality"


class AlarmPriority(Enum):
    """Enumeration of alarm priority levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


# Data models
@dataclass
class MedicalReading:
    """Represents a single medical measurement from a sensor."""
    device_id: str
    metric: str
    value: float
    unit: str
    timestamp: datetime
    quality: int


@dataclass
class DeploymentAlarm:
    """Represents an alarm event in the medical deployment."""
    alarm_id: str
    device_id: str
    timestamp: datetime
    priority: AlarmPriority
    message: str
    acknowledged: bool = False


@dataclass
class MedicalDevice:
    """Represents a medical device or sensor in the deployment."""
    device_id: str
    name: str
    device_type: str
    protocol: str
    address: str
    status: str
    last_seen: datetime
    ip_address: str
    location: Dict[str, Any]
    services: List[Dict[str, Any]]
    battery_level: int
    metadata: Optional[Dict[str, Any]] = None
