#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <AutoConnect.h>
#include <ArduinoJson.h>
#include "ESP32WebCam.h"
#include "esp_camera.h"
#include "FS.h"
#include "SD_MMC.h"

// --- NETWORK CONFIG ---
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASS";

ESP32WebCam webcam(ESP32Cam::CAMERA_MODEL_AI_THINKER);
AutoConnect portal;
AutoConnectConfig config;

// --- STATE ---
struct CameraState {
  bool isActive     = true;
  bool isFlashOn    = false;
  bool isSdMounted  = false;
  bool shouldReboot = false;
  uint32_t saveCounter = 0;  
} camState;

const int FLASH_PIN = 4;
const size_t MAX_BODY_SIZE = 512;

// --- UTILS ---
int clamp(int val, int minVal, int maxVal) {
  if (val < minVal) return minVal;
  if (val > maxVal) return maxVal;
  return val;
}

String framesizeToString(framesize_t size) {
  switch (size) {
    case FRAMESIZE_QQVGA: return "QQVGA";
    case FRAMESIZE_QVGA:  return "QVGA";
    case FRAMESIZE_VGA:   return "VGA";
    case FRAMESIZE_SVGA:  return "SVGA";
    case FRAMESIZE_XGA:   return "XGA";
    case FRAMESIZE_SXGA:  return "SXGA";
    case FRAMESIZE_UXGA:  return "UXGA";
    default: return "UNKNOWN";
  }
}

framesize_t stringToFramesize(const String& sStr) {
  String s = sStr;
  s.toUpperCase();
  if (s == "QVGA") return FRAMESIZE_QVGA;
  if (s == "VGA")  return FRAMESIZE_VGA;
  if (s == "SVGA") return FRAMESIZE_SVGA;
  if (s == "XGA")  return FRAMESIZE_XGA;
  if (s == "SXGA") return FRAMESIZE_SXGA;
  if (s == "UXGA") return FRAMESIZE_UXGA;
  return FRAMESIZE_VGA;
}

bool checkSDFreeSpace(size_t requiredBytes) {
  uint64_t free = SD_MMC.totalBytes() - SD_MMC.usedBytes();
  return free > requiredBytes;
}

// GET: /api/camera
void handleGetCameraMetadata() {
  String currentIP = WiFi.localIP().toString();
  int streamPort = webcam.getServerPort();
  String streamBase = "http://" + currentIP + ":" + String(streamPort);
  String apiBase = "http://" + currentIP + "/api/camera";

  StaticJsonDocument<1024> doc;
  doc["device_id"] = "camera_01";
  doc["status"]   = camState.isActive    ? "active"   : "disabled";
  doc["flash"]    = camState.isFlashOn   ? "on"       : "off";
  doc["sd_card"]  = camState.isSdMounted ? "mounted"  : "not_found";

  if (camState.isSdMounted) {
    doc["sd_total"] = SD_MMC.totalBytes();
    doc["sd_used"]  = SD_MMC.usedBytes();
  }

  sensor_t* s = esp_camera_sensor_get();
  if (s != NULL) {
    JsonObject cfg = doc.createNestedObject("current_config");
    cfg["framesize"]  = framesizeToString((framesize_t)s->status.framesize);
    cfg["quality"]    = s->status.quality;
    cfg["brightness"] = s->status.brightness;
    cfg["contrast"]   = s->status.contrast;
    cfg["vflip"]      = s->status.vflip;
    cfg["hmirror"]    = s->status.hmirror;
  }

  JsonObject endpoints = doc.createNestedObject("endpoints");
  endpoints["stream"]  = camState.isActive ? streamBase + "/_stream"  : "disabled";
  endpoints["capture"] = camState.isActive ? streamBase + "/_capture" : "disabled";
  endpoints["control"] = apiBase + "/control (POST)";
  endpoints["reboot"]  = apiBase + "/reboot (POST)";
  endpoints["sd_save"] = apiBase + "/sdcard/save (POST)";
  endpoints["sd_list"] = apiBase + "/sdcard/list (GET)";

  String jsonResponse;
  serializeJson(doc, jsonResponse);
  portal.host().send(200, "application/json", jsonResponse);
}

// POST: /api/camera/control
void handlePostCameraControl() {
  if (!portal.host().hasArg("plain")) {
    portal.host().send(400, "application/json", "{\"error\":\"Missing JSON body\"}");
    return;
  }

  String body = portal.host().arg("plain");
  if (body.length() > MAX_BODY_SIZE) {
    portal.host().send(413, "application/json", "{\"error\":\"Request body too large\"}");
    return;
  }

  StaticJsonDocument<512> doc;
  if (deserializeJson(doc, body)) {
    portal.host().send(400, "application/json", "{\"error\":\"Invalid JSON\"}");
    return;
  }

  sensor_t* s = esp_camera_sensor_get();
  if (s == NULL) {
    portal.host().send(500, "application/json", "{\"error\":\"Sensor not available\"}");
    return;
  }

  if (doc.containsKey("active"))     camState.isActive = doc["active"];

  if (doc.containsKey("flash")) {
    bool on = (doc["flash"].as<String>() == "on");
    digitalWrite(FLASH_PIN, on ? HIGH : LOW);
    camState.isFlashOn = on;
  }

  if (doc.containsKey("framesize"))  s->set_framesize(s,  stringToFramesize(doc["framesize"].as<String>()));
  if (doc.containsKey("quality"))    s->set_quality(s,    clamp(doc["quality"],    10, 63));
  if (doc.containsKey("brightness")) s->set_brightness(s, clamp(doc["brightness"], -2,  2));
  if (doc.containsKey("contrast"))   s->set_contrast(s,   clamp(doc["contrast"],   -2,  2));
  if (doc.containsKey("vflip"))      s->set_vflip(s,      doc["vflip"]   ? 1 : 0);
  if (doc.containsKey("hmirror"))    s->set_hmirror(s,    doc["hmirror"] ? 1 : 0);

  portal.host().send(200, "application/json", "{\"message\":\"Configuration updated\"}");
}

// POST: /api/camera/reboot
void handlePostReboot() {
  portal.host().send(200, "application/json", "{\"message\":\"Rebooting\"}");
  camState.shouldReboot = true;
}

// POST: /api/camera/sdcard/save
void handlePostSDSave() {
  if (!camState.isActive) {
    portal.host().send(403, "application/json", "{\"error\":\"Camera disabled\"}");
    return;
  }
  if (!camState.isSdMounted) {
    portal.host().send(500, "application/json", "{\"error\":\"SD not mounted\"}");
    return;
  }

  camera_fb_t* fb = esp_camera_fb_get();
  if (!fb) {
    portal.host().send(500, "application/json", "{\"error\":\"Capture failed\"}");
    return;
  }

  if (!checkSDFreeSpace(fb->len * 2)) {
    esp_camera_fb_return(fb);
    portal.host().send(500, "application/json", "{\"error\":\"SD full\"}");
    return;
  }

  camState.saveCounter++;
  String path = "/img_" + String(camState.saveCounter) + "_" + String(millis()) + ".jpg";

  File file = SD_MMC.open(path.c_str(), FILE_WRITE);
  if (!file) {
    esp_camera_fb_return(fb);
    portal.host().send(500, "application/json", "{\"error\":\"File open failed\"}");
    return;
  }

  size_t written     = file.write(fb->buf, fb->len);
  size_t expectedLen = fb->len;  
  file.close();
  esp_camera_fb_return(fb);

  if (written != expectedLen) {
    Serial.printf("[SD] Write incomplete: %u / %u bytes\n", written, expectedLen);
    portal.host().send(500, "application/json", "{\"error\":\"Write incomplete\"}");
    return;
  }

  String response = "{\"message\":\"Saved\",\"filename\":\"" + path + "\",\"size\":" + String(written) + "}";
  portal.host().send(200, "application/json", response);
}

// GET: /api/camera/sdcard/list
void handleGetSDList() {
  if (!camState.isSdMounted) {
    portal.host().send(500, "application/json", "{\"error\":\"SD not mounted\"}");
    return;
  }

  JsonDocument doc;
  JsonArray files = doc.createNestedArray("files");

  File root = SD_MMC.open("/");
  if (!root || !root.isDirectory()) {
    if (root) root.close();
    portal.host().send(500, "application/json", "{\"error\":\"Open root failed\"}");
    return;
  }

  const int MAX_FILES = 20;
  int count = 0;
  bool truncated = false;

  File file = root.openNextFile();
  while (file) {
    if (!file.isDirectory()) {
      if (count < MAX_FILES) {
        JsonObject obj = files.createNestedObject();
        obj["name"] = file.name();
        obj["size"] = file.size();
        count++;
      } else {
        truncated = true;
        file.close();
        break;
      }
    }
    file.close();
    file = root.openNextFile();
  }
  root.close();

  doc["count"]     = count;
  doc["truncated"] = truncated;  

  String jsonResponse;
  serializeJson(doc, jsonResponse);
  portal.host().send(200, "application/json", jsonResponse);
}


void setup() {
  Serial.begin(115200);

  pinMode(FLASH_PIN, OUTPUT);
  digitalWrite(FLASH_PIN, LOW);

  if (!SD_MMC.begin("/sdcard", true)) {
    Serial.println("[SD] Mount failed");
  } else {
    camState.isSdMounted = true;
    Serial.println("[SD] Mounted");
  }

  if (webcam.sensorInit() != ESP_OK) {
    Serial.println("[CAM] Init failed");
  }

  config.apid = ssid;
  config.psk = password;
  config.autoReconnect = true;
  config.reconnectInterval = 1;
  portal.config(config);

  Serial.print("Connecting to WiFi");
  if (portal.begin()) {
    while (WiFi.status() != WL_CONNECTED) {
      Serial.print(".");
      delay(500);
    }
    String ip = WiFi.localIP().toString();
    Serial.println();
    Serial.println("WiFi Connected! IP: " + ip);
    Serial.println("API Endpoint: http://" + ip + "/api/camera");

    portal.host().on("/api/camera",             HTTP_GET,  handleGetCameraMetadata);
    portal.host().on("/api/camera/control",     HTTP_POST, handlePostCameraControl);
    portal.host().on("/api/camera/reboot",      HTTP_POST, handlePostReboot);
    portal.host().on("/api/camera/sdcard/save", HTTP_POST, handlePostSDSave);
    portal.host().on("/api/camera/sdcard/list", HTTP_GET,  handleGetSDList);

    if (webcam.startCameraServer() == ESP_OK) {
      Serial.printf("[CAM] Stream ready on port %u\n", webcam.getServerPort());
    }
  }
}

void loop() {
  if (camState.shouldReboot) {
    delay(500);
    ESP.restart();
  }
  portal.handleClient();
}

