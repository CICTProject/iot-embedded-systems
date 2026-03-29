"""
Database module for medical sensor deployment.
Provides InfluxDB connection and client utilities.
"""

import logging
import os
from typing import Optional

from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.client.influxdb_client import InfluxDBClient as InfluxClient

logger = logging.getLogger(__name__)


# InfluxDB client wrapper

class InfluxDBClient:
    """Wrapper for InfluxDB client with connection management."""

    def __init__(
        self,
        url: Optional[str] = None,
        token: Optional[str] = None,
        org: Optional[str] = None,
        bucket: Optional[str] = None,
    ):
        """Initialize InfluxDB client connection."""
        self.url = url or os.getenv("INFLUXDB_URL", "http://localhost:8086")
        self.token = token or os.getenv("INFLUXDB_TOKEN", "")
        self.org = org or os.getenv("INFLUXDB_ORG", "medical")
        self.bucket = bucket or os.getenv("INFLUXDB_BUCKET", "medical_sensors")
        self.client = None
        self._connect()

    def _connect(self) -> None:
        """Establish InfluxDB connection."""
        try:
            self.client = InfluxClient(
                url=self.url,
                token=self.token,
                org=self.org,
            )
            logger.info(
                "Connected to InfluxDB at %s (org=%s, bucket=%s)",
                self.url,
                self.org,
                self.bucket,
            )
        except ImportError:
            logger.error(
                "influxdb-client not installed. Install with: pip install influxdb-client"
            )
            raise
        except Exception as e:
            logger.error("Failed to connect to InfluxDB: %s", e)
            raise

    def get_write_client(self):
        """Get write API client."""
        if not self.client:
            self._connect()
        assert self.client is not None
        return self.client.write_api(write_options=SYNCHRONOUS)

    def get_query_client(self):
        """Get query API client."""
        if not self.client:
            self._connect()
        assert self.client is not None
        return self.client.query_api()

    def close(self) -> None:
        """Close InfluxDB connection."""
        if self.client:
            self.client.close()
            self.client = None
            logger.info("Closed InfluxDB connection")


# Global client instance
_db_client: Optional[InfluxDBClient] = None


def get_db_client() -> InfluxDBClient:
    """Get or create global InfluxDB client."""
    global _db_client
    if _db_client is None:
        _db_client = InfluxDBClient()
    return _db_client


def close_db_client() -> None:
    """Close global InfluxDB client."""
    global _db_client
    if _db_client:
        _db_client.close()
        _db_client = None
