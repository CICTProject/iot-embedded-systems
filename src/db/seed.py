"""
Database seeding for medical sensor deployment.
Generates and writes device registry and sensor data to InfluxDB.
"""

import logging
import math
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List

from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.client.write.point import Point

from src.db.models import (
    AlarmPriority,
    DeviceType,
    MedicalDevice,
    SensorKind,
)
from src.db.database import get_db_client




logger = logging.getLogger(__name__)


# Sensor data stimulation

class MedicalSensorSimulator:
    """Simulates realistic medical sensor readings with physiological patterns."""

    def __init__(self):
        """Initialize the sensor simulator with baseline values, noise parameters, and units."""
        self.base_values = {
            SensorKind.HEART_RATE: 74.0,
            SensorKind.SPO2: 98.0,
            SensorKind.BLOOD_PRESSURE_SYSTOLIC: 118.0,
            SensorKind.BLOOD_PRESSURE_DIASTOLIC: 76.0,
            SensorKind.ECG: 1.0,
            SensorKind.RESPIRATION_RATE: 16.0,
            SensorKind.BODY_TEMPERATURE: 36.8,
            SensorKind.GLUCOSE: 95.0,
            SensorKind.MOTION: 0.2,
            SensorKind.AIR_QUALITY: 12.0,
        }

        self.noise = {
            SensorKind.HEART_RATE: 4.0,
            SensorKind.SPO2: 0.6,
            SensorKind.BLOOD_PRESSURE_SYSTOLIC: 6.0,
            SensorKind.BLOOD_PRESSURE_DIASTOLIC: 4.0,
            SensorKind.ECG: 0.2,
            SensorKind.RESPIRATION_RATE: 1.5,
            SensorKind.BODY_TEMPERATURE: 0.25,
            SensorKind.GLUCOSE: 6.0,
            SensorKind.MOTION: 0.15,
            SensorKind.AIR_QUALITY: 3.0,
        }

        self.units = {
            SensorKind.HEART_RATE: "bpm",
            SensorKind.SPO2: "%",
            SensorKind.BLOOD_PRESSURE_SYSTOLIC: "mmHg",
            SensorKind.BLOOD_PRESSURE_DIASTOLIC: "mmHg",
            SensorKind.ECG: "mV",
            SensorKind.RESPIRATION_RATE: "rpm",
            SensorKind.BODY_TEMPERATURE: "°C",
            SensorKind.GLUCOSE: "mg/dL",
            SensorKind.MOTION: "g",
            SensorKind.AIR_QUALITY: "AQI",
        }

        self.t = 0

    def generate(self, kind: SensorKind) -> float:
        """
        Generate a realistic simulated medical sensor reading.
        
        Args:
            kind: The sensor kind to simulate
            
        Returns:
            Simulated sensor value within physiological bounds
        """
        base = self.base_values[kind]
        noise = self.noise[kind]
        trend = math.sin(self.t / 25.0) * 0.03
        jitter = random.gauss(0, noise * 0.35)
        self.t += 1

        # Simulate occasional anomalies (2.5% spike)
        if random.random() < 0.03:
            jitter *= 2.5

        value = base * (1 + trend) + jitter

        # Apply physiological bounds based on sensor type
        if kind == SensorKind.SPO2:
            value = max(70, min(100, value))
        elif kind == SensorKind.BODY_TEMPERATURE:
            value = max(33.0, min(41.5, value))
        elif kind in (SensorKind.BLOOD_PRESSURE_SYSTOLIC, SensorKind.BLOOD_PRESSURE_DIASTOLIC):
            value = max(30, value)
        elif kind == SensorKind.HEART_RATE:
            value = max(25, min(220, value))
        elif kind == SensorKind.RESPIRATION_RATE:
            value = max(4, min(45, value))
        elif kind == SensorKind.GLUCOSE:
            value = max(40, min(400, value))
        elif kind == SensorKind.MOTION:
            value = max(0, value)
        elif kind == SensorKind.AIR_QUALITY:
            value = max(0, value)

        return round(value, 2)

    def get_unit(self, kind: SensorKind) -> str:
        """Get the measurement unit for a given sensor kind."""
        return self.units[kind]


# Device creation and database seeding

def create_devices() -> Dict[str, MedicalDevice]:
    """Create and initialize all medical devices in the deployment."""
    now = datetime.now()

    def mk_location(zone: str, x: float, y: float, z: float) -> Dict[str, Any]:
        """Helper to create location dictionary."""
        return {"zone": zone, "x": x, "y": y, "z": z}

    devices = [
        MedicalDevice(
            device_id="cam_corridor_01",
            name="Corridor Camera 01",
            device_type=DeviceType.CAMERA.value,
            protocol="http/rest",
            address="sim/cam_corridor_01",
            status="online",
            last_seen=now,
            ip_address="10.20.0.11",
            location=mk_location("corridor", 12.0, 4.2, 2.8),
            services=[
                {"name": "video_stream", "protocol": "RTSP", "resolution": "1080p", "fps": 25},
                {"name": "motion_detection", "protocol": "HTTP/REST"},
            ],
            battery_level=100,
            metadata={"fov_deg": 84, "notes": "corridor north"},
        ),
        MedicalDevice(
            device_id="cam_corridor_02",
            name="Corridor Camera 02",
            device_type=DeviceType.CAMERA.value,
            protocol="http/rest",
            address="sim/cam_corridor_02",
            status="online",
            last_seen=now,
            ip_address="10.20.0.12",
            location=mk_location("corridor", 18.5, 4.0, 2.8),
            services=[
                {"name": "video_stream", "protocol": "RTSP", "resolution": "720p", "fps": 20},
            ],
            battery_level=97,
            metadata={"fov_deg": 72},
        ),
        MedicalDevice(
            device_id="wearable_hr_01",
            name="Wearable HR Patient A",
            device_type=DeviceType.MEDICAL_SENSOR.value,
            protocol="mqtt",
            address="sim/wearable_hr_01",
            status="online",
            last_seen=now,
            ip_address="10.20.1.21",
            location=mk_location("ward_a", 3.0, 2.0, 0.8),
            services=[
                {"name": "heart_rate", "protocol": "MQTT"},
                {"name": "spo2", "protocol": "MQTT"},
            ],
            battery_level=88,
            metadata={"patient_tag": "A", "sensor_kinds": ["heart_rate", "spo2"]},
        ),
        MedicalDevice(
            device_id="bedside_monitor_01",
            name="Bedside Monitor ICU 01",
            device_type=DeviceType.MEDICAL_SENSOR.value,
            protocol="mqtt",
            address="sim/bedside_monitor_01",
            status="online",
            last_seen=now,
            ip_address="10.20.1.31",
            location=mk_location("icu_room_1", 1.5, 2.3, 1.0),
            services=[
                {"name": "ecg", "protocol": "MQTT"},
                {"name": "heart_rate", "protocol": "MQTT"},
                {"name": "respiration_rate", "protocol": "MQTT"},
                {"name": "body_temperature", "protocol": "MQTT"},
            ],
            battery_level=100,
            metadata={"sensor_kinds": ["ecg", "heart_rate", "respiration_rate", "body_temperature"]},
        ),
        MedicalDevice(
            device_id="bp_station_01",
            name="Blood Pressure Station 01",
            device_type=DeviceType.MEDICAL_SENSOR.value,
            protocol="mqtt",
            address="sim/bp_station_01",
            status="online",
            last_seen=now,
            ip_address="10.20.1.41",
            location=mk_location("triage", 6.5, 1.2, 1.0),
            services=[
                {"name": "blood_pressure_systolic", "protocol": "MQTT"},
                {"name": "blood_pressure_diastolic", "protocol": "MQTT"},
            ],
            battery_level=93,
            metadata={"sensor_kinds": ["blood_pressure_systolic", "blood_pressure_diastolic"]},
        ),
        MedicalDevice(
            device_id="gateway_floor_01",
            name="Gateway Floor 01",
            device_type=DeviceType.GATEWAY.value,
            protocol="mqtt",
            address="sim/gateway_floor_01",
            status="online",
            last_seen=now,
            ip_address="10.20.0.2",
            location=mk_location("network_room", 0.0, 0.0, 0.0),
            services=[
                {"name": "routing", "protocol": "MQTT"},
                {"name": "device_registry", "protocol": "HTTP/REST"},
            ],
            battery_level=100,
            metadata={"uplink": "internet"},
        ),
        MedicalDevice(
            device_id="edge_node_01",
            name="Edge Analytics Node 01",
            device_type=DeviceType.EDGE_NODE.value,
            protocol="http/rest",
            address="sim/edge_node_01",
            status="online",
            last_seen=now,
            ip_address="10.20.0.3",
            location=mk_location("server_room", 1.0, 1.0, 0.0),
            services=[
                {"name": "deployment_monitoring", "protocol": "HTTP/REST"},
                {"name": "alarm_engine", "protocol": "HTTP/REST"},
            ],
            battery_level=100,
            metadata={"cpu": "simulated", "memory": "simulated"},
        ),
    ]

    result = {}
    for d in devices:
        result[d.device_id] = d

    logger.info("Created %d medical deployment devices", len(result))
    return result


# Database seeding initialization

def seed_device_registry(devices: Dict[str, MedicalDevice]) -> None:
    """Write device registry to InfluxDB as metadata."""
    db_client = get_db_client()
    write_api = db_client.get_write_client()

    points = []
    now = datetime.now()

    for device in devices.values():
        point = (
            Point("device_registry")
            .tag("device_id", device.device_id)
            .tag("device_type", device.device_type)
            .tag("protocol", device.protocol)
            .tag("zone", device.location.get("zone", "unknown"))
            .field("name", device.name)
            .field("status", device.status)
            .field("ip_address", device.ip_address)
            .field("battery_level", device.battery_level)
            .field("services_count", len(device.services))
            .time(now)
        )
        points.append(point)

    write_api.write(bucket=db_client.bucket, org=db_client.org, record=points)
    logger.info("Seeded %d devices to InfluxDB for org=%s, bucket=%s", len(points), db_client.org, db_client.bucket)


def seed_historical_data(devices: Dict[str, MedicalDevice]) -> None:
    """Generate and write 72 hours of historical sensor data to InfluxDB."""
    db_client = get_db_client()
    write_api = db_client.get_write_client()

    simulator = MedicalSensorSimulator()
    now = datetime.now()
    points = []
    batch_size = 500

    for device in devices.values():
        if device.device_type != DeviceType.MEDICAL_SENSOR.value:
            continue

        for service in device.services:
            metric = service["name"]
            if metric not in SensorKind._value2member_map_:
                continue

            kind = SensorKind(metric)
            unit = simulator.get_unit(kind)

            for i in range(72):
                ts = now - timedelta(hours=24) + timedelta(minutes=i * 20)
                value = simulator.generate(kind)
                quality = random.randint(94, 100)

                point = (
                    Point("medical_reading")
                    .tag("device_id", device.device_id)
                    .tag("metric", metric)
                    .tag("zone", device.location.get("zone", "unknown"))
                    .field("value", float(value))
                    .field("quality", quality)
                    .field("unit", unit)
                    .time(ts)
                )
                points.append(point)

                # Write in batches to avoid memory overhead
                if len(points) >= batch_size:
                    write_api.write(bucket=db_client.bucket, org=db_client.org, record=points)
                    points = []

    # Write remaining points
    if points:
        write_api.write(bucket=db_client.bucket, org=db_client.org, record=points)

    total_points = 72 * sum(
        len([svc for svc in d.services if svc["name"] in SensorKind._value2member_map_])
        for d in devices.values()
        if d.device_type == DeviceType.MEDICAL_SENSOR.value
    )
    logger.info("Seeded %d historical data points to InfluxDB", total_points)


def initialize_database() -> Dict[str, MedicalDevice]:
    """Initialize the database with device registry and historical data."""
    try:
        logger.info("Initializing medical sensor deployment database...")
        
        # Create devices
        devices = create_devices()
        
        # Seed to InfluxDB
        seed_device_registry(devices)
        seed_historical_data(devices)
        
        logger.info("Database initialization complete")
        return devices
    except Exception as e:
        logger.error("Failed to initialize database: %s", e)
        raise

