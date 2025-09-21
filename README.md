🔋 EV Battery SoC Prediction
📌 Proje Özeti

Bu proje, elektrikli araç bataryalarının Şarj Durumu (State of Charge – SoC) tahminini yapmak için geliştirilmiştir.
NASA’nın sağladığı B0005, B0006 ve B0018 batarya veri setleri kullanılarak model eğitilmiş ve farklı bataryalardan gelen verilerle test edilmiştir.

Projedeki Bileşenler

Backend (FastAPI): Eğitilen modeli REST API olarak sunar.

Frontend (Streamlit): Kullanıcıya canlı tahmin, manuel giriş ve dosya yükleme arayüzü sağlar.

Mosquitto (MQTT Broker): Publisher’dan gelen verileri backend’e iletir.

Publisher: CSV dosyasından batarya verilerini MQTT üzerinden yayınlar.

🚀 Docker ile Çalıştırma

Proje kök klasöründe (docker-compose.yml olan yerde):

docker compose up --build

Çalışan servisler

Backend API: http://localhost:8000/docs

Frontend UI: http://localhost:8501

Mosquitto Broker: localhost:1883

Publisher: CSV’den MQTT’ye otomatik veri yollar

🔧 Docker Çalışmazsa Manuel Çalıştırma
Backend (FastAPI)
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000


📌 API adresi: http://localhost:8000/docs

Frontend (Streamlit)
cd frontend
pip install -r requirements.txt
streamlit run app.py


📌 UI adresi: http://localhost:8501

Publisher (Opsiyonel)
cd publisher
pip install -r requirements.txt
python mqtt_publisher.py

🔌 API Endpointleri

GET /health → Servis durumu

POST /predict → Tek ölçümden SoC tahmini

GET /soc/last?device_id=B0006 → Son tahmin

GET /soc/history?device_id=B0006&limit=50 → Geçmiş tahminler

POST /upload → CSV/XLSX dosyası yükleyip toplu tahmin

Örnek istek:

{
  "Voltage": 3.72,
  "Current": -1.5,
  "Temperature": 25.0,
  "device_id": "manual"
}

📊 Frontend Özellikleri

📡 Canlı Tahmin: Publisher’dan gelen verileri gerçek zamanlı grafik ve tablo ile gösterir.

✍️ Manuel Giriş: Voltaj, akım ve sıcaklık girilerek tahmin alınabilir.

📂 Dosya Yükle: CSV/XLSX dosyası yüklenerek toplu tahmin yapılabilir.
