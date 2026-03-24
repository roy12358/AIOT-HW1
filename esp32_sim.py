"""
esp32_sim.py — Simulated ESP32 DHT11 sensor
Sends fake temperature/humidity data to the Flask server every 5 seconds.
"""

import time
import random
import requests

SERVER_URL = "http://127.0.0.1:5000/sensor"
DEVICE_ID  = "sim_esp32"
INTERVAL   = 5  # seconds


def send_reading():
    temperature = round(random.uniform(20.0, 35.0), 2)
    humidity    = round(random.uniform(40.0, 80.0), 2)

    payload = {
        "temperature": temperature,
        "humidity":    humidity,
        "device_id":   DEVICE_ID,
        "source":      "simulated",
    }

    try:
        resp = requests.post(SERVER_URL, json=payload, timeout=5)
        print(f"[SIM] Temp={temperature:.2f}  Humi={humidity:.2f}  HTTP={resp.status_code}")
    except requests.exceptions.ConnectionError:
        print("[SIM] ERROR: Cannot connect to Flask server. Is app.py running?")
    except Exception as exc:
        print(f"[SIM] ERROR: {exc}")


if __name__ == "__main__":
    print(f"[SIM] Simulator started. Sending to {SERVER_URL} every {INTERVAL}s")
    print("[SIM] Press Ctrl+C to stop.\n")
    while True:
        send_reading()
        time.sleep(INTERVAL)
