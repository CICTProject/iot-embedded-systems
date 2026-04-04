#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <AutoConnect.h>
#include <ArduinoJson.h>
#include "ESP32WebCam.h"

const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASS";

ESP32WebCam webcam(ESP32Cam::CAMERA_MODEL_AI_THINKER);
AutoConnect portal;
AutoConnectConfig config;

const char CAMERA_VIEWER[] = R"*(
{
  "title": "Camera Viewer", "uri": "/", "menu": false,
  "element": [
    { "name": "viewport", "type": "ACText", "format": "<img src='http://%s'>", "posterior": "none" }
  ]
}
)*";

String viewer(AutoConnectAux& aux, PageArgument &args) {
  AutoConnectAux& viewer = *portal.aux("/");
  viewer["viewport"].value = WiFi.localIP().toString() + ":" + String(webcam.getServerPort()) + String(webcam.getStreamPath());
  return String();
}

void handleGetCameraMetadata() {

  String currentIP = WiFi.localIP().toString();
  int streamPort = webcam.getServerPort();
  String streamPath = webcam.getStreamPath();
  
  String fullStreamUrl = "http://" + currentIP + ":" + String(streamPort) + streamPath;

  StaticJsonDocument<300> doc;
  doc["device_id"] = "camera_01";
  
  if (WiFi.status() == WL_CONNECTED) {
    doc["status"] = "active";
    doc["ip_address"] = currentIP;
    doc["stream_port"] = streamPort;
    doc["stream_path"] = streamPath;
    doc["stream_url"] = fullStreamUrl;
  } else {
    doc["status"] = "network_error";
  }

  String jsonResponse;
  serializeJson(doc, jsonResponse);
  
  portal.host().send(200, "application/json", jsonResponse);
}

void setup() {
  Serial.begin(115200);

  if (webcam.sensorInit() != ESP_OK) {
    Serial.println("Camera Hardware Error!");
  }

  config.apid = ssid;
  config.psk = password;
  config.autoReconnect = true;
  portal.config(config);

  Serial.println("Connecting to WiFi and starting AutoConnect Portal...");

  if (portal.begin()) {

  Serial.println("");
  Serial.print("WiFi Connected! IP: ");
  Serial.println(WiFi.localIP());
  Serial.println("API Endpoint: http://");
  Serial.print(WiFi.localIP());
  Serial.println("/api/camera");

    portal.load(CAMERA_VIEWER);
    portal.on("/", viewer);
    
    portal.host().on("/api/camera", HTTP_GET, handleGetCameraMetadata);
    
    webcam.startCameraServer();
  }
}

void loop() {
  portal.handleClient();
}