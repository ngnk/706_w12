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

## 🧪 Verification & Testing

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

## 🐛 Troubleshooting

### Problem: "Connection refused" when running producer/consumer

**Solution:**
1. Check Docker containers are running:
   ```bash
   docker-compose ps
   ```

2. Restart Docker services:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

3. Wait 30 seconds and try again

### Problem: No data appearing in dashboard

**Solution:**
1. Ensure producer is running (check Terminal 1)
2. Ensure consumer is running (check Terminal 2)
3. Check for error messages in any terminal
4. Click "Refresh Now" in dashboard sidebar

### Problem: "ModuleNotFoundError" when running Python scripts

**Solution:**
1. Activate virtual environment:
   ```bash
   source venv/bin/activate  # or venv\Scripts\activate
   ```

2. Reinstall dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Problem: Docker containers won't start

**Solution:**
1. Check if ports are already in use:
   - Port 9092 (Kafka)
   - Port 5432 (PostgreSQL)

2. Stop other applications using these ports

3. Or modify ports in `docker-compose.yml`

### Problem: Dashboard is slow or unresponsive

**Solution:**
1. Reduce "Records to Load" in sidebar (try 200)
2. Increase "Update Interval" to 20-30 seconds
3. Close other browser tabs
4. Check if all 5 components are running

---

## 🛑 Stopping the System

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

## 🔄 Restarting the System

### Quick Restart (keeping data)
```bash
# Start Docker
docker-compose up -d

# Wait 30 seconds

# Run each Python component in separate terminals
python producer.py
python consumer.py
python stream_processor.py
python ml_detector.py
streamlit run dashboard.py
```

### Fresh Start (clean slate)
```bash
# Stop and remove everything
docker-compose down -v

# Start fresh
docker-compose up -d

# Wait 30 seconds

# Run components as usual
```

---

## 📊 Expected Behavior

After running for 5 minutes, you should see:

- **Producer**: ~150-300 messages sent
- **Consumer**: Same number of readings stored
- **Stream Processor**: ~5 windows completed
- **ML Detector**: Models trained, anomalies detected
- **Dashboard**: Live updating with all data

**Anomaly rates:**
- Rule-based: ~5% (configured in producer)
- ML-based: ~5% (configured in detector)

---

## 🎓 Assignment Submission

For your assignment submission, include:

1. **GitHub Repository** with:
   - All source code files
   - README.md
   - SETUP.md (this file)
   - requirements.txt
   - docker-compose.yml
   - .gitignore

2. **Screenshots**:
   - Dashboard showing all 4 tabs
   - Terminal outputs from each component
   - Database query results

3. **Documentation**:
   - Brief explanation of your implementation
   - Challenges faced and solutions
   - Bonus features implemented

---

## 💡 Tips for Success

1. **Start with infrastructure first**: Always run `docker-compose up -d` before Python components

2. **Check logs if issues occur**:
   ```bash
   docker-compose logs kafka
   docker-compose logs postgres
   ```

3. **Monitor resource usage**: This system is resource-intensive. Close other applications if needed.

4. **Use virtual environment**: Keeps dependencies isolated and clean

5. **Keep terminals visible**: Watch for errors in real-time

6. **Be patient**: ML model training takes ~1-2 minutes initially

---

## 🎉 Success Criteria

You know the system is working correctly when:

✅ All 5 terminals show no errors  
✅ Producer is sending messages  
✅ Consumer is storing data  
✅ Stream processor completes windows  
✅ ML detector finds anomalies  
✅ Dashboard displays live data  
✅ Dashboard auto-refreshes  
✅ All 4 dashboard tabs work  
✅ Filters in sidebar work  

---

## 📞 Getting Help

If you encounter issues:

1. Check the Troubleshooting section above
2. Review terminal outputs for specific error messages
3. Verify all prerequisites are installed correctly
4. Try a fresh start with `docker-compose down -v`

---

**Happy Streaming! 🚀**

Your IoT Environmental Monitoring System is now ready to demonstrate advanced data streaming, windowed processing, and machine learning capabilities!
