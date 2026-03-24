from flask import Flask, request, jsonify
import sqlite3
import time
import random
import threading

app = Flask(__name__)
DB_PATH      = "aiotdb.db"
REAL_TIMEOUT = 30   # 超過幾秒沒有 real 資料 → ESP32 視為離線


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS sensors (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        temperature REAL,
        humidity    REAL,
        device_id   TEXT,
        source      TEXT,
        timestamp   INTEGER
    )
    """)
    conn.commit()
    conn.close()


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def esp32_online() -> bool:
    """Return True if real ESP32 sent data within REAL_TIMEOUT seconds."""
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT MAX(timestamp) FROM sensors WHERE source='real'"
    ).fetchone()
    conn.close()
    last_ts = row[0]
    if last_ts is None:
        return False
    return (time.time() - last_ts) <= REAL_TIMEOUT


def sim_loop():
    """Background thread: insert simulated data every 5 s when ESP32 is offline."""
    while True:
        if not esp32_online():
            temp = round(random.uniform(20.0, 35.0), 2)
            humi = round(random.uniform(40.0, 80.0), 2)
            conn = sqlite3.connect(DB_PATH)
            conn.execute(
                "INSERT INTO sensors (temperature, humidity, device_id, source, timestamp) VALUES (?, ?, ?, ?, ?)",
                (temp, humi, "sim_esp32", "simulated", int(time.time()))
            )
            conn.commit()
            conn.close()
            print(f"[SIM]  Temp={temp}  Humi={humi}")
        else:
            print("[SIM]  ESP32 online — 模擬暫停")
        time.sleep(5)


# ── POST /sensor ───────────────────────────────────────────────────────────────
@app.route("/sensor", methods=["POST"])
def receive_sensor():
    data = request.get_json(silent=True) or {}

    temperature = data.get("temperature")
    humidity    = data.get("humidity")
    device_id   = data.get("device_id", "unknown")
    source      = data.get("source", "unknown")

    if temperature is None or humidity is None:
        return jsonify({"error": "missing temperature or humidity"}), 400

    try:
        temperature = float(temperature)
        humidity    = float(humidity)
    except (TypeError, ValueError):
        return jsonify({"error": "invalid numeric values"}), 400

    conn = get_db()
    conn.execute(
        "INSERT INTO sensors (temperature, humidity, device_id, source, timestamp) VALUES (?, ?, ?, ?, ?)",
        (temperature, humidity, device_id, source, int(time.time()))
    )
    conn.commit()
    conn.close()

    print(f"[{source}] {device_id}  Temp={temperature:.1f}  Humi={humidity:.1f}")
    return jsonify({"status": "ok"}), 201


# ── GET /health ────────────────────────────────────────────────────────────────
@app.route("/health", methods=["GET"])
def health():
    online = esp32_online()
    return jsonify({"status": "ok", "esp32": "online" if online else "offline"}), 200


# ── GET /data ──────────────────────────────────────────────────────────────────
@app.route("/data", methods=["GET"])
def get_data():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM sensors ORDER BY id DESC LIMIT 50"
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows]), 200


if __name__ == "__main__":
    init_db()
    t = threading.Thread(target=sim_loop, daemon=True)
    t.start()
    app.run(host="0.0.0.0", port=5000, debug=False)
