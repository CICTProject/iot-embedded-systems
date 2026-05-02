# System-related tools for device registry and monitoring.
from typing import Any, Dict, List, Optional
from src.db.database import get_db_client
from datetime import datetime
from influxdb_client.client.write.point import Point

import logging

logger = logging.getLogger(__name__)

def write_sensor_data(
    device_id: str,
    metric: str,
    value: float,
    unit: str = "",
    quality: int = 100,
    tags: Optional[Dict[str, str]] = None,
    timestamp: Optional[datetime] = None,
) -> bool:
    """
    Write a single sensor measurement to InfluxDB.
    
    Args:
        device_id: Unique device identifier
        metric: Metric/sensor kind name (e.g., 'heart_rate', 'ecg', 'camera_frame')
        value: Numeric measurement value
        unit: Unit of measurement (e.g., 'bpm', 'mV', 'frame')
        quality: Data quality score (0-100, default: 100)
        tags: Additional tags for filtering and organizing data
        timestamp: Timestamp for the measurement (default: current time)
        
    Returns:
        True if write successful, False otherwise
    """
    try:
        db_client = get_db_client()
        write_api = db_client.get_write_client()
        
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        # Build the data point
        point = (
            Point("medical_reading")
            .tag("device_id", device_id)
            .tag("metric", metric)
            .field("value", float(value))
            .field("quality", int(quality))
            .field("unit", unit)
        )
        
        # Add optional tags
        if tags:
            for key, val in tags.items():
                point.tag(key, str(val))
        
        # Set timestamp
        point.time(timestamp)
        
        # Write to InfluxDB
        write_api.write(bucket=db_client.bucket, org=db_client.org, record=point)
        
        logger.info(
            "Successfully wrote sensor data - device_id=%s, metric=%s, value=%s, timestamp=%s",
            device_id, metric, value, timestamp
        )
        return True
        
    except Exception as e:
        logger.error("Error writing sensor data: %s", e)
        return False

def write_ecg_data(
    device_id: str,
    metric: str,
    value: float,
    unit: str = "mV",
    status: str = "unknown",
    timestamp: Optional[datetime] = None,
) -> bool:
    """
    Write ECG data to database.
    
    Args:
        device_id: ECG device identifier
        metric: Metric name (e.g., 'ecg_raw')
        value: Numeric measurement value
        unit: Unit of measurement (default: 'mV' for ECG, 'bpm' for heart rate)
        status: Status of the ECG reading (e.g., 'normal', 'arrhythmia', 'artifact')
        timestamp: Timestamp for the measurement (default: current time)
    Returns:
        True if write successful, False otherwise
    """
    try:
        db_client = get_db_client()
        write_api = db_client.get_write_client()
        
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        # Write ECG data point
        
        ecg_point = (
            Point("medical_reading")
            .tag("device_id", device_id)
            .field("metric", metric)
            .field("value", float(value))
            .field("status", status)
            .field("unit", unit)
            .time(timestamp)
        )
        
        write_api.write(bucket=db_client.bucket, org=db_client.org, record=ecg_point)
        
        logger.info(
            "Successfully wrote ECG data - device_id=%s, metric=%s, value=%s, timestamp=%s",
            device_id, metric, value, timestamp
        )
        return True
        
    except Exception as e:
        logger.error("Error writing ECG data: %s", e)
        return False

def write_camera_data(
    device_id: str,
    status: str,
    flash_status: str,
    sd_card_status: str,

    sd_used: Optional[int] = None,
    sd_total: Optional[int] = None,

    framesize: str = "UNKNOWN",
    quality: int = 0,
    brightness: int = 0,
    contrast: int = 0,
    vflip: bool = False,
    hmirror: bool = False,

    timestamp: Optional[datetime] = None,
) -> bool:
    """
    Write camera metadata and status to InfluxDB.
    
    Args:
        device_id: Camera device identifier
        status: Overall camera status (e.g., 'active', 'disabled')
        flash_status: Flash status ('on' or 'off')
        sd_card_status: SD card status ('mounted', 'not_found')

        sd_used: SD card bytes used (optional)
        sd_total: SD card total bytes (optional)


        framesize: Frame size setting (e.g., 'VGA', 'QVGA', 'UXGA')
        quality: Quality setting (0-63, lower = better)
        brightness: Brightness level (-2 to 2)
        contrast: Contrast level (-2 to 2)
        vflip: Vertical flip status (True/False)
        hmirror: Horizontal mirror status (True/False)

        timestamp: Timestamp for the measurement
        
    Returns:
        True if write successful, False otherwise
    """
    try:
        db_client = get_db_client()
        write_api = db_client.get_write_client()
        
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        tags = {"zone": zone} if zone else {}
        
        # Write camera configuration point
        point = (
            Point("camera_status")
            .tag("device_id", device_id)
            .tag("status", status)
            .tag("flash", flash_status)
            .tag("sd_card", sd_card_status)
            .tag(**tags)

            .field("framesize", framesize)
            .field("quality", int(quality))
            .field("brightness", int(brightness))
            .field("contrast", int(contrast))
            .field("vflip", bool(vflip))
            .field("hmirror", bool(hmirror))

            .time(timestamp)
        )
        
        # Add optional SD card metrics
        if sd_used is not None:
            point.field("sd_used_bytes", int(sd_used))
        if sd_total is not None:
            point.field("sd_total_bytes", int(sd_total))
            if sd_used is not None:
                sd_percent = (sd_used / sd_total * 100) if sd_total > 0 else 0
                point.field("sd_usage_percent", float(sd_percent))
        
        write_api.write(bucket=db_client.bucket, org=db_client.org, record=point)
        
        logger.info(
            "Successfully wrote camera data - device_id=%s, framesize=%s, quality=%s, timestamp=%s",
            device_id, framesize, quality, timestamp
        )
        return True
        
    except Exception as e:
        logger.error("Error writing camera data: %s", e)
        return False
