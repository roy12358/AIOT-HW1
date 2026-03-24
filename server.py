from flask import Flask, request
import sqlite3
import time

app = Flask(__name__)

# 初始化資料庫
def init_db():
    conn = sqlite3.connect("aiotdb.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dht11_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        temperature REAL,
        humidity REAL,
        timestamp INTEGER
    )
    """)
    conn.commit()
    conn.close()

# 接收 ESP32 資料
@app.route("/data")
def receive_data():
    temp = request.args.get("temp")
    humi = request.args.get("humi")

    conn = sqlite3.connect("aiotdb.db")
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO dht11_data (temperature, humidity, timestamp)
    VALUES (?, ?, ?)
    """, (temp, humi, int(time.time())))

    conn.commit()
    conn.close()

    print(f"收到資料: Temp={temp}, Humi={humi}")

    return "OK"

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)