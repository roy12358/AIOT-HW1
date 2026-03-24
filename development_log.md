# Development Log — HW1 Client Side IoT

---

## 一、作業目標

建立一個完整的 IoT Client 系統，從感測資料讀取、資料模擬，到透過 WiFi 傳輸並儲存至資料庫，完成端到端資料流程，並擴充 Streamlit 視覺化 Dashboard。

---

## 二、系統架構

```
[DHT11 Sensor]
      │ GPIO Pin 4
      ▼
[ESP32 (WIFI_DHT11.ino)]
  - WiFi 連線 (AndroidAP4907)
  - 每 5 秒讀取 DHT11
  - HTTP POST JSON → /sensor
      │
      ▼  POST http://10.162.30.142:5000/sensor
[Flask Server — app.py]
  ├── POST /sensor  → 寫入 SQLite
  ├── GET  /health  → ESP32 在線狀態
  ├── GET  /data    → 最新 50 筆 JSON
  └── 背景執行緒 sim_loop() — ESP32 離線時自動補 simulated 資料
      │
      ▼
[SQLite — aiotdb.db]
  Table: sensors
  id | temperature | humidity | device_id | source | timestamp
      │
      ▼
[Streamlit Dashboard — dashboard.py]
  - 本地模式：讀 SQLite，自動偵測 ESP32 在線/離線
  - Cloud Demo 模式：DB 不存在時產生 in-memory 模擬資料
```

---

## 三、開發歷程

### HW1-1 — LED Flash（GPIO 基礎驗證）

透過控制 ESP32 GPIO 腳位，實現 LED 週期性閃爍，驗證開發板與開發環境正常運作。

```cpp
#define LED_PIN 2
void setup() {
  pinMode(LED_PIN, OUTPUT);
}
void loop() {
  digitalWrite(LED_PIN, HIGH);  delay(1000);
  digitalWrite(LED_PIN, LOW);   delay(1000);
}
```

- `digitalWrite()` 控制高低電位，`delay()` 產生閃爍間隔
- 確認 Arduino IDE 燒錄流程、COM Port 連線正常

---

### HW1-2 — DHT11 感測資料讀取

接上 DHT11 感測器（GPIO Pin 4），透過 Serial Monitor 即時顯示溫濕度。

```cpp
#include <DHT.h>
#define DHTPIN 4
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);

void setup() {
  Serial.begin(115200);
  dht.begin();
}
void loop() {
  float h = dht.readHumidity();
  float t = dht.readTemperature();
  if (isnan(h) || isnan(t)) return;
  Serial.print("Temp: "); Serial.print(t);
  Serial.print(" Humi: "); Serial.println(h);
  delay(2000);
}
```

**Serial Monitor 實測輸出（115200 baud）：**

```
濕度: 95.00 %   溫度: 33.50 °C
濕度: 95.00 %   溫度: 33.60 °C
濕度: 79.00 %   溫度: 33.70 °C
濕度: 61.00 %   溫度: 33.60 °C
濕度: 57.00 %   溫度: 33.40 °C
濕度: 53.00 %   溫度: 33.50 °C
濕度: 34.00 %   溫度: 33.20 °C
```

- 加入 `isnan()` 判斷，防止感測器初始化未完成時送出 NaN
- 數值隨環境變化，確認 DHT11 運作正常

---

### HW1-3 — SQLite 隨機資料模擬

使用 Python 建立 SQLite 資料庫 `aiotdb.db`，以亂數產生溫濕度模擬資料，驗證資料庫寫入流程。

```python
import sqlite3, random, time
conn = sqlite3.connect("aiotdb.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS dht11_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    temperature REAL,
    humidity REAL,
    timestamp INTEGER
)""")
for _ in range(20):
    cursor.execute(
        "INSERT INTO dht11_data (temperature, humidity, timestamp) VALUES (?, ?, ?)",
        (random.uniform(20, 35), random.uniform(40, 80), int(time.time()))
    )
conn.commit()
conn.close()
```

**寫入結果（節錄）：**

```
id | temperature | humidity  | timestamp
 1 |   31.50     |  42.34    | 1774278654
 2 |   30.46     |  49.41    | 1774278654
 5 |   21.13     |  47.07    | 1774278654
12 |   20.52     |  77.94    | 1774278654
```

---

### HW1-4 — WiFi 傳輸與 Flask Server 串接（原始版 server.py）

將 ESP32 DHT11 讀值透過 WiFi 以 HTTP GET 傳送至電腦端 Flask Server，寫入 SQLite。

**原始 ESP32（HTTP GET）：**

```cpp
String serverName = "http://10.162.30.142:5000/data";
http.begin(serverName + "?temp=" + String(t) + "&humi=" + String(h));
http.GET();
```

**原始 Flask Server（server.py）：**

```python
@app.route("/data")
def receive():
    temp = request.args.get("temp")
    humi = request.args.get("humi")
    cur.execute("INSERT INTO dht11_data (temperature, humidity, timestamp) VALUES (?, ?, ?)",
                (temp, humi, int(time.time())))
    return "OK"
```

**Serial Monitor — WiFi 連線 + 傳輸：**

```
連線中.....
WiFi 連線成功！
10.162.30.52
送出資料: Temp=28.90  Humi=52.00   HTTP 回應碼: 200
送出資料: Temp=28.10  Humi=60.00   HTTP 回應碼: 200
送出資料: Temp=28.40  Humi=61.00   HTTP 回應碼: 200
```

**Flask Server Log：**

```
 * Running on http://10.162.30.142:5000
收到資料: Temp=28.90, Humi=52.00
10.162.30.52 - "GET /data?temp=28.90&humi=52.00 HTTP/1.1" 200 -
收到資料: Temp=28.10, Humi=60.00
10.162.30.52 - "GET /data?temp=28.10&humi=60.00 HTTP/1.1" 200 -
```

---

## 四、系統升級（app.py — POST JSON + 自動模擬）

### 4.1 升級對照表

| 項目 | 原始版 (server.py) | 升級版 (app.py) |
|------|-------------------|----------------|
| HTTP 方法 | GET + query params | POST + JSON body |
| 資料表 | `dht11_data` (3欄) | `sensors` (5欄 + device_id, source) |
| 端點 | `/data` only | `/sensor` + `/health` + `/data` |
| 錯誤處理 | 無 | missing field → 400 |
| 模擬器 | 需另外執行 | 內建背景執行緒，自動判斷 |

### 4.2 升級後 ESP32 韌體（POST JSON）

```cpp
#include <ArduinoJson.h>

StaticJsonDocument<200> doc;
doc["temperature"] = temp;
doc["humidity"]    = humi;
doc["device_id"]   = "esp32_real";
doc["source"]      = "real";
String payload;
serializeJson(doc, payload);

HTTPClient http;
http.begin("http://10.162.30.142:5000/sensor");
http.addHeader("Content-Type", "application/json");
int code = http.POST(payload);  // → HTTP 201
```

### 4.3 自動模擬背景執行緒（sim_loop）

ESP32 超過 30 秒未傳資料時，自動每 15 秒補一筆 simulated 資料：

```python
def sim_loop():
    while True:
        if not esp32_online():
            temp = round(random.uniform(20.0, 35.0), 2)
            humi = round(random.uniform(40.0, 80.0), 2)
            # INSERT INTO sensors ... source="simulated"
            print(f"[SIM]  Temp={temp}  Humi={humi}")
        else:
            print("[SIM]  ESP32 online — 模擬暫停")
        time.sleep(15)
```

---

## 五、本地接收 Real Data 實測結果

### Flask Server Log（ESP32 傳入時）

```
 * Running on http://127.0.0.1:5000
 * Running on http://10.162.30.142:5000
[real] esp32_real  Temp=28.9  Humi=52.0
[real] esp32_real  Temp=30.6  Humi=49.0
[real] esp32_real  Temp=30.0  Humi=49.0
[real] esp32_real  Temp=30.1  Humi=45.0
[SIM]  ESP32 online — 模擬暫停
[real] esp32_real  Temp=29.8  Humi=47.0
[SIM]  ESP32 online — 模擬暫停
[real] esp32_real  Temp=29.9  Humi=47.0
```

### Serial Monitor — ESP32 升級版（POST 回應）

```
連線中.....
WiFi 連線成功！
10.162.30.52
送出資料: Temp=29.90  Humi=44.00
HTTP 回應碼: 201
{"status":"ok"}
送出資料: Temp=29.90  Humi=44.00
HTTP 回應碼: 201
```

### /data API 回應（節錄）

```json
[
  {"id":378, "temperature":30.0, "humidity":47.0, "device_id":"esp32_real", "source":"real", "timestamp":1774357172},
  {"id":377, "temperature":30.0, "humidity":43.0, "device_id":"esp32_real", "source":"real", "timestamp":1774357166},
  {"id":376, "temperature":30.0, "humidity":44.0, "device_id":"esp32_real", "source":"real", "timestamp":1774357161}
]
```

### SQLite aiotdb.db 統計

```
總筆數      : 389 筆
Real ESP32  : 270 筆
Simulated   : 119 筆
首筆時間    : 2026-03-24 19:34:35
末筆時間    : 2026-03-24 21:00:29
溫度 avg    : 29.7°C  (min 25.6 / max 30.9)
濕度 avg    : 46.0%
```

### Dashboard 接收真實資料截圖

下圖為 ESP32 燒錄後，Dashboard 自動切換至 **ESP32 Online（綠色）** 狀態，
左側顯示即時溫濕度與折線圖，右側 Serial Monitor 可見 HTTP 201 回應。

![ESP32 Real Data — Dashboard + Serial Monitor](assets/realdata.png)

- **Latest Temperature**：29.9°C
- **Latest Humidity**：44.0%
- **溫度折線圖**：穩定維持在 29~31°C
- **濕度折線圖**：40~65% 區間波動
- **Latest Records 資料表**：source 欄位顯示 `real`，device_id 為 `esp32_real`

---

## 六、遇到的問題與解決

| 問題 | 解決方式 |
|------|---------|
| 原 `/data` 為 GET，無法傳 metadata | 新增 `POST /sensor`，接收完整 JSON |
| `get_json()` 在 body 為空時 crash | 改用 `get_json(silent=True) or {}` |
| 原資料表無 device_id / source | 重新設計 `sensors` 資料表 |
| 模擬器需手動另開 terminal | 改為 Flask 內建背景執行緒 `sim_loop()` |
| 切換 mock 模式時沒有新資料 | sim_loop 移入 app.py，Flask 啟動即自動執行 |
| Streamlit Cloud 無本地 DB | 加入 `CLOUD_MODE` 偵測，session_state random walk 產生平滑 demo 資料 |
| 雲端 demo 每次 rerun 資料大跳 | 改用 random walk（±0.4°C / ±1%），session_state 保存狀態 |
| ESP32 用 GET，改 POST 需新函式庫 | 加入 `ArduinoJson`，透過 Library Manager 安裝 |

---

## 七、GitHub & Streamlit Cloud 部署

**Repository：** https://github.com/roy12358/AIOT-HW1

**Live Demo：** https://roy-aiot-hw1.streamlit.app/

### 本地 vs 雲端行為對照

| 環境 | 資料來源 | ESP32 偵測 |
|------|---------|-----------|
| 本地（有 aiotdb.db）| SQLite 直讀 | 自動切換 real / simulated |
| Streamlit Cloud | in-memory random walk | 無（固定 simulated） |

---

## 八、實驗結果總結

| 項目 | 結果 |
|------|------|
| ESP32 WiFi 連線 | 成功（SSID: AndroidAP4907） |
| DHT11 資料讀取 | 正常（~30°C / ~44%） |
| HTTP POST 回應碼 | 201 Created |
| Flask Server 接收 | 270 筆 real 資料成功寫入 |
| SQLite 儲存 | 389 筆（270 real + 119 simulated） |
| ESP32 離線自動切換 | 正常（30秒無資料 → sim 啟動） |
| Streamlit 本地 | 正常，圖表每 5 秒刷新 |
| Streamlit Cloud | 正常，平滑 random walk demo |

---

## 九、結論

完成從感測器讀取 → WiFi POST → Flask → SQLite → Dashboard 的完整端到端 AIoT 架構。
系統同時支援真實 ESP32 與 Python 模擬兩條資料管道，無論硬體在線與否，Dashboard 皆能持續顯示最新資料。

## 十、未來改進

- 使用 MQTT 協議取代 HTTP，降低網路延遲
- 串接雲端資料庫（Firebase / AWS DynamoDB）
- 加入溫濕度異常警報（超閾值 LINE Notify）
- Flask 部署至 Railway / Render，讓 Streamlit Cloud 串接真實資料
