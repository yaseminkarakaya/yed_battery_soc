import streamlit as st, requests, pandas as pd, plotly.express as px, plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

API = "http://127.0.0.1:8000"

st.set_page_config(page_title="BMS SoC Demo", layout="wide")

# ---- Custom CSS ----
st.markdown("""
<style>
/* Genel boşlukları azalt */
.block-container {
    padding-top: 1.35rem;
    padding-bottom: 0.01rem;
    max-width: 90%; /* içerik biraz daha yayvan olsun */
}

/* Başlık ortalı ve biraz daha küçük */
h2 {
    text-align: center;
    margin: 0.3rem 0 0.8rem 0;
    font-size: 1.8rem;
}
h3 {
    text-align: center;
    margin: 0.2rem 0 0.4rem 0;
    font-size: 1.4rem;
}
h4 {
    text-align: center;
    margin: 0.2rem 0;
    font-size: 1.2rem;
}

/* Sekmeleri ortala */
div[data-baseweb="tab-list"] {
    display: flex;
    justify-content: center;
    gap: 1.5rem;             /* sekmeler arası mesafe */
    margin-bottom: 0.2rem;
}

/* Sekme yazı boyutlarını küçült ve dengeli yap */
div[data-baseweb="tab"] button {
    font-size: 1.3rem !important;
    padding: 0.25rem 0.6rem !important;
}

/* Metric kutularını daha kompakt yap */
[data-testid="stMetricValue"] {
    font-size: 2rem !important;
    font-weight: 600 !important;
}
[data-testid="stMetricLabel"] {
    font-size: 0.75rem !important;
    color: #555 !important;
    margin-bottom: -0.2rem !important;
}

/* Tabloyu sıkılaştır */
.dataframe {
    font-size: 0.85rem !important;
}
</style>
""", unsafe_allow_html=True)


# ---- Başlık ----
st.markdown("<h2 style='color:#007bff;'>🔋 BMS SoC Demo</h2>", unsafe_allow_html=True)

# ---- Sekmeler ----
tabs = st.tabs(["📡 Canlı Tahmin", "✍️ Manuel Giriş", "📂 Dosya Yükle"])

# ==================================================
# 📡 CANLI TAHMİN
# ==================================================
with tabs[0]:
    st.markdown("### 📡 Canlı Tahmin (MQTT - B0006)")

    if "live" not in st.session_state: st.session_state["live"] = False
    if "live_data" not in st.session_state: st.session_state["live_data"] = None
    if "live_hist" not in st.session_state: st.session_state["live_hist"] = []

    # Başlat/Durdur butonları ortada ve yan yana
    col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 2])
    with col_btn2:
        b1, b2 = st.columns([1, 1])
        if b1.button("▶ Başlat", use_container_width=True):
            st.session_state["live"] = True
        if b2.button("⏸ Durdur", use_container_width=True):
            st.session_state["live"] = False

    # Autorefresh sadece canlı açıkken
    if st.session_state["live"]:
        st_autorefresh(interval=500, key="live_auto")  # 1 sn'de bir güncelleme
        try:
            res = requests.get(f"{API}/soc/last", params={"device_id": "B0006"}, timeout=5).json()
            hist = requests.get(
                f"{API}/soc/history", params={"device_id": "B0006", "limit": 50}, timeout=5
            ).json().get("items", [])
            if res: st.session_state["live_data"] = res
            if hist: st.session_state["live_hist"] = hist
        except Exception as e:
            st.error(f"API bağlantı hatası: {e}")

    # Son veriler ekranda göster
    if st.session_state["live_data"]:
        res = st.session_state["live_data"]
        soc = res.get("predicted_soc", 0.0)
        v   = res.get("voltage", 0.0)
        i   = res.get("current", 0.0)
        t   = res.get("temperature", 0.0)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("SoC", f"{soc:.1f}%")
        m2.metric("Voltaj", f"{v:.2f}")
        m3.metric("Akım", f"{i:.2f}")
        m4.metric("Sıcaklık", f"{t:.1f}")

        if st.session_state["live_hist"]:
            df = pd.DataFrame(st.session_state["live_hist"])
            if "predicted_soc" in df.columns:
                df = df.rename(columns={"predicted_soc": "Predicted SoC (%)"})
            if "timestamp" in df:
                df["time"] = pd.to_datetime(df["timestamp"], unit="s")

            fig = px.line(df, x="time" if "time" in df else df.index,
                          y="Predicted SoC (%)", height=200)
            st.plotly_chart(fig, use_container_width=True)

            cols = ["Predicted SoC (%)", "voltage", "current", "temperature"]
            if "time" in df.columns: cols = ["time"] + cols
            st.dataframe(df[cols].tail(8), use_container_width=True, height=220)

# ==================================================
# ✍️ MANUEL GİRİŞ
# ==================================================
with tabs[1]:
    st.markdown("### ✍️ Manuel Veri Girişi")
    c1, c2, c3 = st.columns(3)
    v = c1.number_input("Voltaj (V)", value=3.7, step=0.01, format="%.2f")
    i = c2.number_input("Akım (A)", value=-1.5, step=0.01, format="%.2f")
    t = c3.number_input("Sıcaklık (°C)", value=25.0, step=0.1, format="%.1f")

    if "manual_soc" not in st.session_state: st.session_state["manual_soc"] = None
    if st.button("🔮 Tahmin Et"):
        try:
            res = requests.post(f"{API}/predict",
                                json={"Voltage": v, "Current": i, "Temperature": t, "device_id": "manual"}).json()
            st.session_state["manual_soc"] = res.get("predicted_soc", 0)
        except Exception as e:
            st.error(f"Tahmin hatası: {e}")

    if st.session_state["manual_soc"] is not None:
        soc = st.session_state["manual_soc"]
        st.markdown(f"**Tahmin Edilen SoC: {soc:.2f}%**")
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=soc,
            gauge={"axis":{"range":[0,100]},
                   "steps":[{"range":[0,20],"color":"red"},
                            {"range":[20,60],"color":"yellow"},
                            {"range":[60,100],"color":"green"}],
                   "bar":{"color":"darkblue"}}
        ))
        fig.update_layout(height=200, margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig, use_container_width=True)

# ==================================================
# 📂 DOSYA YÜKLE
# ==================================================
with tabs[2]:
    st.subheader("📂 Dosya Yükle")
    f = st.file_uploader("CSV/XLSX", type=["csv", "xlsx", "xls"])
    if "upload_result" not in st.session_state: st.session_state["upload_result"] = None

    if f:
        try:
            res = requests.post(f"{API}/upload",
                                files={"file": (f.name, f.getvalue(), f.type)},
                                timeout=15).json()
            if "error" not in res: st.session_state["upload_result"] = res
            else: st.error(res["error"])
        except Exception as e:
            st.error(f"Dosya yükleme hatası: {e}")

    if st.session_state["upload_result"]:
        df = pd.DataFrame(st.session_state["upload_result"]["items"])
        if not df.empty:
            # SOC ve predicted_soc aynıysa SOC'u kaldır
            if "SOC" in df.columns and "predicted_soc" in df.columns:
                try:
                    if df["SOC"].round(4).equals(df["predicted_soc"].round(4)):
                        df = df.drop(columns=["SOC"])
                except: pass

            # Gereksiz kolonları kaldır
            drop_cols = ["timestamp", "device_id", "ts", "time"]
            df = df.drop(columns=[c for c in drop_cols if c in df.columns], errors="ignore")

            # Kolon isimlerini okunabilir yap
            rename = {"predicted_soc": "Predicted SoC (%)",
                      "voltage": "Voltage (V)",
                      "current": "Current (A)",
                      "temperature": "Temperature (°C)"}
            df = df.rename(columns={c: rename.get(c, c) for c in df.columns})

            st.success(f"Ortalama SoC: {st.session_state['upload_result']['predicted_soc']:.2f}%")
            st.dataframe(df, use_container_width=True, height=400)
