# 🚀 SETUP GUIDE - IoT Environmental Monitoring System

Complete step-by-step guide to get the system running.

---

## 📋 Prerequisites Checklist

Before starting, ensure you have:

- [ ] Docker Desktop installed and running
- [ ] Docker Compose installed (usually comes with Docker Desktop)
- [ ] Python 3.9 or higher
- [ ] pip (Python package manager)
- [ ] At least 4GB free RAM
- [ ] At least 2GB free disk space

### Verify Prerequisites

```bash
# Check Docker
docker --version
# Expected: Docker version 20.x or higher

# Check Docker Compose
docker-compose --version
# Expected: Docker Compose version 1.29 or higher

# Check Python
python --version  # or python3 --version
# Expected: Python 3.9.x or higher

# Check pip
pip --version  # or pip3 --version
```

---

## 🛠️ Installation Steps

### Step 1: Get the Project Files

If you have the project as a ZIP file:
```bash
unzip iot-streaming-system.zip
cd iot-streaming-system
```

If cloning from a repository:
```bash
git clone <repository-url>
cd iot-streaming-system
```

### Step 2: Start Docker Infrastructure

This will start Kafka and PostgreSQL in containers:

```bash
docker-compose up -d
```

**Wait 30-60 seconds** for services to initialize.

Verify containers are running:
```bash
docker-compose ps
```

You should see:
- `kafka` - Status: Up
- `postgres` - Status: Up

### Step 3: Install Python Dependencies

Create a virtual environment (recommended):
```bash
# Create virtual environment
python -m venv venv

# Activate it
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

Install dependencies:
```bash
pip install -r requirements.txt
```

This will install:
- kafka-python (Kafka client)
- psycopg2-binary (PostgreSQL driver)
- pandas, numpy (data processing)
- scikit-learn (machine learning)
- streamlit (dashboard)
- plotly (visualizations)

### Step 4: Verify Installation

Test Kafka connectivity:
```bash
docker exec -it kafka kafka-topics --list --bootstrap-server localhost:9092
```

Test PostgreSQL connectivity:
```bash
docker exec -it postgres psql -U iot_user -d iot_db -c "SELECT version();"
```

If both commands work, you're ready to go! ✅

---

## 🎮 Running the System

You need to run **5 components** in **5 separate terminal windows** (or tabs).

### Terminal 1: Producer 📡

Generates synthetic IoT sensor data.

```bash
# Activate venv if using one
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Run producer
python producer.py
```

**Expected output:**
```
[Producer] ✓ Connected to Kafka successfully!
[Producer] ✓ Created 25 virtual sensors
[Producer] 📡 Starting sensor data stream...
[Producer] 📊 Server_Room_temperature_a1b2c3 | temperature | 25.43 °C | Server Room
```

### Terminal 2: Consumer 💾

Reads from Kafka and stores in PostgreSQL.

```bash
source venv/bin/activate
python consumer.py
```

**Expected output:**
```
[Consumer] ✓ Connected to Kafka successfully!
[Consumer] ✓ Connected to PostgreSQL successfully!
[Consumer] ✓ Table 'sensor_readings' ready with indexes.
[Consumer] ✓ #1 Stored: temperature | 25.43 °C | Server Room
```

### Terminal 3: Stream Processor ⚡

Performs windowed aggregations (Flink-style).

```bash
source venv/bin/activate
python stream_processor.py
```

**Expected output:**
```
[Stream Processor] ✓ Connected to Kafka successfully!
[Stream Processor] ✓ Connected to PostgreSQL successfully!
[Stream Processor] ✓ Aggregates table ready.
[Stream Processor] 🎧 Processing stream with 1-minute tumbling windows...
```

After ~1 minute:
```
[Stream Processor] ⏰ Window completed: 14:23:00
  📊 Server Room | temperature | Avg: 24.56 | Readings: 12 | Anomalies: 0
```

### Terminal 4: ML Detector 🤖

Machine learning anomaly detection.

```bash
source venv/bin/activate
python ml_detector.py
```

**Expected output:**
```
[ML Detector] ✓ Connected to Kafka successfully!
[ML Detector] ✓ Connected to PostgreSQL successfully!
[ML Detector] 🤖 ML anomaly detection active...
[ML Detector] 🔄 Training model for temperature with 50 samples...
```

When anomalies are detected:
```
[ML Detector] 🚨 ANOMALY DETECTED!
  Sensor: Office_Floor_3_humidity_x7y8z9
  Type: humidity
  Value: 95.23 %
  Anomaly Score: -0.2341
```

### Terminal 5: Dashboard 📊

Interactive Streamlit visualization.

```bash
source venv/bin/activate
streamlit run dashboard.py
```

**Expected output:**
```
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.1.x:8501
```

**Open your browser to: http://localhost:8501**

---

## 🎯 Using the Dashboard

The dashboard has **4 tabs**:

### 1. 📊 Real-Time Monitoring
- View live sensor readings
- See KPIs (total readings, anomalies, active sensors)
- Visualize trends over time
- Filter by location and sensor type

### 2. ⏰ Windowed Aggregates
- Stream processing results
- 1-minute window aggregations
- Average, min, max values
- Anomaly counts per window

### 3. 🤖 ML Anomaly Detection
- Machine learning predictions
- Comparison with rule-based detection
- Anomaly score distributions
- Detection agreement metrics

### 4. 📈 Analytics
- Sensor correlation heatmaps
- Statistics by location
- Advanced insights

**Dashboard Controls (left sidebar):**
- Select different views/tabs
- Filter by location
- Filter by sensor type
- Adjust auto-refresh interval (3-30 seconds)
- Change number of records to load

---

## Verification & Testing

### Check Data Flow

1. **Verify data in Kafka:**
```bash
docker exec -it kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic iot_sensors \
  --from-beginning \
  --max-messages 5
```

2. **Check PostgreSQL data:**
```bash
# Connect to database
docker exec -it postgres psql -U iot_user -d iot_db

# Run queries
SELECT COUNT(*) FROM sensor_readings;
SELECT COUNT(*) FROM sensor_aggregates;
SELECT COUNT(*) FROM ml_anomaly_predictions;

# Exit
\q
```

3. **Query specific data:**
```sql
-- Recent readings
SELECT sensor_type, location, value, anomaly 
FROM sensor_readings 
ORDER BY timestamp DESC 
LIMIT 10;

-- Aggregates
SELECT window_start, location, sensor_type, avg_value 
FROM sensor_aggregates 
ORDER BY window_start DESC 
LIMIT 10;

-- ML anomalies
SELECT sensor_type, is_anomaly, anomaly_score 
FROM ml_anomaly_predictions 
WHERE is_anomaly = TRUE 
LIMIT 10;
```

---

## Stopping the System

### Stop Python Components
Press `Ctrl+C` in each terminal running Python scripts.

### Stop Docker Infrastructure
```bash
docker-compose down
```

To also remove volumes (delete all data):
```bash
docker-compose down -v
```

---
