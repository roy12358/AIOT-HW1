# HW1-1 Client Side IoT — AIoT System

## Live Demo

**Streamlit Dashboard:** https://roy-aiot-hw1.streamlit.app/

> Cloud Demo 模式：自動產生平滑模擬資料（無需本地 ESP32）

---

## 系統架構

```
[DHT11] → ESP32 → WiFi → Flask Server → SQLite(aiotdb.db)
                                              ↓
                                    Streamlit Dashboard
```

兩條資料管道：
- **真實管道**：ESP32 + DHT11 → WiFi → POST /sensor
- **模擬管道**：Flask 內建 sim_loop（ESP32 離線時自動啟動）

## 專案文件

| 檔案 | 說明 |
|------|------|
| `WIFI_DHT11/WIFI_DHT11.ino` | ESP32 韌體（POST JSON 版） |
| `server.py` | 原始 Flask server（HW1-1 初版，GET） |
| `app.py` | 升級版 Flask server + 自動模擬背景執行緒 |
| `esp32_sim.py` | 獨立 Python 模擬器（可單獨執行） |
| `dashboard.py` | Streamlit Dashboard（本地 + 雲端 demo 模式） |
| `requirements.txt` | Python 套件需求 |
| [development_log.md](development_log.md) | 完整開發記錄 + 實測截圖 |

## 截圖

![ESP32 Real Data — Dashboard + Serial Monitor](assets/realdata.png)

## 快速啟動

```bash
# 1. 建立虛擬環境
python -m venv venv
venv\Scripts\activate

# 2. 安裝套件
pip install -r requirements.txt

# 3. 啟動 Flask（含自動模擬）
python app.py

# 4. 啟動 Dashboard
streamlit run dashboard.py
```

## API 端點

| Method | Endpoint | 說明 |
|--------|----------|------|
| POST | /sensor | 接收 JSON 感測資料 |
| GET  | /health  | ESP32 在線狀態 |
| GET  | /data    | 最新 50 筆 JSON |

## ESP32 設定

修改 `WIFI_DHT11/WIFI_DHT11.ino` 中的 server IP：
```cpp
String serverName = "http://<YOUR_LOCAL_IP>:5000/sensor";
```

需安裝 Arduino 函式庫：`ArduinoJson`（Library Manager 搜尋安裝）
