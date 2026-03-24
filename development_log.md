# Development Log — HW1-1 Client Side IoT

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

### Step 1 — LED Flash（GPIO 基礎驗證）

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

### Step 2 — DHT11 感測資料讀取

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
濕度: 53.00 %   溫度: 33.40 °C
濕度: 36.00 %   溫度: 33.20 °C
濕度: 34.00 %   溫度: 33.20 °C
```

- 加入 `isnan()` 判斷，防止感測器初始化未完成時送出 NaN
- 數值隨環境變化，確認 DHT11 運作正常

---

### Step 3 — SQLite 隨機資料模擬

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

- 共寫入 20 筆，資料庫建立與寫入均正常

---

### Step 4 — WiFi 傳輸與 Flask Server 串接（原始版 server.py）

將 ESP32 DHT11 讀值透過 WiFi 以 HTTP GET 傳送至電腦端 Flask Server，寫入 SQLite。

**原始 ESP32 程式碼（WIFI_DHT11.ino 初版，HTTP GET）：**

```cpp
String serverName = "http://10.162.30.142:5000/data";
// loop() 中：
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

**Serial Monitor — WiFi 連線 + 資料傳輸：**

```
連線中.....
WiFi 連線成功！
10.162.30.52
送出資料: Temp=28.90  Humi=52.00   HTTP 回應碼: 200
送出資料: Temp=28.10  Humi=60.00   HTTP 回應碼: 200
送出資料: Temp=28.40  Humi=61.00   HTTP 回應碼: 200
送出資料: Temp=28.50  Humi=83.00   HTTP 回應碼: 200
```

**Flask Server Log：**

```
PS C:\Users\User\Code\python> python server.py
 * Serving Flask app 'server'
 * Running on http://127.0.0.1:5000
 * Running on http://10.162.30.142:5000
收到資料: Temp=28.90, Humi=52.00
10.162.30.52 - [23/Mar/2026 23:30:41] "GET /data?temp=28.90&humi=52.00 HTTP/1.1" 200 -
收到資料: Temp=28.10, Humi=60.00
10.162.30.52 - [23/Mar/2026 23:30:46] "GET /data?temp=28.10&humi=60.00 HTTP/1.1" 200 -
```

**SQLite 寫入結果（dht11_data 資料表）：**

```
id  | temperature | humidity | timestamp
 21 |    28.9     |    52    | 1774279841
 22 |    28.1     |    60    | 1774279846
 23 |    28.4     |    61    | 1774279852
 24 |    28.5     |    83    | 1774279857
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
| 模擬器 | 需另外執行 esp32_sim.py | 內建背景執行緒，自動判斷 |
| ESP32 在線偵測 | 無 | `/health` 回傳 ESP32 狀態 |

### 4.2 升級後 ESP32 韌體（POST JSON）

```cpp
#include <ArduinoJson.h>

String serverName = "http://10.162.30.142:5000/sensor";

void loop() {
  StaticJsonDocument<200> doc;
  doc["temperature"] = temp;
  doc["humidity"]    = humi;
  doc["device_id"]   = "esp32_real";
  doc["source"]      = "real";
  String payload;
  serializeJson(doc, payload);

  HTTPClient http;
  http.begin(serverName);
  http.addHeader("Content-Type", "application/json");
  int code = http.POST(payload);  // HTTP 201
  http.end();
}
```

### 4.3 自動模擬背景執行緒

```python
def sim_loop():
    while True:
        if not esp32_online():          # 超過 30 秒無 real 資料
            temp = round(random.uniform(20.0, 35.0), 2)
            humi = round(random.uniform(40.0, 80.0), 2)
            # 寫入 DB，source="simulated"
            print(f"[SIM]  Temp={temp}  Humi={humi}")
        else:
            print("[SIM]  ESP32 online — 模擬暫停")
        time.sleep(5)
```

---

## 五、本地接收 Real Data 實測結果

### Flask Server 啟動 Log

```
 * Serving Flask app 'app'
 * Running on http://127.0.0.1:5000
 * Running on http://10.162.30.142:5000
[real] esp32_real  Temp=28.9  Humi=52.0
[real] esp32_real  Temp=30.6  Humi=49.0
[real] esp32_real  Temp=30.0  Humi=49.0
[real] esp32_real  Temp=30.1  Humi=45.0
[real] esp32_real  Temp=30.2  Humi=44.0
[SIM]  ESP32 online — 模擬暫停
[real] esp32_real  Temp=29.8  Humi=47.0
[SIM]  ESP32 online — 模擬暫停
[real] esp32_real  Temp=29.9  Humi=47.0
```

### /health 端點回應

```json
{"esp32": "online", "status": "ok"}
```

### /data 端點回應（節錄，最新10筆）

```json
[
  {"id":378, "temperature":30.0, "humidity":47.0, "device_id":"esp32_real", "source":"real", "timestamp":1774357172},
  {"id":377, "temperature":30.0, "humidity":43.0, "device_id":"esp32_real", "source":"real", "timestamp":1774357166},
  {"id":376, "temperature":30.0, "humidity":44.0, "device_id":"esp32_real", "source":"real", "timestamp":1774357161},
  {"id":375, "temperature":30.0, "humidity":44.0, "device_id":"esp32_real", "source":"real", "timestamp":1774357155},
  {"id":374, "temperature":29.8, "humidity":45.0, "device_id":"esp32_real", "source":"real", "timestamp":1774357150}
]
```

### SQLite aiotdb.db 統計（實測）

```
總筆數      : 389 筆
Real ESP32  : 270 筆  (來自 esp32_real，燒錄後持續送入)
Simulated   : 119 筆  (ESP32 離線期間自動補入)
首筆時間    : 2026-03-24 19:34:35
末筆時間    : 2026-03-24 21:00:29
溫度 avg    : 29.7°C
溫度 min/max: 25.6°C / 30.9°C
濕度 avg    : 46.0%
```

### Streamlit Dashboard 顯示（ESP32 Online 狀態）

```
┌─────────────────────────────────────────────────────┐
│  AIoT Sensor Dashboard                              │
│  ESP32 DHT11 — Real & Simulated Pipeline            │
├─────────────────────────────────────────────────────┤
│  ✅ ESP32 Online — 顯示真實感測資料                   │
│  目前模式：`real`                                    │
├──────────────────┬──────────────────┬───────────────┤
│ Latest Temp (°C) │ Latest Humi (%)  │ Total Records │
│      30.0        │      47.0        │     270       │
├──────────────────┴──────────────────┴───────────────┤
│  Temperature over Time        Humidity over Time    │
│  30.5 ┤      ╭──╮             80 ┤                  │
│  30.0 ┤──────╯  ╰───────      60 ┤───────╮          │
│  29.5 ┤                       40 ┤       ╰──────    │
│       └──────────────────        └──────────────    │
├─────────────────────────────────────────────────────┤
│  Latest Records                                     │
│  id  │ datetime  │ temp │ humi │ device_id │ source │
│  378 │ 21:00:08  │ 30.0 │ 47.0 │ esp32_real│ real   │
│  377 │ 21:00:03  │ 30.0 │ 43.0 │ esp32_real│ real   │
│  376 │ 20:59:58  │ 30.0 │ 44.0 │ esp32_real│ real   │
│  375 │ 20:59:53  │ 30.0 │ 44.0 │ esp32_real│ real   │
│  374 │ 20:59:47  │ 29.8 │ 45.0 │ esp32_real│ real   │
└─────────────────────────────────────────────────────┘
```

### Streamlit Dashboard 顯示（ESP32 Offline — 自動切換 Simulated）

```
┌─────────────────────────────────────────────────────┐
│  ⚠️ ESP32 Offline — 自動切換至模擬資料               │
│  目前模式：`simulated`                               │
├──────────────────┬──────────────────┬───────────────┤
│ Latest Temp (°C) │ Latest Humi (%)  │ Total Records │
│      27.3        │      58.4        │     119       │
├─────────────────────────────────────────────────────┤
│  (圖表顯示模擬資料，每 5 秒自動更新)                  │
└─────────────────────────────────────────────────────┘
```

---

## 六、遇到的問題與解決

| 問題 | 解決方式 |
|------|---------|
| 原 `/data` 為 GET，無法傳 device metadata | 新增 `POST /sensor`，接收完整 JSON |
| `get_json()` 在 body 為空時 crash | 改用 `get_json(silent=True) or {}` |
| 原資料表無 device_id / source | 重新設計 `sensors` 資料表 |
| 模擬器需手動另開 terminal 執行 | 改為 Flask 內建背景執行緒 `sim_loop()` |
| 切換 mock 模式時沒有資料進來 | sim_loop 移入 app.py，Flask 啟動即自動執行 |
| Streamlit Cloud 無本地 DB | 加入 `CLOUD_MODE` 偵測，自動產生 in-memory demo 資料 |
| ESP32 用 GET，燒錄後改 POST 需新函式庫 | 加入 `ArduinoJson`，透過 Library Manager 安裝 |

---

## 七、GitHub & Streamlit Cloud 部署

### Repository

```
https://github.com/roy12358/AIOT-HW1
```

### 部署架構

```
本地環境                         雲端
─────────────────────            ──────────────────────
ESP32 (real data)                GitHub (roy12358/AIOT-HW1)
    │ POST /sensor                       │
    ▼                                    ▼
Flask app.py                    Streamlit Cloud
    │ SQLite aiotdb.db           dashboard.py (Cloud Demo 模式)
    │                            → in-memory 模擬資料
    ▼
Streamlit dashboard.py (本地)
→ 真實 DB 資料 + 自動切換
```

### .gitignore（不上傳至 GitHub）

```
venv/
__pycache__/
aiotdb.db        ← DB 含個人環境資料，不上傳
AIOT-HW1.pdf     ← 作業 PDF
*.pyc
```

---

## 八、實驗結果總結

| 項目 | 結果 |
|------|------|
| ESP32 WiFi 連線 | 成功（SSID: AndroidAP4907） |
| DHT11 資料讀取 | 正常（30°C / 44~47%） |
| HTTP POST 回應碼 | 201 Created |
| Flask Server 接收 | 270 筆 real 資料成功寫入 |
| SQLite 儲存 | 389 筆（270 real + 119 simulated） |
| ESP32 離線自動切換 | 正常（30秒無資料 → sim 啟動） |
| Streamlit 本地 Dashboard | 正常，圖表每 5 秒刷新 |
| Streamlit Cloud 部署 | 正常，Cloud Demo 模式顯示模擬資料 |

---

## 九、結論

完成從感測器讀取 → WiFi POST → Flask → SQLite → Dashboard 的完整端到端 AIoT 架構。
系統同時支援真實 ESP32 與 Python 模擬兩條資料管道，並具備自動切換機制，
無論硬體在線與否，Dashboard 皆能持續顯示最新資料。

## 十、未來改進

- 使用 MQTT 協議取代 HTTP，降低網路延遲
- 串接雲端資料庫（Firebase / AWS DynamoDB）
- 加入溫濕度異常警報（超閾值 LINE Notify）
- Flask 部署至 Railway / Render，讓 Streamlit Cloud 可串接真實資料
