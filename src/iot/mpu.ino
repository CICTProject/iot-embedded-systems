#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <ArduinoJson.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>

const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASS";

const int I2C_SDA_PIN = 8;
const int I2C_SCL_PIN = 9;

WebServer server(80); 
Adafruit_MPU6050 mpu;
bool isSensorReady = false;

void handleGetMPU() {
  StaticJsonDocument<512> doc;
  doc["device_id"] = "mpu_sensor_01";

  if (!isSensorReady) {
    doc["status"] = "sensor_error";
    doc["message"] = "MPU6050 initialization failed";
  } else {
    sensors_event_t a, g, temp;
    mpu.getEvent(&a, &g, &temp);

    doc["status"] = "active";
    
    JsonObject accel = doc.createNestedObject("acceleration");
    accel["x"] = a.acceleration.x;
    accel["y"] = a.acceleration.y;
    accel["z"] = a.acceleration.z;
    accel["unit"] = "m/s^2";

    JsonObject rotation = doc.createNestedObject("rotation");
    rotation["x"] = g.gyro.x;
    rotation["y"] = g.gyro.y;
    rotation["z"] = g.gyro.z;
    rotation["unit"] = "rad/s";

    doc["temperature"] = temp.temperature;
    doc["temp_unit"] = "C";
  }

  String jsonResponse;
  serializeJson(doc, jsonResponse); 
  
  server.send(200, "application/json", jsonResponse);
}

void setup() {
  Serial.begin(115200);
  Wire.begin();

  if (mpu.begin()) {
    mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
    mpu.setGyroRange(MPU6050_RANGE_500_DEG);
    mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);
    isSensorReady = true;
  }

  WiFi.begin(ssid, password);
  Serial.println("Connecting to WiFi...");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.print("WiFi Connected! IP: ");
  Serial.println(WiFi.localIP());
  Serial.println("API Endpoint: http://");
  Serial.print(WiFi.localIP());
  Serial.println("/api/mpu");

  server.on("/api/mpu", HTTP_GET, handleGetMPU);
  server.begin();
}

void loop() {
  server.handleClient();
}