# HW1-1 Client Side IoT — AIoT System

## 系統架構

```
[DHT11] → ESP32 → WiFi → Flask Server → SQLite(aiotdb.db)
                                              ↓
                                    Streamlit Dashboard
```

兩條資料管道並行運作：
- **真實管道**：ESP32 + DHT11 → WiFi → POST /sensor
- **模擬管道**：esp32_sim.py → POST /sensor（每 5 秒）

## 專案檔案

```
AIOT/
├── WIFI_DHT11.ino    # ESP32 韌體（POST JSON 升級版）
├── server.py         # 原始 Flask server（HW1-1 初版，GET）
├── app.py            # 升級版 Flask server（POST JSON + /health + /data）
├── esp32_sim.py      # Python 模擬器（假 ESP32）
├── dashboard.py      # Streamlit 視覺化 Dashboard
├── requirements.txt  # Python 套件需求
├── aiotdb.db         # SQLite 資料庫（自動建立）
├── README.md
└── development_log.md
```

## 快速啟動

### 1. 建立虛擬環境並安裝套件
```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 2. 啟動 Flask Server
```bash
python app.py
# 執行於 http://0.0.0.0:5000
```

### 3. 啟動模擬器（另開終端機）
```bash
python esp32_sim.py
```

### 4. 啟動 Dashboard（另開終端機）
```bash
streamlit run dashboard.py
# 開啟 http://localhost:8501
```

## API 端點

| Method | Endpoint  | 說明                     |
|--------|-----------|--------------------------|
| POST   | /sensor   | 接收 JSON 感測資料        |
| GET    | /health   | 健康檢查 → "OK"           |
| GET    | /data     | 回傳最新 50 筆 JSON       |

## ESP32 設定

修改 `WIFI_DHT11.ino` 中的伺服器 IP：
```cpp
String serverName = "http://<YOUR_LOCAL_IP>:5000/sensor";
```

POST JSON 格式：
```json
{
  "temperature": 28.5,
  "humidity": 65.0,
  "device_id": "esp32_real",
  "source": "real"
}
```

ESP32 需安裝額外函式庫：`ArduinoJson`（透過 Arduino Library Manager 安裝）

## 重新執行指令

```bash
# Terminal 1 — Flask server
python app.py

# Terminal 2 — 模擬器
python esp32_sim.py

# Terminal 3 — Dashboard
streamlit run dashboard.py
```

## 版本說明

| 檔案 | 版本 | 說明 |
|------|------|------|
| server.py | HW1-1 原始版 | GET + query params，`dht11_data` 表 |
| app.py | 升級版 | POST JSON，`sensors` 表，含 device_id/source |
| WIFI_DHT11.ino | 升級版 | POST JSON，含 ArduinoJson |
