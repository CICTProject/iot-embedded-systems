### 1. Get API Endpoint
Using the Arduino IDE to compile and upload the code to the ESP, open Serial Monitor with a baud rate of 115200. The screen will display the connection status. If successful, it will show the local IP address and API Endpoint.

**Example:**
```text
Connecting to WiFi......
WiFi Connected! IP: 192.168.1.327
API Endpoint: http://192.168.1.327/api/mpu
```

### 2. Fetch Data from API
Use the `requests` library in Python to call the API:

**Example:**
```python
import requests

response = requests.get("http://192.168.1.327/api/mpu")
data = response.json()
print(data)
```

### 3. Expected Response
The received data will be formatted in standard JSON as follows:

**Example:**

```json
{
  "device_id": "mpu_sensor_01",
  "status": "active",
  "acceleration": {
    "x": 0.12,
    "y": -0.05,
    "z": 9.81,
    "unit": "m/s^2"
  },
  "rotation": {
    "x": 0.01,
    "y": 0.00,
    "z": -0.02,
    "unit": "rad/s"
  },
  "temperature": 28.5,
  "temp_unit": "C"
}
```

### 4. Write Data to InfluxDB
Sample Python code to package the data and save it to InfluxDB:

```python
import os
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

load_dotenv()

INFLUX_URL = os.getenv("INFLUXDB_URL")
INFLUX_TOKEN = os.getenv("INFLUXDB_TOKEN")
INFLUX_ORG = os.getenv("INFLUXDB_ORG")
INFLUX_BUCKET = os.getenv("INFLUXDB_BUCKET")

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)

point = Point("medical_reading") \
    .tag("device_id", "mpu_sensor_01") \
    .field("accel_x", 0.12) \
    .field("accel_y", -0.05) \
    .field("accel_z", 9.81) \
    .field("temperature", 28.5)

write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
```