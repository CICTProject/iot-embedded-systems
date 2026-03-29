#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <AutoConnect.h>
#include "ESP32WebCam.h"

const char  CAMERA_VIEWER[] = R"*(
{
  "title": "Camera",
  "uri": "/",
  "menu": false,
  "element": [
    {
      "name": "viewport",
      "type": "ACText",
      "format": "<img src='http://%s'>",
      "posterior": "none"
    },
    {
      "name": "discon",
      "type": "ACElement",
      "value": "<script>window.addEventListener('pagehide',function(){window.stop();});</script>"
    }
  ]
}
)*";

// Declare ESP32-CAM handling interface. It contains ESP-IDF Web Server.
ESP32WebCam webcam(ESP32Cam::CAMERA_MODEL_AI_THINKER);

// AutoConnect portal. It contains the WebServer from ESP32 Arduino Core.
AutoConnect portal;
AutoConnectConfig config;

// AutoConnectAux page handler, it starts streaming by adding the ESP32WebCam
// streaming endpoint to the src attribute of the img tag on the AutoConnectAux page.
String viewer(AutoConnectAux& aux, PageArgument &args) {
  AutoConnectAux& viewer = *portal.aux("/");
  // Set the Streaming server host, port, and endpoint
  viewer["viewport"].value = WiFi.localIP().toString() + ":" + String(webcam.getServerPort())
                           + String(webcam.getStreamPath());
  return String();
}

void setup() {
  delay(1000);
  Serial.begin(115200);
  Serial.println();

  // Start Image sensor
  if (webcam.sensorInit() != ESP_OK) {
    Serial.println("Camera initialize failed");
  }

  // Allow automatic re-connection as long as the WiFi connection is established.
  config.autoReconnect = true;
  config.reconnectInterval = 1;
  portal.config(config);

  // Start the portal, it will launch the WebServer for the portal from inside of AutoConnect.
  if (portal.begin()) {
    portal.load(CAMERA_VIEWER);
    portal.on("/", viewer);
    // Start ESP32 Camera Web Server
    if (webcam.startCameraServer() == ESP_OK) {
      Serial.printf("ESP32WebCam server %s port %u ready\n", WiFi.localIP().toString().c_str(),
        webcam.getServerPort());
    }
    else {
      Serial.println("ESP32WebCam server start failed");
    }
  }
}

void loop() {
  portal.handleClient();
}