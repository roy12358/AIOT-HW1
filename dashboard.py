"""
dashboard.py — Streamlit AIoT Dashboard
- 本地模式：從 SQLite aiotdb.db 讀取
- 雲端模式：DB 不存在時自動產生 demo 資料
自動偵測 ESP32 是否在線，無真實資料時切換 simulated。
"""

import os
import sqlite3
import time
import random
import pandas as pd
import streamlit as st

DB_PATH      = "aiotdb.db"
REAL_TIMEOUT = 30
CLOUD_MODE   = not os.path.exists(DB_PATH)


# ── Data helpers ───────────────────────────────────────────────────────────────

def esp32_online() -> bool:
    if CLOUD_MODE:
        return False
    try:
        conn = sqlite3.connect(DB_PATH)
        row  = conn.execute(
            "SELECT MAX(timestamp) FROM sensors WHERE source='real'"
        ).fetchone()
        conn.close()
        last_ts = row[0]
        return last_ts is not None and (time.time() - last_ts) <= REAL_TIMEOUT
    except Exception:
        return False


def load_local(source: str) -> pd.DataFrame:
    try:
        conn = sqlite3.connect(DB_PATH)
        df   = pd.read_sql_query(
            "SELECT * FROM sensors WHERE source=? ORDER BY id DESC LIMIT 200",
            conn, params=(source,)
        )
        conn.close()
        if not df.empty:
            df["datetime"] = pd.to_datetime(df["timestamp"], unit="s")
        return df
    except Exception:
        return pd.DataFrame()


def make_demo_data() -> pd.DataFrame:
    """Generate 40 rows of in-memory simulated data for cloud demo."""
    now  = int(time.time())
    rows = [
        {
            "id":          i + 1,
            "temperature": round(random.uniform(20.0, 35.0), 2),
            "humidity":    round(random.uniform(40.0, 80.0), 2),
            "device_id":   "sim_esp32",
            "source":      "simulated",
            "timestamp":   now - (40 - i) * 5,
        }
        for i in range(40)
    ]
    df = pd.DataFrame(rows)
    df["datetime"] = pd.to_datetime(df["timestamp"], unit="s")
    return df


# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AIoT Dashboard",
    page_icon="🌡️",
    layout="wide",
)

st.title("AIoT Sensor Dashboard")
st.caption("ESP32 DHT11 — Real & Simulated Pipeline")

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("資料來源")

    if CLOUD_MODE:
        st.info("Cloud Demo 模式\n（無本地 DB）")
        active_source = "simulated"
        manual_mode   = False
    else:
        manual_mode = st.checkbox("手動選擇模式", value=False)
        if manual_mode:
            active_source = st.radio("來源", ["real", "simulated"])
        else:
            st.caption("自動偵測 ESP32 狀態")
            active_source = None  # 決定在下方

    st.divider()
    auto_refresh = st.checkbox("Auto-refresh (5 s)", value=True)
    if st.button("Refresh now"):
        st.rerun()

# ── Auto-detect (本地模式) ──────────────────────────────────────────────────────
if not CLOUD_MODE and not manual_mode:
    online        = esp32_online()
    active_source = "real" if online else "simulated"
else:
    online = False

# ── Status banner ───────────────────────────────────────────────────────────────
if CLOUD_MODE:
    st.info("Cloud Demo 模式 — 顯示模擬資料")
elif active_source == "real":
    st.success("ESP32 Online — 顯示真實感測資料")
elif manual_mode:
    st.info(f"手動模式：顯示 `{active_source}` 資料")
else:
    st.warning("ESP32 Offline — 自動切換至模擬資料")

st.caption(f"目前模式：`{active_source}`")

# ── Load data ───────────────────────────────────────────────────────────────────
if CLOUD_MODE:
    df = make_demo_data()
else:
    df = load_local(active_source)

# ── KPI row ─────────────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)

if not df.empty:
    latest = df.iloc[0]
    col1.metric("Latest Temperature (°C)", f"{latest['temperature']:.1f}")
    col2.metric("Latest Humidity (%)",      f"{latest['humidity']:.1f}")
    col3.metric("Total Records",            len(df))
else:
    col1.metric("Latest Temperature (°C)", "—")
    col2.metric("Latest Humidity (%)",      "—")
    col3.metric("Total Records",            0)
    st.info(f"尚無 `{active_source}` 資料。")

st.divider()

# ── Charts ───────────────────────────────────────────────────────────────────────
if not df.empty:
    chart_df = df.sort_values("datetime")

    col_t, col_h = st.columns(2)
    with col_t:
        st.subheader("Temperature over Time (°C)")
        st.line_chart(chart_df.set_index("datetime")[["temperature"]])
    with col_h:
        st.subheader("Humidity over Time (%)")
        st.line_chart(chart_df.set_index("datetime")[["humidity"]])

    st.subheader("Latest Records")
    st.dataframe(
        df[["id", "datetime", "temperature", "humidity", "device_id", "source"]].head(50),
        use_container_width=True,
        hide_index=True,
    )

# ── Auto-refresh ─────────────────────────────────────────────────────────────────
if auto_refresh:
    time.sleep(5)
    st.rerun()
