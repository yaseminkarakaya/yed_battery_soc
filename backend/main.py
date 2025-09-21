import os, json, threading, time
from collections import defaultdict, deque
from io import BytesIO
from typing import List, Optional

import numpy as np
import pandas as pd
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager
import paho.mqtt.client as mqtt

from model_backend import load_backend

# ---- Config ----
SEQ_LEN = 15
HISTORY_SIZE = 200
MQTT_HOST = os.getenv("MQTT_HOST", "broker.emqx.io")
MQTT_PORT = 1883
MQTT_TOPIC = "bms/demo"

# ---- State ----
model = load_backend()
seq_buffers = defaultdict(lambda: deque(maxlen=SEQ_LEN))
history = defaultdict(lambda: deque(maxlen=HISTORY_SIZE))

# ---- Schemas ----
class BatteryPoint(BaseModel):
    Voltage: float
    Current: float
    Temperature: float

class PredictRequest(BatteryPoint):
    device_id: Optional[str] = "sim"

# ---- Helpers ----
def _predict_and_store(device_id: str, vec: List[float]):
    seq_buffers[device_id].append(vec)
    soc = model.predict_sequence(np.array(seq_buffers[device_id])) if len(seq_buffers[device_id]) >= SEQ_LEN else model.predict_point(vec)
    item = {
        "device_id": device_id,
        "predicted_soc": float(np.clip(soc, 0, 100)),
        "timestamp": time.time(),
        "voltage": vec[0], "current": vec[1], "temperature": vec[2]
    }
    history[device_id].append(item)
    return item

def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    rename = {"voltage_measured": "Voltage", "current_measured": "Current", "temperature_measured": "Temperature"}
    df = df.rename(columns=rename)
    for col in ["Voltage","Current","Temperature"]:
        if col not in df.columns: df[col] = 0.0 if col!="Temperature" else 25.0
    return df

# ---- MQTT ----
def on_connect(client, userdata, flags, rc):
    print("[MQTT] connected:", rc); client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        dev = data.get("device_id","sim")
        V,I,T = float(data["Voltage"]), float(data["Current"]), float(data.get("Temperature",25))
        _predict_and_store(dev,[V,I,T])
    except Exception as e:
        print("[MQTT] error:", e)

def start_mqtt_loop():
    c = mqtt.Client()
    c.on_connect,on_message
    c.on_connect=on_connect; c.on_message=on_message
    while True:
        try:
            c.connect(MQTT_HOST,MQTT_PORT,60); c.loop_forever()
        except Exception as e:
            print("[MQTT] reconnecting:", e); time.sleep(5)

# ---- App ----
@asynccontextmanager
async def lifespan(app: FastAPI):
    threading.Thread(target=start_mqtt_loop,daemon=True).start()
    yield

app = FastAPI(title="BMS SoC API",version="1.0",lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

@app.get("/health") 
def health(): return {"status":"ok"}

@app.get("/soc/last")
def last(device_id: str="sim"): return history[device_id][-1] if history[device_id] else {"device_id":device_id,"predicted_soc":0}

@app.get("/soc/history")
def hist(device_id:str="sim",limit:int=100): return {"items":list(history[device_id])[-limit:]}

@app.post("/predict")
def predict(req: PredictRequest): return _predict_and_store(req.device_id,[req.Voltage,req.Current,req.Temperature])

@app.post("/upload")
async def upload(file:UploadFile=File(...)):
    df = pd.read_csv(BytesIO(await file.read())) if file.filename.endswith(".csv") else pd.read_excel(BytesIO(await file.read()))
    df=_normalize(df)
    preds,items=[],[]
    for _,r in df.head(100).iterrows():
        it=_predict_and_store("file",[r["Voltage"],r["Current"],r["Temperature"]])
        preds.append(it["predicted_soc"]); items.append(it)
    return {"predicted_soc":float(np.mean(preds)) if preds else 0,"items":items}
