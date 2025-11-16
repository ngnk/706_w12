# ⚡ QUICK REFERENCE - IoT Streaming System

## 🚀 Start Infrastructure
```bash
docker-compose up -d
# Wait 30 seconds
```

## 🎮 Run Components (5 separate terminals)

### Terminal 1: Producer
```bash
python producer.py
```

### Terminal 2: Consumer
```bash
python consumer.py
```

### Terminal 3: Stream Processor
```bash
python stream_processor.py
```

### Terminal 4: ML Detector
```bash
python ml_detector.py
```

### Terminal 5: Dashboard
```bash
streamlit run dashboard.py
```

## 🌐 Access Dashboard
**URL**: http://localhost:8501

## 🛑 Stop Everything
```bash
# Stop Python: Ctrl+C in each terminal
docker-compose down
```

## 🔍 Check Data
```bash
# Kafka messages
docker exec -it kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic iot_sensors --from-beginning --max-messages 5

# PostgreSQL
docker exec -it postgres psql -U iot_user -d iot_db

# Then run:
SELECT COUNT(*) FROM sensor_readings;
SELECT COUNT(*) FROM sensor_aggregates;
SELECT COUNT(*) FROM ml_anomaly_predictions;
```

## 📊 Expected Results (after 5 minutes)
- Producer: ~150-300 messages
- Consumer: Same # in database
- Stream Processor: ~5 windows
- ML Detector: Models trained, anomalies found
- Dashboard: Live updating

## 🎯 Bonus Features

### Bonus #1: Stream Processing ✅
**File**: `stream_processor.py`
- 1-minute tumbling windows
- Real-time aggregations (AVG, MIN, MAX, STDDEV)
- Statistical anomaly detection (Z-scores)

### Bonus #2: ML Anomaly Detection ✅
**File**: `ml_detector.py`
- Isolation Forest algorithm
- 7-dimensional feature engineering
- Online learning (retrains every 5 min)
- Compares with rule-based detection

## 📁 Key Files
- `producer.py` - Data generator
- `consumer.py` - Kafka → DB
- `stream_processor.py` - Windowed agg
- `ml_detector.py` - ML detection
- `dashboard.py` - Visualization
- `docker-compose.yml` - Infrastructure
- `README.md` - Full docs
- `SETUP.md` - Setup guide

## 🐛 Quick Fixes

**No data?**
→ Check producer is running

**Connection error?**
→ `docker-compose restart kafka`

**Dashboard slow?**
→ Reduce records in sidebar

**Fresh start?**
→ `docker-compose down -v`
→ `docker-compose up -d`

## 📞 Help
See detailed guides:
- SETUP.md - Installation
- README.md - Full documentation
- PROJECT_SUMMARY.md - Overview
