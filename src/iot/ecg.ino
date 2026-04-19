#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <ArduinoJson.h>

const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASS";

WebServer server(80); 

const int LO_PLUS_PIN = 2;
const int LO_MINUS_PIN = 3;
const int ECG_ANALOG_PIN = 36;

void handleGetECG() {

  int leadsOffPlus = digitalRead(LO_PLUS_PIN);
  int leadsOffMinus = digitalRead(LO_MINUS_PIN);
  
  int ecgValue = analogRead(ECG_ANALOG_PIN);


  StaticJsonDocument<256> doc;
  doc["device_id"] = "ecg_sensor_01";
  
  if (leadsOffPlus == 1 || leadsOffMinus == 1) {
  
    doc["status"] = "leads_off";
    doc["ecg_raw"] = 0;
    doc["message"] = "Patient electrodes are disconnected";
  } else {

    doc["status"] = "active";
    doc["ecg_raw"] = ecgValue;
    doc["unit"] = "mV_raw";
  }

  String jsonResponse;
  serializeJson(doc, jsonResponse);

  server.send(200, "application/json", jsonResponse);
}

void setup() {
  Serial.begin(115200);
  pinMode(LO_PLUS_PIN, INPUT);
  pinMode(LO_MINUS_PIN, INPUT);

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
  Serial.println("/api/ecg");

  server.on("/api/ecg", HTTP_GET, handleGetECG);
  server.begin();
}

void loop() {
  server.handleClient();
}