"""
Advanced Machine Learning Anomaly Detection System

Features:
- Isolation Forest for unsupervised anomaly detection
- Online learning with periodic model updates
- Multi-sensor correlation analysis
- Sequential pattern detection
- Stores predictions back to database
"""

import json
import time
import pickle
from datetime import datetime, timedelta
from collections import deque
import psycopg2
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from kafka import KafkaConsumer
from typing import Dict, List, Tuple


class OnlineAnomalyDetector:
    """ML-based anomaly detector with online learning capabilities."""
    
    def __init__(self, contamination: float = 0.05, window_size: int = 1000):
        """
        Initialize the anomaly detector.
        
        Args:
            contamination: Expected proportion of anomalies (default 5%)
            window_size: Number of recent samples to keep for model updates
        """
        self.contamination = contamination
        self.window_size = window_size
        
        # Models per sensor type
        self.models: Dict[str, IsolationForest] = {}
        self.scalers: Dict[str, StandardScaler] = {}
        
        # Training data buffers
        self.training_buffers: Dict[str, deque] = {}
        
        # Model performance tracking
        self.predictions_count = {}
        self.anomalies_detected = {}
        
        # Last training time
        self.last_training = {}
        self.retrain_interval = timedelta(minutes=5)
        
    def _get_features(self, reading: dict, history: List[dict]) -> np.ndarray:
        """
        Extract features from current reading and historical context.
        
        Features include:
        - Current value
        - Hour of day (cyclical encoding)
        - Rate of change from previous reading
        - Rolling statistics (mean, std) from recent history
        """
        features = []
        
        # Current value
        features.append(reading["value"])
        
        # Time-based features (cyclical encoding)
        timestamp = datetime.fromisoformat(reading["timestamp"])
        hour = timestamp.hour
        features.append(np.sin(2 * np.pi * hour / 24))  # Hour sine
        features.append(np.cos(2 * np.pi * hour / 24))  # Hour cosine
        
        # Historical features
        if len(history) >= 2:
            recent_values = [h["value"] for h in history[-10:]]
            
            # Rate of change
            prev_value = history[-1]["value"]
            rate_of_change = (reading["value"] - prev_value) / (prev_value + 1e-6)
            features.append(rate_of_change)
            
            # Rolling statistics
            features.append(np.mean(recent_values))
            features.append(np.std(recent_values))
            features.append(np.max(recent_values) - np.min(recent_values))  # Range
        else:
            # Not enough history, use zeros
            features.extend([0.0, reading["value"], 0.0, 0.0])
        
        return np.array(features).reshape(1, -1)
    
    def _should_retrain(self, sensor_type: str) -> bool:
        """Check if model should be retrained."""
        if sensor_type not in self.last_training:
            return True
        
        time_since_training = datetime.now() - self.last_training[sensor_type]
        buffer_size = len(self.training_buffers.get(sensor_type, []))
        
        return (time_since_training >= self.retrain_interval and 
                buffer_size >= self.window_size)
    
    def train_model(self, sensor_type: str):
        """Train or update the model for a specific sensor type."""
        if sensor_type not in self.training_buffers:
            return
        
        buffer = self.training_buffers[sensor_type]
        if len(buffer) < 50:  # Minimum samples needed
            return
        
        print(f"[ML Detector] 🔄 Training model for {sensor_type} with {len(buffer)} samples...")
        
        # Extract features from buffer
        X = []
        for i, reading in enumerate(buffer):
            history = list(buffer)[:i]
            features = self._get_features(reading, history)
            X.append(features.flatten())
        
        X = np.array(X)
        
        # Fit scaler
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Train Isolation Forest
        model = IsolationForest(
            contamination=self.contamination,
            random_state=42,
            n_estimators=100,
            max_samples='auto',
            n_jobs=-1
        )
        model.fit(X_scaled)
        
        # Store model and scaler
        self.models[sensor_type] = model
        self.scalers[sensor_type] = scaler
        self.last_training[sensor_type] = datetime.now()
        
        print(f"[ML Detector] ✓ Model trained for {sensor_type}")
    
    def predict(self, reading: dict, history: List[dict]) -> Tuple[bool, float]:
        """
        Predict if a reading is anomalous.
        
        Returns:
            Tuple of (is_anomaly, anomaly_score)
        """
        sensor_type = reading["sensor_type"]
        
        # Add to training buffer
        if sensor_type not in self.training_buffers:
            self.training_buffers[sensor_type] = deque(maxlen=self.window_size)
        self.training_buffers[sensor_type].append(reading)
        
        # Initialize model if needed
        if sensor_type not in self.models:
            if len(self.training_buffers[sensor_type]) >= 50:
                self.train_model(sensor_type)
            return False, 0.0
        
        # Check if retraining is needed
        if self._should_retrain(sensor_type):
            self.train_model(sensor_type)
        
        # Extract features and predict
        features = self._get_features(reading, history)
        features_scaled = self.scalers[sensor_type].transform(features)
        
        # Predict (-1 for anomaly, 1 for normal)
        prediction = self.models[sensor_type].predict(features_scaled)[0]
        
        # Get anomaly score (lower = more anomalous)
        anomaly_score = self.models[sensor_type].score_samples(features_scaled)[0]
        
        is_anomaly = prediction == -1
        
        # Update statistics
        if sensor_type not in self.predictions_count:
            self.predictions_count[sensor_type] = 0
            self.anomalies_detected[sensor_type] = 0
        
        self.predictions_count[sensor_type] += 1
        if is_anomaly:
            self.anomalies_detected[sensor_type] += 1
        
        return is_anomaly, anomaly_score
    
    def get_statistics(self) -> Dict:
        """Get detector performance statistics."""
        stats = {}
        for sensor_type in self.predictions_count:
            total = self.predictions_count[sensor_type]
            anomalies = self.anomalies_detected[sensor_type]
            stats[sensor_type] = {
                "total_predictions": total,
                "anomalies_detected": anomalies,
                "anomaly_rate": (anomalies / total * 100) if total > 0 else 0.0,
            }
        return stats


def setup_database(conn):
    """Create table for ML predictions."""
    cur = conn.cursor()
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ml_anomaly_predictions (
            id SERIAL PRIMARY KEY,
            sensor_id VARCHAR(100),
            sensor_type VARCHAR(50),
            location VARCHAR(100),
            value NUMERIC(10, 2),
            timestamp TIMESTAMP,
            is_anomaly BOOLEAN,
            anomaly_score NUMERIC(10, 6),
            rule_based_anomaly BOOLEAN,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_ml_predictions_timestamp 
        ON ml_anomaly_predictions(timestamp DESC);
    """)
    
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_ml_predictions_anomaly 
        ON ml_anomaly_predictions(is_anomaly, timestamp DESC);
    """)
    
    conn.commit()
    print("[ML Detector] ✓ Predictions table ready.")


def run_ml_detector():
    """Main ML anomaly detection processor."""
    try:
        print("[ML Detector] Connecting to Kafka at localhost:9092...")
        consumer = KafkaConsumer(
            "iot_sensors",
            bootstrap_servers="localhost:9092",
            auto_offset_reset="latest",
            enable_auto_commit=True,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            group_id="ml-detector-group",
        )
        print("[ML Detector] ✓ Connected to Kafka successfully!")
        
        print("[ML Detector] Connecting to PostgreSQL...")
        conn = psycopg2.connect(
            dbname="iot_db",
            user="iot_user",
            password="iot_password",
            host="localhost",
            port="5432",
        )
        conn.autocommit = False
        print("[ML Detector] ✓ Connected to PostgreSQL successfully!")
        
        setup_database(conn)
        
        # Initialize ML detector
        detector = OnlineAnomalyDetector(contamination=0.05, window_size=1000)
        
        # Keep history per sensor
        sensor_history: Dict[str, deque] = {}
        
        print("[ML Detector] 🤖 ML anomaly detection active...\n")
        
        message_count = 0
        last_stats_print = time.time()
        
        for message in consumer:
            try:
                reading = message.value
                sensor_id = reading["sensor_id"]
                
                # Maintain history for each sensor
                if sensor_id not in sensor_history:
                    sensor_history[sensor_id] = deque(maxlen=100)
                
                history = list(sensor_history[sensor_id])
                sensor_history[sensor_id].append(reading)
                
                # Get ML prediction
                is_ml_anomaly, anomaly_score = detector.predict(reading, history)
                
                # Store prediction in database
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO ml_anomaly_predictions 
                    (sensor_id, sensor_type, location, value, timestamp, 
                     is_anomaly, anomaly_score, rule_based_anomaly)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                """, (
                    reading["sensor_id"],
                    reading["sensor_type"],
                    reading["location"],
                    reading["value"],
                    reading["timestamp"],
                    is_ml_anomaly,
                    anomaly_score,
                    reading["anomaly"],  # Original rule-based flag
                ))
                conn.commit()
                
                message_count += 1
                
                # Log anomalies
                if is_ml_anomaly:
                    print(f"[ML Detector] 🚨 ANOMALY DETECTED!")
                    print(f"  Sensor: {sensor_id[:40]}")
                    print(f"  Type: {reading['sensor_type']}")
                    print(f"  Value: {reading['value']} {reading['unit']}")
                    print(f"  Location: {reading['location']}")
                    print(f"  Anomaly Score: {anomaly_score:.4f}")
                    print(f"  Rule-based flag: {reading['anomaly']}\n")
                
                # Print statistics every 60 seconds
                if time.time() - last_stats_print >= 60:
                    stats = detector.get_statistics()
                    print("\n[ML Detector] 📊 Statistics:")
                    for sensor_type, stat in stats.items():
                        print(f"  {sensor_type:<15} | "
                              f"Predictions: {stat['total_predictions']:>5} | "
                              f"Anomalies: {stat['anomalies_detected']:>4} | "
                              f"Rate: {stat['anomaly_rate']:>5.2f}%")
                    print()
                    last_stats_print = time.time()
                
            except Exception as e:
                print(f"[ML Detector ERROR] Failed to process message: {e}")
                import traceback
                traceback.print_exc()
                continue
                
    except KeyboardInterrupt:
        print("\n[ML Detector] Shutting down gracefully...")
        conn.close()
    except Exception as e:
        print(f"[ML Detector ERROR] {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    run_ml_detector()
