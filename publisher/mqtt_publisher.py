import os, time, json
import pandas as pd
import paho.mqtt.client as mqtt

# ---- MQTT Ayarları ----
MQTT_HOST = os.getenv("MQTT_HOST", "broker.emqx.io")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
TOPIC = "bms/demo"

# ---- CSV Dosyası (B0006) ----
CSV_PATH = os.getenv("CSV_B0006", "B0006_discharge_clean.csv")
SLEEP_SEC = float(os.getenv("SLEEP_SEC", "1.0"))

# ---- Kolon Normalizasyonu ----
def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    rename = {
        "voltage_measured": "Voltage",
        "current_measured": "Current",
        "temperature_measured": "Temperature"
    }
    df = df.rename(columns=rename)
    if "Voltage" not in df.columns: df["Voltage"] = 3.7
    if "Current" not in df.columns: df["Current"] = 0.0
    if "Temperature" not in df.columns: df["Temperature"] = 25.0
    return df[["Voltage", "Current", "Temperature"]]

# ---- Mesaj Formatı ----
def row_to_msg(row):
    return {
        "device_id": "B0006",
        "Voltage": float(row["Voltage"]),
        "Current": float(row["Current"]),
        "Temperature": float(row["Temperature"]),
        "ts": time.time()
    }

if __name__ == "__main__":
    # MQTT bağlantısı
    cli = mqtt.Client()
    try:
        cli.connect(MQTT_HOST, MQTT_PORT, 60)
        cli.loop_start()
        print(f"[PUB] Connected to {MQTT_HOST}:{MQTT_PORT}, topic={TOPIC}")
    except Exception as e:
        print(f"[ERROR] MQTT bağlantı hatası: {e}")
        exit(1)

    # CSV oku
    try:
        df = pd.read_csv(CSV_PATH)
    except Exception:
        df = pd.read_excel(CSV_PATH)

    df = normalize_df(df).head(200)  # test için ilk 200 satır

    if df.empty:
        print(f"[ERROR] Dosya boş veya yanlış: {CSV_PATH}")
        exit(1)

    print(f"[PUB] {CSV_PATH} yüklendi, {len(df)} satır gönderilecek.")

    try:
        for _, row in df.iterrows():
            msg = row_to_msg(row)
            cli.publish(TOPIC, json.dumps(msg))
            print("[PUB] Sent:", msg)
            time.sleep(SLEEP_SEC)
    except KeyboardInterrupt:
        print("\n[PUB] Stopped by user.")
    finally:
        cli.loop_stop()
        cli.disconnect()
        print("[PUB] Disconnected.")
