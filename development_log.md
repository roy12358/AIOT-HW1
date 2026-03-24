# Development Log — AIoT System (HW1-1 Client Side IoT)

---

## 一、作業目標

建立一個完整的 IoT Client 系統，從感測資料讀取、資料模擬，到透過 WiFi 傳輸並儲存至資料庫，完成端到端資料流程。

---

## 二、系統架構

```
[DHT11] → ESP32 → WiFi → Flask Server → SQLite(aiotdb.db)
                                              ↓
                                    Streamlit Dashboard (擴充)
```

---

## 三、開發歷程

### Step 1 — LED Flash（GPIO 基礎驗證）

最初透過控制 ESP32 的 GPIO 腳位，實現 LED 週期性閃爍，驗證開發板與開發環境正常運作。

```cpp
#define LED_PIN 2
void setup() {
  pinMode(LED_PIN, OUTPUT);
}
void loop() {
  digitalWrite(LED_PIN, HIGH);
  delay(1000);
  digitalWrite(LED_PIN, LOW);
  delay(1000);
}
```

- 使用 `digitalWrite()` 控制高低電位
- 搭配 `delay()` 產生閃爍間隔
- 確認 GPIO 輸出功能正常

---

### Step 2 — DHT11 感測資料讀取

接上 DHT11 感測器（GPIO pin 4），透過 Serial Monitor 即時顯示溫濕度。

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

**Serial Monitor 實測結果（節錄）：**

```
濕度: 95.00 %  溫度: 33.50 °C
濕度: 79.00 %  溫度: 33.70 °C
濕度: 61.00 %  溫度: 33.60 °C
濕度: 53.00 %  溫度: 33.40 °C
濕度: 34.00 %  溫度: 33.20 °C
```

- 加入 `isnan()` 判斷，避免讀取失敗時送出 NaN 值
- 數值隨時間變化，感測器運作正常

---

### Step 3 — SQLite 隨機資料模擬

使用 Python 建立 SQLite 資料庫 `aiotdb.db`，以亂數產生溫濕度資料，驗證資料庫寫入流程。

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

| id | temperature | humidity | timestamp  |
|----|-------------|----------|------------|
| 1  | 31.50       | 42.34    | 1774278654 |
| 2  | 30.46       | 49.41    | 1774278654 |
| 5  | 21.13       | 47.07    | 1774278654 |
| 12 | 20.52       | 77.94    | 1774278654 |

- 共寫入 20 筆亂數資料
- 資料庫建立與寫入均正常

---

### Step 4 — WiFi 傳輸與 Flask Server 串接（原始版本 server.py）

將 ESP32 的 DHT11 讀值透過 WiFi 以 HTTP GET 傳送至電腦端 Flask Server，寫入 SQLite。

**原始 ESP32 程式碼（WIFI_DHT11.ino 初版）：**

```cpp
#include <WiFi.h>
#include <HTTPClient.h>
#include <DHT.h>

const char* ssid = "AndroidAP4907";
const char* password = "88888888";
#define DHTPIN 4
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);

String serverName = "http://10.162.30.142:5000/data";

void setup() {
  Serial.begin(115200);
  dht.begin();
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) delay(500);
}
void loop() {
  float t = dht.readTemperature();
  float h = dht.readHumidity();
  if (!isnan(t) && !isnan(h)) {
    HTTPClient http;
    http.begin(serverName + "?temp=" + String(t) + "&humi=" + String(h));
    http.GET();
    http.end();
  }
  delay(5000);
}
```

**原始 Flask Server（server.py 初版）：**

```python
from flask import Flask, request
import sqlite3, time
app = Flask(__name__)

@app.route("/data")
def receive():
    temp = request.args.get("temp")
    humi = request.args.get("humi")
    conn = sqlite3.connect("aiotdb.db")
    cur = conn.cursor()
    cur.execute("INSERT INTO dht11_data (temperature, humidity, timestamp) VALUES (?, ?, ?)",
                (temp, humi, int(time.time())))
    conn.commit()
    conn.close()
    return "OK"

app.run(host="0.0.0.0", port=5000)
```

**實測結果：**

```
連線中.....
WiFi 連線成功！
10.162.30.52
送出資料: Temp=28.90 Humi=52.00   HTTP 回應碼: 200
送出資料: Temp=28.10 Humi=60.00   HTTP 回應碼: 200
送出資料: Temp=28.40 Humi=61.00   HTTP 回應碼: 200
送出資料: Temp=28.50 Humi=83.00   HTTP 回應碼: 200
```

**SQLite 寫入結果（節錄）：**

| id | temperature | humidity | timestamp  |
|----|-------------|----------|------------|
| 21 | 28.9        | 52       | 1774279841 |
| 22 | 28.1        | 60       | 1774279846 |
| 23 | 28.4        | 61       | 1774279852 |
| 24 | 28.5        | 83       | 1774279857 |

---

## 四、系統升級（擴充版 — app.py）

在 HW1-1 基礎上進行以下升級：

| 項目 | 原始版本 (server.py) | 升級版本 (app.py) |
|------|---------------------|------------------|
| HTTP 方法 | GET + query params | POST + JSON body |
| 資料表 | `dht11_data` (3 欄) | `sensors` (5 欄 + device_id, source) |
| 端點 | `/data` only | `/sensor`, `/health`, `/data` |
| 錯誤處理 | 無 | missing field 回傳 400 |
| 回應格式 | 純文字 "OK" | JSON `{"status": "ok"}` |
| 模擬器 | 無 | `esp32_sim.py` (每 5 秒送資料) |
| Dashboard | 無 | `dashboard.py` (Streamlit) |

### 升級細節

**ESP32 (WIFI_DHT11.ino) — GET → POST JSON**
- 加入 `ArduinoJson` 函式庫
- `Content-Type: application/json` header
- payload 加入 `device_id: "esp32_real"`, `source: "real"`
- 端點改為 `/sensor`

**Flask (app.py) — 新增路由**
- `POST /sensor` → 寫入 `sensors` 資料表
- `GET /health` → 回傳 "OK"（健康檢查）
- `GET /data` → 回傳最新 50 筆 JSON

**模擬器 (esp32_sim.py)**
- 亂數產生 temperature (20~35°C)、humidity (40~80%)
- 每 5 秒 POST 一次至 `/sensor`
- `device_id: "sim_esp32"`, `source: "simulated"`

**Dashboard (dashboard.py)**
- Streamlit 直讀 SQLite `aiotdb.db`
- KPI 卡：最新溫度、濕度、總筆數
- 折線圖：溫度/濕度時序圖
- 篩選器：依 source (real / simulated)
- 每 5 秒自動刷新

---

## 五、遇到的問題與解決

| 問題 | 解決方式 |
|------|---------|
| 原 `/data` 為 GET，無法傳 metadata | 新增 `POST /sensor`，接收 JSON |
| `get_json()` 在 body 為空時 crash | 改用 `get_json(silent=True) or {}` |
| 原資料表無 device_id / source 欄位 | 設計新 `sensors` 資料表 |
| Dashboard 無資料時顯示 KeyError | 加入 `if not df.empty:` 保護 |
| Streamlit 自動刷新造成 empty df 錯誤 | warning 放在 df 為空的 else 分支 |

---

## 六、實驗結果

- ESP32 成功連接 WiFi（SSID: AndroidAP4907）
- DHT11 可穩定讀取溫濕度，HTTP 回應碼 200
- Flask Server 成功接收並寫入 SQLite
- 模擬器每 5 秒產生並送出資料
- Streamlit Dashboard 正常顯示圖表與 KPI

---

## 七、結論

完成從感測器讀取 → WiFi 傳輸 → Flask Server → SQLite → Streamlit Dashboard 的完整 AIoT 端到端架構，並同時支援真實 ESP32 與 Python 模擬兩條資料管道。

## 八、未來改進

- 使用 MQTT 協議取代 HTTP 提升效率
- 串接雲端資料庫（AWS / Firebase）
- 加入異常警報機制（溫度超閾值通知）
