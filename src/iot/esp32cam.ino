/**
 * ESP32-CAM Web Server — Production Firmware
 * Board  : AI Thinker ESP32-CAM
 * Target : Arduino framework (PlatformIO)
 */

#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <ArduinoJson.h>
#include <esp_task_wdt.h>
#include "ESP32WebCam.h"
#include "esp_camera.h"
#include "FS.h"
#include "SD_MMC.h"

#define WIFI_SSID           "AZ7"
#define WIFI_PASSWORD       "zzzzzzzz"

#define WIFI_CONNECT_TIMEOUT_MS   15000   
#define WIFI_RECONNECT_INTERVAL_MS 5000   

#define HTTP_PORT           80
#define FLASH_PIN           4

#define SD_MOUNT_POINT      "/sdcard"
#define SD_IMAGE_DIR        "/images"     
#define SD_MAX_FILES        200           

#define WDT_TIMEOUT_SEC     10         
#define LOG_HEAP_INTERVAL_MS 10000       

enum class CamError {
  OK,
  NOT_ACTIVE,
  CAPTURE_FAIL,
  SENSOR_FAIL,
  SD_NOT_MOUNTED,
  SD_FILE_FAIL,
  SD_NOT_FOUND,
  SD_LIMIT_REACHED,
  INVALID_PARAM,
};

const char* camErrorStr(CamError e) {
  switch (e) {
    case CamError::NOT_ACTIVE:       return "camera_disabled";
    case CamError::CAPTURE_FAIL:     return "capture_fail";
    case CamError::SENSOR_FAIL:      return "sensor_fail";
    case CamError::SD_NOT_MOUNTED:   return "sd_not_mounted";
    case CamError::SD_FILE_FAIL:     return "sd_file_write_fail";
    case CamError::SD_NOT_FOUND:     return "file_not_found";
    case CamError::SD_LIMIT_REACHED: return "sd_file_limit_reached";
    case CamError::INVALID_PARAM:    return "invalid_param";
    default:                         return "unknown_error";
  }
}

struct CameraState {
  bool     isActive        = true;
  bool     isFlashOn       = false;
  bool     isSdMounted     = false;
  bool     shouldReboot    = false;
  uint32_t imageSaveCount  = 0;        
};

WebServer    server(HTTP_PORT);
ESP32WebCam  webcam(ESP32Cam::CAMERA_MODEL_AI_THINKER);
CameraState  camState;

static uint32_t lastWifiCheck  = 0;
static uint32_t lastHeapLog    = 0;
static uint32_t bootTime       = 0;

#define _LOG(tag, msg) Serial.printf("[%6lus][%s] %s\n", \
                          (millis() / 1000), tag, String(msg).c_str())

#define LOG_SYS(m)   _LOG("SYS ", m)
#define LOG_WIFI(m)  _LOG("WIFI", m)
#define LOG_CAM(m)   _LOG("CAM ", m)
#define LOG_SD(m)    _LOG("SD  ", m)
#define LOG_API(m)   _LOG("API ", m)
#define LOG_ERR(m)   _LOG("ERR ", m)

void sendJson(int code, const String& body) {
  server.sendHeader("Content-Type", "application/json");
  server.send(code, "application/json", body);
}

void sendOk(const String& dataJson = "{}") {
  sendJson(200, "{\"success\":true,\"data\":" + dataJson + "}");
}

void sendErr(int code, CamError e) {
  sendJson(code, "{\"success\":false,\"error\":\"" + String(camErrorStr(e)) + "\"}");
}

void sendParseErr() {
  sendJson(400, "{\"success\":false,\"error\":\"invalid_json\"}");
}

inline int clamp(int val, int lo, int hi) {
  return val < lo ? lo : (val > hi ? hi : val);
}

bool isSafePath(const String& path) {
  if (path.indexOf("..") >= 0)   return false;
  if (!path.startsWith("/"))     return false;
  return true;
}

void logRequest() {
  LOG_API(server.method() == HTTP_GET ? "GET  " : "POST "
    + server.uri()
    + " | IP=" + server.client().remoteIP().toString()
    + " | Free heap=" + String(ESP.getFreeHeap()));
}

String nextImagePath() {
  camState.imageSaveCount++;
  char buf[64];
  snprintf(buf, sizeof(buf), "%s/img_%06lu_%lu.jpg",
           SD_IMAGE_DIR,
           (unsigned long)camState.imageSaveCount,
           (unsigned long)millis());
  return String(buf);
}

bool applySensorSetting(const JsonDocument& doc) {
  sensor_t* s = esp_camera_sensor_get();
  if (!s) return false;

  if (doc.containsKey("quality"))    s->set_quality(s,    clamp(doc["quality"],    10, 63));
  if (doc.containsKey("brightness")) s->set_brightness(s, clamp(doc["brightness"], -2,  2));
  if (doc.containsKey("contrast"))   s->set_contrast(s,   clamp(doc["contrast"],   -2,  2));
  if (doc.containsKey("saturation")) s->set_saturation(s, clamp(doc["saturation"], -2,  2));
  if (doc.containsKey("sharpness"))  s->set_sharpness(s,  clamp(doc["sharpness"],  -2,  2));
  if (doc.containsKey("hmirror"))    s->set_hmirror(s,    (bool)doc["hmirror"]);
  if (doc.containsKey("vflip"))      s->set_vflip(s,      (bool)doc["vflip"]);
  if (doc.containsKey("awb"))        s->set_whitebal(s,   (bool)doc["awb"]);
  if (doc.containsKey("aec"))        s->set_exposure_ctrl(s, (bool)doc["aec"]);

  return true;
}

// GET /api/camera
void api_metadata() {
  logRequest();

  char buf[512];
  snprintf(buf, sizeof(buf),
    "{"
      "\"device\":\"esp32cam\","
      "\"model\":\"AI-Thinker\","
      "\"status\":\"%s\","
      "\"uptime_sec\":%lu,"
      "\"free_heap\":%lu,"
      "\"sd_mounted\":%s,"
      "\"images_saved\":%lu,"
      "\"endpoints\":{"
        "\"metadata\":\"GET /api/camera\","
        "\"status\":\"GET /api/camera/status\","
        "\"capture\":\"GET /api/camera/capture\","
        "\"control\":\"POST /api/camera/control\","
        "\"sd_save\":\"POST /api/camera/sdcard/save\","
        "\"sd_list\":\"GET /api/camera/sdcard/list\","
        "\"sd_delete\":\"POST /api/camera/sdcard/delete\","
        "\"stream\":\"GET http://{ip}:81/_stream\","
        "\"reboot\":\"POST /api/system/reboot\","
        "\"health\":\"GET /api/system/health\""
      "}"
    "}",
    camState.isActive ? "active" : "disabled",
    (unsigned long)((millis() - bootTime) / 1000),
    (unsigned long)ESP.getFreeHeap(),
    camState.isSdMounted ? "true" : "false",
    (unsigned long)camState.imageSaveCount
  );

  sendOk(String(buf));
}

// GET /api/camera/status
void api_status() {
  logRequest();

  char buf[128];
  snprintf(buf, sizeof(buf),
    "{\"active\":%s,\"flash\":\"%s\",\"free_heap\":%lu}",
    camState.isActive ? "true" : "false",
    camState.isFlashOn ? "on" : "off",
    (unsigned long)ESP.getFreeHeap()
  );

  sendOk(String(buf));
}

// GET /api/camera/capture
void api_capture() {
  logRequest();

  if (!camState.isActive) { sendErr(403, CamError::NOT_ACTIVE); return; }

  camera_fb_t* fb = esp_camera_fb_get();
  if (!fb) {
    LOG_ERR("Capture failed");
    sendErr(500, CamError::CAPTURE_FAIL);
    return;
  }

  LOG_CAM("Capture OK | " + String(fb->len) + " bytes");

  server.sendHeader("Content-Disposition", "inline; filename=\"capture.jpg\"");
  server.send_P(200, "image/jpeg", (const char*)fb->buf, fb->len);

  esp_camera_fb_return(fb);
}

// POST /api/camera/control
void api_control() {
  logRequest();

  if (!server.hasArg("plain")) { sendErr(400, CamError::INVALID_PARAM); return; }

  String body = server.arg("plain");
  LOG_API("Body: " + body);

  StaticJsonDocument<512> doc;
  if (deserializeJson(doc, body)) { sendParseErr(); return; }

  // Bật / tắt camera (không cần sensor)
  if (doc.containsKey("active")) {
    camState.isActive = (bool)doc["active"];
    LOG_CAM("Active: " + String(camState.isActive));
  }

  // Flash
  if (doc.containsKey("flash")) {
    bool on = String((const char*)doc["flash"]) == "on";
    digitalWrite(FLASH_PIN, on ? HIGH : LOW);
    camState.isFlashOn = on;
    LOG_CAM("Flash: " + String(on ? "ON" : "OFF"));
  }

  // Sensor settings
  if (!applySensorSetting(doc)) {
    LOG_ERR("Sensor get failed");
    sendErr(500, CamError::SENSOR_FAIL);
    return;
  }

  char res[128];
  snprintf(res, sizeof(res),
    "{\"active\":%s,\"flash\":\"%s\"}",
    camState.isActive ? "true" : "false",
    camState.isFlashOn ? "on" : "off"
  );
  sendOk(String(res));
}

// POST /api/camera/sdcard/save
void api_sd_save() {
  logRequest();

  if (!camState.isSdMounted)  { sendErr(503, CamError::SD_NOT_MOUNTED); return; }
  if (!camState.isActive)     { sendErr(403, CamError::NOT_ACTIVE);     return; }

  if (camState.imageSaveCount >= SD_MAX_FILES) {
    sendErr(507, CamError::SD_LIMIT_REACHED);
    return;
  }

  camera_fb_t* fb = esp_camera_fb_get();
  if (!fb) { sendErr(500, CamError::CAPTURE_FAIL); return; }

  String path = nextImagePath();
  File file = SD_MMC.open(path, FILE_WRITE);

  if (!file) {
    esp_camera_fb_return(fb);
    LOG_ERR("Cannot open file: " + path);
    sendErr(500, CamError::SD_FILE_FAIL);
    return;
  }

  size_t written = file.write(fb->buf, fb->len);
  file.close();
  esp_camera_fb_return(fb);

  if (written != fb->len) {
    LOG_ERR("Write incomplete: " + String(written) + "/" + String(fb->len));
    sendErr(500, CamError::SD_FILE_FAIL);
    return;
  }

  LOG_SD("Saved " + path + " (" + String(written) + " bytes)");

  char res[256];
  snprintf(res, sizeof(res),
    "{\"path\":\"%s\",\"size\":%zu,\"total_saved\":%lu}",
    path.c_str(), written, (unsigned long)camState.imageSaveCount
  );
  sendOk(String(res));
}

// GET /api/camera/sdcard/list
void api_sd_list() {
  logRequest();

  if (!camState.isSdMounted) { sendErr(503, CamError::SD_NOT_MOUNTED); return; }

  DynamicJsonDocument doc(8192);
  JsonArray arr = doc.createNestedArray("files");

  File root = SD_MMC.open(SD_IMAGE_DIR);
  if (!root || !root.isDirectory()) {
    String out;
    serializeJson(doc, out);
    sendOk(out);
    return;
  }

  File entry = root.openNextFile();
  while (entry) {
    if (!entry.isDirectory()) {
      JsonObject o = arr.createNestedObject();
      o["name"] = String(entry.name());
      o["size"] = entry.size();
    }
    entry = root.openNextFile();
  }

  doc["count"] = arr.size();
  doc["dir"]   = SD_IMAGE_DIR;

  String out;
  serializeJson(doc, out);
  sendOk(out);
}

// POST /api/camera/sdcard/delete
void api_sd_delete() {
  logRequest();

  if (!camState.isSdMounted) { sendErr(503, CamError::SD_NOT_MOUNTED); return; }
  if (!server.hasArg("plain")) { sendErr(400, CamError::INVALID_PARAM); return; }

  StaticJsonDocument<128> doc;
  if (deserializeJson(doc, server.arg("plain"))) { sendParseErr(); return; }

  if (!doc.containsKey("name")) { sendErr(400, CamError::INVALID_PARAM); return; }

  String name = String((const char*)doc["name"]);

  if (!isSafePath(name)) {
    LOG_ERR("Unsafe path rejected: " + name);
    sendErr(400, CamError::INVALID_PARAM);
    return;
  }

  if (!SD_MMC.exists(name)) {
    sendErr(404, CamError::SD_NOT_FOUND);
    return;
  }

  SD_MMC.remove(name);
  LOG_SD("Deleted: " + name);

  sendOk("{\"deleted\":\"" + name + "\"}");
}

// GET /api/system/health
void api_health() {
  logRequest();

  char buf[256];
  snprintf(buf, sizeof(buf),
    "{"
      "\"status\":\"ok\","
      "\"uptime_sec\":%lu,"
      "\"free_heap\":%lu,"
      "\"min_free_heap\":%lu,"
      "\"wifi_rssi\":%d,"
      "\"sd_mounted\":%s"
    "}",
    (unsigned long)((millis() - bootTime) / 1000),
    (unsigned long)ESP.getFreeHeap(),
    (unsigned long)ESP.getMinFreeHeap(),
    WiFi.RSSI(),
    camState.isSdMounted ? "true" : "false"
  );

  sendOk(String(buf));
}

// POST /api/system/reboot
void api_reboot() {
  logRequest();
  LOG_SYS("Reboot requested via API");
  sendOk("{\"message\":\"rebooting\"}");
  camState.shouldReboot = true;
}

// 404
void api_not_found() {
  sendJson(404, "{\"success\":false,\"error\":\"endpoint_not_found\","
                "\"uri\":\"" + server.uri() + "\"}");
}

bool wifiConnect() {
  LOG_WIFI("Connecting to " + String(WIFI_SSID) + "...");
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  uint32_t start = millis();
  while (WiFi.status() != WL_CONNECTED) {
    if (millis() - start > WIFI_CONNECT_TIMEOUT_MS) {
      LOG_ERR("WiFi connect timeout");
      return false;
    }
    delay(250);
    Serial.print(".");
  }
  Serial.println();
  LOG_WIFI("Connected | IP=" + WiFi.localIP().toString()
           + " | RSSI=" + String(WiFi.RSSI()) + " dBm");
  return true;
}

void wifiMaintain() {
  if (millis() - lastWifiCheck < WIFI_RECONNECT_INTERVAL_MS) return;
  lastWifiCheck = millis();

  if (WiFi.status() != WL_CONNECTED) {
    LOG_WIFI("Lost connection, reconnecting...");
    WiFi.disconnect();
    wifiConnect();
  }
}

bool setupSD() {
  if (!SD_MMC.begin(SD_MOUNT_POINT, true)) {
    LOG_ERR("SD mount failed");
    return false;
  }
  LOG_SD("Mounted | Type=" + String(SD_MMC.cardType())
         + " | Size=" + String(SD_MMC.cardSize() / (1024 * 1024)) + " MB");

  // Tạo thư mục images nếu chưa có
  if (!SD_MMC.exists(SD_IMAGE_DIR)) {
    SD_MMC.mkdir(SD_IMAGE_DIR);
    LOG_SD("Created dir " + String(SD_IMAGE_DIR));
  }
  return true;
}

bool setupCamera() {
  if (webcam.sensorInit() != ESP_OK) {
    LOG_ERR("Camera sensor init failed");
    return false;
  }
  LOG_CAM("Sensor init OK");
  return true;
}

void setupRoutes() {
  server.on("/api/camera",                HTTP_GET,  api_metadata);
  server.on("/api/camera/status",         HTTP_GET,  api_status);
  server.on("/api/camera/capture",        HTTP_GET,  api_capture);
  server.on("/api/camera/control",        HTTP_POST, api_control);
  server.on("/api/camera/sdcard/save",    HTTP_POST, api_sd_save);
  server.on("/api/camera/sdcard/list",    HTTP_GET,  api_sd_list);
  server.on("/api/camera/sdcard/delete",  HTTP_POST, api_sd_delete);
  server.on("/api/system/health",         HTTP_GET,  api_health);
  server.on("/api/system/reboot",         HTTP_POST, api_reboot);
  server.onNotFound(api_not_found);
}

void setup() {
  Serial.begin(115200);
  delay(500);

  bootTime = millis();
  LOG_SYS("=== ESP32-CAM BOOT ===");
  LOG_SYS("SDK: " + String(ESP.getSdkVersion()));
  LOG_SYS("Free heap: " + String(ESP.getFreeHeap()));

  const esp_task_wdt_config_t wdt_cfg = {
    .timeout_ms     = WDT_TIMEOUT_SEC * 1000,
    .idle_core_mask = 0,   
    .trigger_panic  = true
  };
  esp_task_wdt_reconfigure(&wdt_cfg);   
  esp_task_wdt_add(NULL);              

  pinMode(FLASH_PIN, OUTPUT);
  digitalWrite(FLASH_PIN, LOW);

  camState.isSdMounted = setupSD();
  bool camOk = setupCamera();

  if (!camOk) {
    LOG_ERR("Camera init failed — running without camera");
    camState.isActive = false;
  }

  if (!wifiConnect()) {
    LOG_ERR("WiFi unavailable at boot — continuing offline");
  }

  setupRoutes();
  server.begin();
  LOG_SYS("HTTP server started on port " + String(HTTP_PORT));

  webcam.startCameraServer(&camState.isActive);
  LOG_CAM("Stream: http://" + WiFi.localIP().toString() + ":81/_stream");

  LOG_SYS("=== READY ===");
}

void loop() {
  esp_task_wdt_reset();   

  server.handleClient();
  wifiMaintain();

  if (millis() - lastHeapLog > LOG_HEAP_INTERVAL_MS) {
    lastHeapLog = millis();
    LOG_SYS("Heap free=" + String(ESP.getFreeHeap())
            + " min=" + String(ESP.getMinFreeHeap())
            + " | WiFi=" + (WiFi.status() == WL_CONNECTED ? WiFi.RSSI() : 0) + " dBm");
  }

  if (camState.shouldReboot) {
    LOG_SYS("Rebooting in 500ms...");
    server.stop();
    delay(500);
    ESP.restart();
  }
}