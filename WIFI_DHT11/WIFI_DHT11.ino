#include <WiFi.h>
#include <HTTPClient.h>
#include <DHT.h>
#include <ArduinoJson.h>

// ===== WiFi 設定 =====
const char* ssid = "AndroidAP4907";
const char* password = "88888888";

// ===== DHT11 =====
#define DHTPIN 4
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);

// ===== Server URL (POST /sensor) =====
String serverName = "http://10.162.30.142:5000/sensor";

void setup() {
  Serial.begin(115200);
  dht.begin();

  WiFi.begin(ssid, password);
  Serial.print("連線中");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi 連線成功！");
  Serial.println(WiFi.localIP());
}

void loop() {
  if (WiFi.status() == WL_CONNECTED) {

    float temp = dht.readTemperature();
    float humi = dht.readHumidity();

    if (isnan(temp) || isnan(humi)) {
      Serial.println("DHT11 讀取失敗");
      delay(5000);
      return;
    }

    // 組 JSON payload
    StaticJsonDocument<200> doc;
    doc["temperature"] = temp;
    doc["humidity"] = humi;
    doc["device_id"] = "esp32_real";
    doc["source"] = "real";

    String payload;
    serializeJson(doc, payload);

    HTTPClient http;
    http.begin(serverName);
    http.addHeader("Content-Type", "application/json");

    int httpResponseCode = http.POST(payload);

    Serial.print("送出資料: ");
    Serial.print("Temp=");
    Serial.print(temp);
    Serial.print(" Humi=");
    Serial.println(humi);

    Serial.print("HTTP 回應碼: ");
    Serial.println(httpResponseCode);

    if (httpResponseCode > 0) {
      String response = http.getString();
      Serial.println("回應: " + response);
    }

    http.end();

  } else {
    Serial.println("WiFi 未連線");
  }

  delay(5000);
}
